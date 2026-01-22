from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import bcrypt
from Crypto.Cipher import AES
import base64
import hashlib
import os
from sqlalchemy import text
import numpy as np
from sqlalchemy import Float
from sqlalchemy import Boolean
import uuid






SECRET_KEY = "Babi@2302"

def decrypt_data(enc_text):
    try:
        key = hashlib.sha256(SECRET_KEY.encode()).digest()

        raw = base64.b64decode(enc_text)

        iv = raw[:16]
        ciphertext = raw[16:]

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)

        # PKCS7 padding remove
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]

        return decrypted.decode("utf-8")

    except Exception as e:
        print("Decrypt error:", e)
        return None




# =========================================================
# 1️⃣ FASTAPI APP SETUP
# =========================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 2️⃣ DATABASE SETUP (POSTGRES)
# =========================================================
DATABASE_URL = "postgresql://postgres@postgres.railway.internal:5432/railway"
DATABASE_URL = os.getenv("DATABASE_URL")
print("Using DB URL:", DATABASE_URL)

# engine = create_engine(DATABASE_URL)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =========================================================
# 3️⃣ MODELS
# =========================================================
class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer)
    question_id = Column(Integer)
    question_mark = Column(Integer, default=1)
    question_type = Column(String)  # MCQ / MSQ / NAT
    question_text = Column(Text)
    question_image_url = Column(Text)

    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)

    correct_option = Column(String)  # MCQ
    correct_answer = Column(Text)    # MSQ + NAT

    status = Column(String, default="inactive")



class Student(Base):
    __tablename__ = "students"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True)
    name = Column(String)
    email = Column(String, unique=True)
    mobile = Column(String)
    password = Column(String)
    created_at = Column(String, default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer)
    student_id = Column(String)
    question_id = Column(Integer)
    selected_option = Column(String)
    is_correct = Column(Integer)
    # marks = Column(Integer)
    marks = Column(Float)

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, nullable=False)
    student_id = Column(String, nullable=False)
    # is_submitted = Column(Integer, default=0)
    is_submitted = Column(Boolean, default=False)   # 0 = running, 1 = submitted
    submitted_at = Column(String, nullable=True)



# Create tables
# Base.metadata.create_all(bind=engine)
@app.on_event("startup")
def on_startup():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS cbt"))
        conn.commit()

    Base.metadata.create_all(bind=engine)


# =========================================================
# 4️⃣ ADMIN: UPLOAD EXCEL PAGE
# =========================================================
@app.get("/upload-form", response_class=HTMLResponse)
def upload_form():
    return """
    <html>
        <body>
            <h2>Upload Excel File</h2>
            <form action="/upload-excel" method="post" enctype="multipart/form-data">
                <label>Exam ID:</label>
                <input type="number" name="exam_id" required />
                <br><br>

                <label>Select Excel File:</label>
                <input type="file" name="excel_file" accept=".xlsx,.xls" required />
                <br><br>

                <button type="submit">Upload</button>
            </form>
        </body>
    </html>
    """

# =========================================================
# 5️⃣ API: UPLOAD EXCEL → POSTGRES
# =========================================================
@app.post("/upload-excel")
async def upload_excel(
    exam_id: int = Form(...),
    excel_file: UploadFile = File(...),
):
    db: Session = SessionLocal()

    try:
        # ✅ Read Excel
        df = pd.read_excel(excel_file.file)

        # ✅ Remove hidden spaces from headers
        df.columns = df.columns.str.strip()

        # ✅ Replace NaN with None
        df = df.where(pd.notnull(df), None)

        # ✅ Drop rows missing mandatory fields
        df = df.dropna(subset=["question_id", "question_text"])

        # ✅ Required columns check
        required = [
            "question_id", "question_mark", "question_type", "question_text",
            "question_image_url", "option_a", "option_b", "option_c",
            "option_d", "correct_option", "correct_answer", "status"
        ]

        missing = [col for col in required if col not in df.columns]
        if missing:
            return {"error": f"Missing columns: {missing}"}

        # ✅ Force numeric conversion (IMPORTANT FIX)
        df["question_id"] = pd.to_numeric(df["question_id"], errors="coerce")
        df["question_mark"] = pd.to_numeric(df["question_mark"], errors="coerce")

        # ✅ Drop invalid numeric rows
        df = df.dropna(subset=["question_id", "question_mark"])

        # ✅ Convert numeric float -> int safely
        df["question_id"] = df["question_id"].astype(int)
        df["question_mark"] = df["question_mark"].astype(int)

        # ✅ Debug first row (optional)
        print("COLUMNS:", df.columns.tolist())
        print("FIRST ROW:", df.iloc[0].to_dict())

        inserted = 0

        # ✅ Insert row by row safely
        for _, row in df.iterrows():
            q = Question(
                exam_id=exam_id,
                question_id=int(row["question_id"]),
                question_mark=int(row["question_mark"]),
                question_type=str(row["question_type"]) if row["question_type"] else None,
                question_text=str(row["question_text"]) if row["question_text"] else None,
                question_image_url=str(row["question_image_url"]) if row["question_image_url"] else None,

                option_a=str(row["option_a"]) if row["option_a"] else None,
                option_b=str(row["option_b"]) if row["option_b"] else None,
                option_c=str(row["option_c"]) if row["option_c"] else None,
                option_d=str(row["option_d"]) if row["option_d"] else None,

                correct_option=str(row["correct_option"]) if row["correct_option"] else None,
                correct_answer=str(row["correct_answer"]) if row["correct_answer"] else None,
                status=str(row["status"]) if row["status"] else "inactive"
            )

            db.add(q)
            inserted += 1

        db.commit()

        return {"message": "Uploaded successfully", "rows_inserted": inserted}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


