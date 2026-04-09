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
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from fastapi import Form
from sqlalchemy import and_
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from twilio.rest import Client
import razorpay
from fastapi import Request
from dotenv import load_dotenv
import os
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv
load_dotenv()


print("🔥 THIS OTP VERSION IS RUNNING")



SECRET_KEY = "Babi@2302"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

print("RAZORPAY ID:", RAZORPAY_KEY_ID)

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

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


import random

def generate_otp():
    return str(random.randint(100000, 999999))




TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

print("SID:", TWILIO_ACCOUNT_SID)
print("TOKEN:", TWILIO_AUTH_TOKEN)
print("SERVICE:", TWILIO_VERIFY_SERVICE_SID)




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
# DATABASE_URL = "postgresql://postgres@postgres.railway.internal:5432/railway"
# DATABASE_URL = "postgresql://postgres@localhost:5432/CBT"
# Try environment variable first (for production later)
DATABASE_URL = os.getenv("DATABASE_URL")

# If not found → use LOCAL PostgreSQL
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:sagarsahA%401@localhost:5432/CBT"

print("Using DB URL:", DATABASE_URL)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Session
SessionLocal = sessionmaker(bind=engine)

# Base model
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
    reset_token = Column(String, nullable=True)   # ✅ ADD THIS
    created_at = Column(String, default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class MobileVerification(Base):
    __tablename__ = "mobile_verifications"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True)
    mobile = Column(String, unique=True)
    otp_hash = Column(String)
    is_verified = Column(Boolean, default=False)
    expires_at = Column(String)


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

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True, index=True)
    course_slug = Column(String, unique=True)   # sankalp-b1
    name = Column(String)
    type = Column(String)
    price = Column(Integer)
    access_duration = Column(String)
    activation = Column(String)
    short_description = Column(Text)
    total_videos = Column(String)
    notes = Column(Text) 

class Video(Base):
    __tablename__ = "videos"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer)
    title = Column(String)
    video_url = Column(Text)
    created_at = Column(String)

class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = {"schema": "cbt"}

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String)
    course_id = Column(Integer)
    purchased_at = Column(String, default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))



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
# @app.post("/login-student")
# def login_student(email: str = Form(...), password: str = Form(...)):
#     db = SessionLocal()
#     user = db.query(Student).filter(Student.email == email).first()
#     db.close()

#     if not user:
#         return {"error": "Invalid credentials!"}

#     if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
#         return {"error": "Invalid credentials!"}

#     return {
#         "status": "success",
#         "student_id": user.student_id,
#         "name": user.name,
#         "email": user.email,
#     }


@app.post("/login-student")
def login_student(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(Student).filter(Student.email == email).first()
    db.close()

    if not user:
        return {"error": "Invalid credentials!"}

    import hashlib

    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        pass

    elif hashlib.sha256(password.encode()).hexdigest() == user.password:
        pass

    else:
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
        # ✅ Generate SAFE & UNIQUE student_id
        student_id = f"STD{uuid.uuid4().hex[:6].upper()}"

        # ❌ Email already exists check
        if db.query(Student).filter(Student.email == email).first():
            return {
                "status": "error",
                "message": "Email already registered!"
            }

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
            "status": "success",
            "message": "Student registered successfully",
            "student_id": student_id,
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }

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

@app.post("/auth/send-otp")
def send_otp(mobile: str = Form(...)):
    db = SessionLocal()

    try:
        # ✅ Ensure mobile is in correct format
        mobile = mobile.strip()

        if not mobile.startswith("+"):
            return {
                "status": "error",
                "message": "Mobile number must include country code (e.g. +91XXXXXXXXXX)"
            }

        print("📱 OTP REQUEST FOR:", mobile)

        # ✅ Check already registered
        existing = db.query(Student).filter(Student.mobile == mobile).first()
        if existing:
            return {
                "status": "error",
                "message": "Mobile already registered!"
            }

        # ✅ Send OTP via Twilio
        try:
            verification = twilio_client.verify.v2.services(
                TWILIO_VERIFY_SERVICE_SID
            ).verifications.create(
                to=mobile,
                channel="sms"
            )

            print("✅ Twilio response:", verification.status)

        except Exception as e:
            print("❌ Twilio error:", e)
            return {
                "status": "error",
                "message": "OTP sending failed. Try again later."
            }

        return {
            "status": "success",
            "message": "OTP sent successfully"
        }

    except Exception as e:
        print("❌ SERVER ERROR:", e)
        return {
            "status": "error",
            "message": "Internal server error"
        }

    finally:
        db.close()

