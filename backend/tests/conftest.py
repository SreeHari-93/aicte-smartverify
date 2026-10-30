import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./test_aicte.db"
os.environ["SECRET_KEY"] = "test-secret-key-aicte-2026"

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.security.password import hash_password
from backend.app.security.rate_limiter import ip_limiter, account_limiter

TEST_DATABASE_URL = "sqlite:///./test_aicte.db"
engine_test = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    if os.path.exists("./test_aicte.db"):
        try:
            os.remove("./test_aicte.db")
        except OSError:
            pass


@pytest.fixture
def db_session():
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Reset rate limiters before test
    with ip_limiter.lock:
        ip_limiter.requests.clear()
    with account_limiter.lock:
        account_limiter.requests.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def seed_test_data(db_session):
    # Add Test Institute
    inst = Institute(
        aicte_institute_id="TEST001",
        name="Test Institute of Technology",
        state="Delhi",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    # Add Institute User
    inst_user = User(
        email="test_inst@aicte.edu.in",
        password_hash=hash_password("Institute@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst.id,
        is_active=True,
    )
    db_session.add(inst_user)

    # Add Admin User
    admin_user = User(
        email="admin@aicte-india.org",
        password_hash=hash_password("Admin@2026!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()

    return {
        "institute": inst,
        "inst_user": inst_user,
        "admin_user": admin_user,
    }
