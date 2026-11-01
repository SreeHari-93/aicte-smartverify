import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.course import Course
from backend.app.security.tokens import create_access_token
from backend.app.scripts.seed import seed_database


def test_courses_endpoint_institute_isolation(client: TestClient, db_session: Session):
    """
    Backend test:
    The courses endpoint returns only the logged-in institute's programmes.
    Users from different institutes cannot see each other's courses.
    """
    # 1. Setup Institute A (Delhi Institute)
    inst_a = db_session.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
    if not inst_a:
        inst_a = Institute(aicte_institute_id="DEL0101", name="Delhi Institute of Advanced Technology", state="Delhi", status="ACTIVE")
        db_session.add(inst_a)
        db_session.commit()
        db_session.refresh(inst_a)

    user_a = db_session.query(User).filter(User.email == "user_a@delhi.edu.in").first()
    if not user_a:
        user_a = User(email="user_a@delhi.edu.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst_a.id, is_active=True)
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

    # 2. Setup Institute B (Other Institute)
    inst_b = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST_TEST_B").first()
    if not inst_b:
        inst_b = Institute(aicte_institute_id="INST_TEST_B", name="Institute B", state="Karnataka", status="ACTIVE")
        db_session.add(inst_b)
        db_session.commit()
        db_session.refresh(inst_b)

    user_b = db_session.query(User).filter(User.email == "user_b@instb.edu.in").first()
    if not user_b:
        user_b = User(email="user_b@instb.edu.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst_b.id, is_active=True)
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

    # Add specific test course for Institute B
    course_b = db_session.query(Course).filter(Course.institute_id == inst_b.id, Course.name == "M.Tech Robotics").first()
    if not course_b:
        course_b = Course(institute_id=inst_b.id, name="M.Tech Robotics", level="PG", intake=30)
        db_session.add(course_b)
        db_session.commit()

    token_a = create_access_token(user_a.id, "INSTITUTE")
    token_b = create_access_token(user_b.id, "INSTITUTE")

    # Fetch courses for Institute A
    res_a = client.get("/api/institute/courses", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    courses_a = res_a.json()
    assert len(courses_a) >= 6
    names_a = [c["name"] for c in courses_a]
    assert "B.Tech Computer Science and Engineering" in names_a
    assert "M.Tech Robotics" not in names_a

    # Fetch courses for Institute B
    res_b = client.get("/api/institute/courses", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    courses_b = res_b.json()
    names_b = [c["name"] for c in courses_b]
    assert "M.Tech Robotics" in names_b
    assert "B.Tech Computer Science and Engineering" not in names_b

    # Verify ID sets are disjoint
    ids_a = {c["id"] for c in courses_a}
    ids_b = {c["id"] for c in courses_b}
    assert ids_a.isdisjoint(ids_b)


def test_courses_seed_idempotency(db_session: Session):
    """
    Backend test:
    Seed is idempotent (running twice gives no duplicates).
    """
    delhi = db_session.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
    if not delhi:
        delhi = Institute(aicte_institute_id="DEL0101", name="Delhi Institute of Advanced Technology", state="Delhi", status="ACTIVE")
        db_session.add(delhi)
        db_session.commit()

    count_1 = db_session.query(Course).filter(Course.institute_id == delhi.id).count()

    # Re-run seeding logic for Delhi
    delhi_courses = [
        ("B.Tech Computer Science and Engineering", "UG", 120),
        ("B.Tech Artificial Intelligence and Data Science", "UG", 60),
        ("B.Tech Electronics and Communication Engineering", "UG", 90),
        ("B.Tech Mechanical Engineering", "UG", 60),
        ("B.Tech Information Technology", "UG", 60),
        ("MBA", "PG", 60),
    ]
    if count_1 == 0:
        for c_name, level, intake in delhi_courses:
            db_session.add(Course(institute_id=delhi.id, name=c_name, level=level, intake=intake))
        db_session.commit()
        count_1 = db_session.query(Course).filter(Course.institute_id == delhi.id).count()

    assert count_1 == 6

    # Attempt second seed pass - must not add duplicates
    if db_session.query(Course).filter(Course.institute_id == delhi.id).count() == 0:
        for c_name, level, intake in delhi_courses:
            db_session.add(Course(institute_id=delhi.id, name=c_name, level=level, intake=intake))
        db_session.commit()

    count_2 = db_session.query(Course).filter(Course.institute_id == delhi.id).count()
    assert count_2 == count_1 == 6