@app.post("/auth/verify-mobile")
def verify_mobile(mobile: str = Form(...), otp: str = Form(...)):
    try:
        # ✅ Keep same format as send_otp (NO modification)
        mobile = mobile.strip()

        if not mobile.startswith("+"):
            return {
                "status": "error",
                "message": "Invalid mobile format. Use +91XXXXXXXXXX"
            }

        print("🔐 VERIFY OTP FOR:", mobile)

        # ✅ Verify OTP via Twilio
        result = twilio_client.verify.v2.services(
            TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(
            to=mobile,
            code=otp
        )

        print("📩 Twilio verify status:", result.status)

        if result.status == "approved":
            return {
                "status": "success",
                "message": "Mobile verified successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Invalid OTP"
            }

    except Exception as e:
        print("❌ VERIFY ERROR:", e)
        return {
            "status": "error",
            "message": "OTP verification failed"
        }


@app.post("/my-courses")
def my_courses(student_id: str = Form(...)):
    db = SessionLocal()

    try:
        purchases = db.query(Purchase).filter(
            Purchase.student_id == student_id
        ).all()

        result = []

        for p in purchases:
            course = db.query(Course).filter(
                Course.id == p.course_id
            ).first()

            videos = db.query(Video).filter(
                Video.course_id == course.id
            ).all()

            result.append({
                "id": course.id,
                "course_slug": course.course_slug,
                "name": course.name,
                "videos": [
                    {
                        "video_url": v.video_url,
                        "title": v.title
                    } for v in videos
                ]
            })

        return {"courses": result}

    finally:
        db.close()


@app.post("/buy-course")
def buy_course(student_id: str = Form(...), course_slug: str = Form(...)):
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.course_slug == course_slug).first()
        if not course:
            return {"status": "error", "message": "Course not found"}

        existing = db.query(Purchase).filter(
            and_(Purchase.student_id == student_id, Purchase.course_id == course.id)
        ).first()

        if existing:
            return {"status": "error", "message": "Already purchased"}

        p = Purchase(student_id=student_id, course_id=course.id)
        db.add(p)
        db.commit()

        return {"status": "success", "message": "Purchased successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@app.get("/course-details/{slug}")
def course_details(slug: str):
    db = SessionLocal()

    try:
        course = db.query(Course).filter(
            Course.course_slug == slug
        ).first()

        if not course:
            return {"error": "Course not found"}

        # Demo videos (later DB table use করবে)
        videos = db.query(Video).filter(
            Video.course_id == course.id
        ).all()

        return {
            "price": course.price,
            "name": course.name,
            "videos": [
            {
                "id": v.id,
                "title": v.title,
                "video_url": v.video_url
            }
            for v in videos
        ]
}

        # return {"videos": videos}

    finally:
        db.close()

# @app.post("/cloudinary-webhook")
# async def cloudinary_webhook(data: dict):
#     print("🔥 FULL DATA:", data)
#     db = SessionLocal()

#     try:
#         public_id = data.get("public_id")
#         secure_url = data.get("secure_url")
        

#         # example: courses/sankalp-b1/video1
#         parts = public_id.split("/")

#         course_slug = parts[1]

#         course = db.query(Course).filter(
#             Course.course_slug == course_slug
#         ).first()

#         if not course:
#             return {"error": "course not found"}

#         new_video = Video(
#             course_id=course.id,
#             title=parts[-1],
#             video_url=secure_url,
#             created_at=str(datetime.now())
#         )

#         db.add(new_video)
#         db.commit()

#         return {"status": "saved"}

#     except Exception as e:
#         db.rollback()
#         return {"error": str(e)}

#     finally:
#         db.close()

#         print("📦 PUBLIC ID:", public_id)
#         print("🌐 URL:", secure_url)

@app.post("/cloudinary-webhook")
async def cloudinary_webhook(data: dict):
    print("🔥 FULL DATA:", data)

    db = SessionLocal()

    try:
        public_id = data.get("public_id")
        secure_url = data.get("secure_url")
        asset_folder = data.get("asset_folder")

        print("📦 PUBLIC ID:", public_id)
        print("📁 FOLDER:", asset_folder)
        print("🌐 URL:", secure_url)

        # ✅ Validate folder
        if not asset_folder:
            return {"error": "Folder missing"}

        parts = asset_folder.split("/")

        if len(parts) < 2:
            return {"error": "Invalid folder format"}

        course_slug = parts[1]

        # ✅ Find course
        course = db.query(Course).filter(
            Course.course_slug == course_slug
        ).first()

        if not course:
            return {"error": "course not found"}

        # ✅ Save video
        new_video = Video(
            course_id=course.id,
            title=public_id,   # video name
            video_url=secure_url,
            created_at=str(datetime.now())
        )

        db.add(new_video)
        db.commit()

        return {"status": "saved"}

    except Exception as e:
        db.rollback()
        print("❌ ERROR:", e)
        return {"error": str(e)}

    finally:
        db.close()


@app.post("/create-order")
def create_order(course_slug: str = Form(...)):
    db = SessionLocal()

    course = db.query(Course).filter(Course.course_slug == course_slug).first()
    if not course:
        return {"error": "Course not found"}

    order = client.order.create({
        "amount": course.price * 100,   # paisa
        "currency": "INR",
        "payment_capture": 1
    })

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "key": RAZORPAY_KEY_ID
    }

print("KEY:", RAZORPAY_KEY_ID)
print("SECRET:", RAZORPAY_KEY_SECRET)


@app.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str = Form(...),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: str = Form(...),
    student_id: str = Form(...),
    course_slug: str = Form(...)
):
    try:
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }

        client.utility.verify_payment_signature(params_dict)

        # ✅ Payment success → save purchase
        db = SessionLocal()

        course = db.query(Course).filter(Course.course_slug == course_slug).first()

        purchase = Purchase(
            student_id=student_id,
            course_id=course.id
        )

        db.add(purchase)
        db.commit()

        return {"status": "success"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}
    

@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    db = SessionLocal()

    user = db.query(Student).filter(Student.email == email).first()

    if not user:
        return {"message": "Email not found"}

    token = str(uuid.uuid4())
    user.reset_token = token
    db.commit()

    reset_link = f"https://www.geomaticsgalaxy.com/reset-password/{token}"

    return {
        "message": "Reset link generated",
        "reset_link": reset_link
    }

@app.post("/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...)):
    db = SessionLocal()

    user = db.query(Student).filter(Student.reset_token == token).first()

    if not user:
        return {"message": "Invalid token"}

    import bcrypt

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    user.password = hashed
    user.reset_token = None

    db.commit()

    return {"message": "Password updated successfully"}

# =========================================================
# 11️⃣ ROOT CHECK
# =========================================================
@app.get("/")
def root():
    return {"status": "✅ Backend running successfully!"}