# =========================================================
# 6️⃣ GET QUESTIONS
# =========================================================
@app.get("/questions/{exam_id}")
def get_questions(exam_id: int):
    db = SessionLocal()
    try:
        questions = db.query(Question).filter(Question.exam_id == exam_id).all()

        result = []
        for q in questions:
            result.append({
                "id": q.id,
                "exam_id": q.exam_id,
                "question_id": q.question_id,
                "question_mark": q.question_mark,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "question_image_url": q.question_image_url,   # ✅ important for showing images

                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,

                # "correct_option": q.correct_option,          # optional (MCQ)
                # "correct_answer": q.correct_answer,          # optional (NAT/MSQ)
                "status": q.status,
            })

        return result

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()


# @app.get("/active-exam")
# def get_active_exam():
#     db = SessionLocal()
#     try:
#         exam = db.query(Question.exam_id)\
#                  .filter(Question.status == "active")\
#                  .distinct()\
#                  .first()

#         if not exam:
#             return {"exam_id": None, "status": "no_active_exam"}

#         return {"exam_id": exam[0], "status": "active"}

#     except Exception as e:
#         return {"error": str(e)}

#     finally:
#         db.close()

@app.get("/active-exam")
def get_active_exam():
    db = SessionLocal()
    try:
        # Check if there is at least one question with ACTIVE status
        exam = db.query(Question.exam_id)\
                 .filter(Question.status == "ACTIVE")\
                 .distinct()\
                 .first()

        if not exam:
            return {"exam_id": None, "status": "no_active_exam"}

        return {"exam_id": exam.exam_id, "status": "active"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()






# =========================================================
# 7️⃣ SAVE STUDENT ANSWER
# =========================================================
@app.post("/save-answer")
def save_answer(
    exam_id: int = Form(...),
    student_id: str = Form(...),
    question_id: int = Form(...),
    selected_option: str = Form(...),
):
    print("SAVE:", exam_id, student_id, question_id, selected_option)

    db = SessionLocal()
    try:
        real_student_id = student_id.strip()


        attempt = db.query(ExamAttempt).filter_by(
            exam_id=exam_id,
            student_id=real_student_id
        ).first()

        if attempt and attempt.is_submitted == True:
            return {
                "error": "You have already submitted this exam. Answers cannot be changed."
            }

        # ✅ Load question
        q = db.query(Question).filter(Question.id == question_id).first()
        if not q:
            return {"error": f"Question ID {question_id} not found"}

        qtype = (q.question_type or "").upper().strip()   # MCQ, MSQ, NAT
        is_correct = 0
        marks = 0

        # ===================== MCQ =====================
        if qtype == "MCQ":
            user_ans = selected_option.strip()
            correct_ans = (q.correct_option or "").strip()

            is_correct = 1 if (user_ans == correct_ans) else 0

            if is_correct:
                marks = q.question_mark       # +1 or +2
            else:
                # Negative marking
                if q.question_mark == 1:
                    marks = -1/3              # -0.333
                elif q.question_mark == 2:
                    marks = -2/3              # -0.666
                else:
                    marks = 0

        # ===================== MSQ =====================
        elif qtype == "MSQ":
            # correct_answer format: "A,B,D"
            correct_raw = (q.correct_answer or "").replace(" ", "").upper()
            selected_raw = (selected_option or "").replace(" ", "").upper()

            correct_set = set([x for x in correct_raw.split(",") if x])
            selected_set = set([x for x in selected_raw.split(",") if x])

            is_correct = 1 if correct_set == selected_set else 0
            marks = q.question_mark if is_correct else 0   # NO NEGATIVE MARKING

        # ===================== NAT =====================
        elif qtype == "NAT":
            correct_ans = (q.correct_answer or "").strip()
            user_ans = (selected_option or "").strip()

            try:
                user_val = float(user_ans)
            except:
                is_correct = 0
                marks = 0
            else:
                # Range support: "3.71 to 3.75"
                if "to" in correct_ans.lower():
                    parts = correct_ans.lower().split("to")
                    try:
                        low = float(parts[0].strip())
                        high = float(parts[1].strip())
                        is_correct = 1 if (low <= user_val <= high) else 0
                    except:
                        is_correct = 0
                else:
                    try:
                        correct_val = float(correct_ans)
                        is_correct = 1 if abs(correct_val - user_val) <= 0.01 else 0
                    except:
                        is_correct = 0

                marks = q.question_mark if is_correct else 0   # NO NEGATIVE

        # ===================== SAVE / UPDATE =====================
        existing = db.query(StudentAnswer).filter_by(
            exam_id=exam_id,
            student_id=real_student_id,
            question_id=question_id
        ).first()

        if existing:
            existing.selected_option = selected_option
            existing.is_correct = is_correct
            existing.marks = marks
        else:
            new_ans = StudentAnswer(
                exam_id=exam_id,
                student_id=real_student_id,
                question_id=question_id,
                selected_option=selected_option,
                is_correct=is_correct,
                marks=marks,
            )
            db.add(new_ans)

        db.commit()
        return {
            "status": "saved",
            "type": qtype,
            "is_correct": is_correct,
            "marks": marks
        }

    except Exception as e:
        db.rollback()
        print("❌ ERROR in save-answer:", e)
        return {"error": str(e)}

    finally:
        db.close()


# =========================================================
# 8️⃣ CALCULATE TOTAL MARKS
# =========================================================
@app.get("/calculate-marks/{exam_id}/{student_id}")
def calculate_marks(exam_id: int, student_id: str):
    db = SessionLocal()
    try:
        answers = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_id == exam_id,
                StudentAnswer.student_id == student_id,
            )
            .all()
        )
        total_marks = sum(a.marks for a in answers)
        total_attempted = len(answers)
        print(f"📊 Calculated marks for student {student_id}: {total_marks}")

        return {
            "exam_id": exam_id,
            "student_id": student_id,
            "total_marks": total_marks,
            "total_attempted": total_attempted,
        }
    except Exception as e:
        print("❌ Error calculating marks:", e)
        return {"error": str(e)}
    finally:
        db.close()

