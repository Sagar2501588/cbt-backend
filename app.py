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

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer)
    question_text = Column(Text)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_option = Column(String)


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
    student_id = Column(Integer)
    question_id = Column(Integer)
    selected_option = Column(String)
    is_correct = Column(Integer)
    marks = Column(Integer)


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
    print("UPLOAD API CALLED")
    db = SessionLocal()

    try:
        df = pd.read_excel(excel_file.file)

        required_cols = [
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option"
        ]

        for col in required_cols:
            if col not in df.columns:
                return {
                    "error": f"Missing column: {col}",
                    "found": list(df.columns)
                }

        for _, row in df.iterrows():
            print("Inserting:", row["question_text"])
            q = Question(
                exam_id=exam_id,
                question_text=row["question_text"],
                option_a=row["option_a"],
                option_b=row["option_b"],
                option_c=row["option_c"],
                option_d=row["option_d"],
                correct_option=row["correct_option"],
            )
            db.add(q)
            print("ADDING QUESTION:", row["Question"])

        print("COMMITTING TO DB...")
        db.commit()
        print("COMMIT DONE")
        return {
            "message": "Questions uploaded successfully",
            "rows": len(df),
            "exam_id": exam_id
        }

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
    data = db.query(Question).filter(Question.exam_id == exam_id).all()
    db.close()
    return data

# =========================================================
# 7️⃣ SAVE STUDENT ANSWER
# =========================================================
# @app.post("/upload-excel")
# async def upload_excel(
#     exam_id: int = Form(...),
#     excel_file: UploadFile = File(...),
# ):
#     print("UPLOAD API CALLED")
#     db = SessionLocal()

#     try:
#         # Read Excel
#         df = pd.read_excel(excel_file.file)

#         # ✅ VERY IMPORTANT: strip column names
#         df.columns = df.columns.str.strip()

#         print("EXCEL COLUMNS FOUND:", df.columns.tolist())

#         required_cols = [
#             "question_text",
#             "option_a",
#             "option_b",
#             "option_c",
#             "option_d",
#             "correct_option",
#         ]

#         for col in required_cols:
#             if col not in df.columns:
#                 return {
#                     "error": f"Missing column: {col}",
#                     "found": list(df.columns),
#                 }

#         inserted = 0

#         for index, row in df.iterrows():
#             print(f"Inserting row {index + 1}")

#             q = Question(
#                 exam_id=exam_id,
#                 question_text=str(row["question_text"]),
#                 option_a=str(row["option_a"]),
#                 option_b=str(row["option_b"]),
#                 option_c=str(row["option_c"]),
#                 option_d=str(row["option_d"]),
#                 correct_option=str(row["correct_option"]),
#             )

#             db.add(q)
#             inserted += 1

#         print("COMMITTING TO DB...")
#         db.commit()
#         print("COMMIT SUCCESS")

#         return {
#             "message": "Questions uploaded successfully",
#             "rows": inserted,
#             "exam_id": exam_id,
#         }

#     except Exception as e:
#         db.rollback()
#         print("UPLOAD ERROR:", e)
#         return {"error": str(e)}

#     finally:
#         db.close()


# =========================================================
# 8️⃣ CALCULATE TOTAL MARKS
# =========================================================
@app.get("/calculate-marks/{exam_id}/{student_id}")
def calculate_marks(exam_id: int, student_id: int):
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
@app.post("/register-student")
def register_student(
    name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        existing = db.query(Student).count()
        student_id = f"STD{100 + existing + 1}"

        # email already exists
        if db.query(Student).filter(Student.email == email).first():
            return {"error": "Email already registered!"}

        # password bcrypt hash
        final_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # save plaintext email & mobile
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



# =========================================================
# 11️⃣ ROOT CHECK
# =========================================================
@app.get("/")
def root():
    return {"status": "✅ Backend running successfully!"}

