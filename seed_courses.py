import json
from app import SessionLocal, Course  # app.py থেকে import
from sqlalchemy.orm import Session

def seed_courses():
    db: Session = SessionLocal()

    try:
        with open("gate_ge_courses.json", "r") as f:
            courses_data = json.load(f)

        for item in courses_data:
            existing = db.query(Course).filter_by(
                course_slug=item["course_id"]
            ).first()

            if existing:
                print(f"Skipping (already exists): {item['course_name']}")
                continue

            new_course = Course(
                course_slug=item["course_id"],
                name=item["course_name"],
                type=item["type"],
                price=item["price_inr"],
                access_duration=item["access_duration"],
                activation=item["activation"],
                short_description=item["short_description"],
                total_videos=item["total_videos"],
                notes=item["notes"],
            )

            db.add(new_course)
            print(f"Inserted: {item['course_name']}")

        db.commit()
        print("✅ All courses inserted successfully!")

    except Exception as e:
        db.rollback()
        print("❌ Error:", e)

    finally:
        db.close()


if __name__ == "__main__":
    seed_courses()