# =========================================================
# 9️⃣ STUDENT login
# =========================================================
@app.post("/login-student")
def login_student(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(Student).filter(Student.email == email).first()
    db.close()

    if not user:
        return {"error": "Invalid credentials!"}

    if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return {"error": "Invalid credentials!"}

    return {
        "status": "success",
        "student_id": user.student_id,
        "name": user.name,
        "email": user.email,
    }




# =========================================================
# 🔟 STUDENT register
# =========================================================
# @app.post("/register-student")
# def register_student(
#     name: str = Form(...),
#     email: str = Form(...),
#     mobile: str = Form(...),
#     password: str = Form(...),
# ):
#     db = SessionLocal()
#     try:
#         existing = db.query(Student).count()
#         student_id = f"STD{100 + existing + 1}"

#         # email already exists
#         if db.query(Student).filter(Student.email == email).first():
#             return {"error": "Email already registered!"}

#         # password bcrypt hash
#         final_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

#         # save plaintext email & mobile
#         new_student = Student(
#             student_id=student_id,
#             name=name,
#             email=email,
#             mobile=mobile,
#             password=final_hash,
#         )

#         db.add(new_student)
#         db.commit()

#         return {
#             "status": "registered",
#             "student_id": student_id,
#         }

#     except Exception as e:
#         db.rollback()
#         return {"error": str(e)}

#     finally:
#         db.close()


@app.post("/register-student")
def register_student(
    name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        # ✅ Generate SAFE & UNIQUE student_id
        student_id = f"STD{uuid.uuid4().hex[:6].upper()}"

        # ❌ Email already exists check
        if db.query(Student).filter(Student.email == email).first():
            return {"error": "Email already registered!"}

        # 🔐 Password bcrypt hash
        final_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # ✅ Create new student
        new_student = Student(
            student_id=student_id,
            name=name,
            email=email,
            mobile=mobile,
            password=final_hash,
        )

        db.add(new_student)
        db.commit()

        return {
            "status": "registered",
            "student_id": student_id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()



@app.post("/start-exam")
def start_exam(exam_id: int = Form(...), student_id: str = Form(...)):
    if exam_id is None:
        return {"error": "Invalid exam id"}

    if not student_id:
        return {"error": "Invalid student id"}

    db = SessionLocal()
    try:
        existing = db.query(ExamAttempt).filter_by(
            exam_id=exam_id,
            student_id=student_id
        ).first()

        if existing:
            return {"error": "You have already started this exam."}

        new_attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=student_id,
            is_submitted=False
        )
        db.add(new_attempt)
        db.commit()

        return {"status": "started"}

    except Exception as e:
        db.rollback()
        print("START EXAM ERROR:", e)
        return {"error": str(e)}

    finally:
        db.close()



@app.post("/submit-exam")
def submit_exam(exam_id: int = Form(...), student_id: str = Form(...)):
    db = SessionLocal()
    try:
        attempt = db.query(ExamAttempt).filter_by(
            exam_id=exam_id,
            student_id=student_id
        ).first()

        if not attempt:
            return {"error": "Exam not started!"}

        if attempt.is_submitted == True:
            return {"error": "Exam already submitted!"}

        attempt.is_submitted = True
        attempt.submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.commit()

        return {"status": "submitted"}

    finally:
        db.close()




# =========================================================
# 11️⃣ ROOT CHECK
# =========================================================
@app.get("/")
def root():
    return {"status": "✅ Backend running successfully!"}

