import importlib.util
import os
import sqlite3
import subprocess
import sys
import textwrap
import types
from pathlib import Path

from sqlalchemy.engine import make_url


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent
_ADMIN_EMAIL = "admin@example.org"
_ADMIN_PASSWORD = "synthetic-admin-password-123"


def _load_database_module_without_project_settings():
    """Load the resolver with a synthetic config instead of the repository .env."""
    config_module = types.ModuleType("app.core.config")
    config_module.PROJECT_ROOT = _PROJECT_ROOT
    config_module.settings = types.SimpleNamespace(DATABASE_URL="sqlite://")
    previous_config = sys.modules.get("app.core.config")
    sys.modules["app.core.config"] = config_module
    try:
        spec = importlib.util.spec_from_file_location(
            "database_module_under_test", _BACKEND_ROOT / "app" / "core" / "database.py"
        )
        database_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database_module)
        return database_module
    finally:
        if previous_config is None:
            sys.modules.pop("app.core.config", None)
        else:
            sys.modules["app.core.config"] = previous_config


resolve_database_url = _load_database_module_without_project_settings().resolve_database_url


def test_relative_sqlite_database_is_anchored_to_project_root_and_ignores_cwd(tmp_path, monkeypatch):
    database_url = "sqlite:///./food_redist.db"

    from_project_root = resolve_database_url(database_url)
    monkeypatch.chdir(tmp_path)
    from_other_cwd = resolve_database_url(database_url)

    expected_path = (_PROJECT_ROOT / "food_redist.db").resolve()
    assert Path(from_project_root.database) == expected_path
    assert Path(from_other_cwd.database) == expected_path


def test_absolute_sqlite_database_is_unchanged(tmp_path):
    database_path = (tmp_path / "absolute.db").resolve()
    database_url = f"sqlite:///{database_path.as_posix()}"

    resolved = resolve_database_url(database_url)

    assert resolved == make_url(database_url)
    assert Path(resolved.database) == database_path


def test_in_memory_sqlite_database_stays_in_memory():
    database_url = "sqlite://"
    resolved = resolve_database_url(database_url)

    assert resolved == make_url(database_url)
    assert resolved.database is None


def test_memory_sqlite_database_stays_in_memory():
    database_url = "sqlite:///:memory:"

    resolved = resolve_database_url(database_url)

    assert resolved == make_url(database_url)
    assert resolved.database == ":memory:"


def test_sqlite_uri_memory_database_is_unchanged():
    database_url = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

    resolved = resolve_database_url(database_url)

    assert resolved == make_url(database_url)
    assert resolved.database == "file:memdb1"
    assert resolved.query["mode"] == "memory"
    assert resolved.query["cache"] == "shared"
    assert resolved.query["uri"] == "true"


def test_postgresql_url_credentials_and_query_are_unchanged():
    database_url = (
        "postgresql://user%40example.com:p%40ss@db.example.com:5432/food"
        "?sslmode=require&application_name=food%20share"
    )
    expected = make_url(database_url)

    resolved = resolve_database_url(database_url)

    assert resolved == expected
    assert resolved.username == "user@example.com"
    assert resolved.password == "p@ss"
    assert resolved.query == expected.query


_ISOLATED_CONFIG_SETUP = """
import os
import sys
import types
from pathlib import Path

config_module = types.ModuleType("app.core.config")
config_module.PROJECT_ROOT = Path(os.environ["TEST_PROJECT_ROOT"])
config_module.settings = types.SimpleNamespace(
    PROJECT_NAME="Food Redistribution Platform",
    API_V1_STR="/api/v1",
    DATABASE_URL=os.environ["DATABASE_URL"],
    JWT_SECRET_KEY=os.environ["JWT_SECRET_KEY"],
    JWT_REFRESH_SECRET_KEY=os.environ["JWT_REFRESH_SECRET_KEY"],
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=7,
    CORS_ORIGINS=["http://localhost:5173"],
    FRONTEND_URL="http://localhost:5173",
    ADMIN_EMAIL=os.environ["ADMIN_EMAIL"],
    ADMIN_PASSWORD=os.environ["ADMIN_PASSWORD"],
    STORAGE_PROVIDER="local",
    UPLOAD_DIR=os.environ["UPLOAD_DIR"],
    AWS_ACCESS_KEY_ID="",
    AWS_SECRET_ACCESS_KEY="",
    AWS_S3_BUCKET_NAME="",
    AWS_REGION="us-east-1",
    EMAIL_PROVIDER="console",
    SMTP_HOST="localhost",
    SMTP_PORT=25,
    SMTP_USERNAME="",
    SMTP_PASSWORD="",
    SMTP_FROM_EMAIL="no-reply@example.org",
    ENV="test",
    RATE_LIMIT_ENABLED=False,
    RATE_LIMIT_WINDOW_SECONDS=60,
    RATE_LIMIT_LOGIN_MAX_REQUESTS=10,
    RATE_LIMIT_REGISTER_MAX_REQUESTS=5,
    RATE_LIMIT_UPLOAD_MAX_REQUESTS=20,
    RATE_LIMIT_QR_MAX_REQUESTS=30,
)
sys.modules["app.core.config"] = config_module
"""


def _isolated_environment(project_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    pythonpath = [str(_BACKEND_ROOT)]
    if environment.get("PYTHONPATH"):
        pythonpath.append(environment["PYTHONPATH"])
    environment.update(
        {
            "DATABASE_URL": "sqlite:///./food_redist.db",
            "ENV": "test",
            "ADMIN_EMAIL": _ADMIN_EMAIL,
            "ADMIN_PASSWORD": _ADMIN_PASSWORD,
            "JWT_SECRET_KEY": "isolated-test-access-secret-1234567890",
            "JWT_REFRESH_SECRET_KEY": "isolated-test-refresh-secret-1234567890",
            "CORS_ORIGINS": "http://localhost:5173",
            "FRONTEND_URL": "http://localhost:5173",
            "RATE_LIMIT_ENABLED": "false",
            "EMAIL_PROVIDER": "console",
            "STORAGE_PROVIDER": "local",
            "UPLOAD_DIR": str(project_root / "uploads"),
            "TEST_PROJECT_ROOT": str(project_root),
            "PYTHONPATH": os.pathsep.join(pythonpath),
        }
    )
    return environment


def _run_isolated_step(name: str, script: str, cwd: Path, environment: dict[str, str]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(_ISOLATED_CONFIG_SETUP) + textwrap.dedent(script),
        ],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
    )
    output = f"{result.stdout}\n{result.stderr}".replace(_ADMIN_EMAIL, "[redacted-email]")
    output = output.replace(_ADMIN_PASSWORD, "[redacted-password]")
    assert result.returncode == 0, f"{name} failed with exit code {result.returncode}:\n{output}"


def test_relative_database_is_shared_by_migrations_bootstrap_and_api(tmp_path):
    """Exercise migration, bootstrap, and API processes against one temp file."""
    project_root = tmp_path / "simulated-project-root"
    backend_directory = project_root / "backend"
    backend_directory.mkdir(parents=True)
    environment = _isolated_environment(project_root)
    environment["ALEMBIC_CONFIG"] = str(_BACKEND_ROOT / "alembic.ini")
    environment["ALEMBIC_SCRIPT_LOCATION"] = str(_BACKEND_ROOT / "alembic")
    environment["ALEMBIC_VERSION_LOCATION"] = str(_BACKEND_ROOT / "alembic" / "versions")

    _run_isolated_step(
        "alembic upgrade",
        """
        import os

        from alembic import command
        from alembic.config import Config

        alembic_config = Config(os.environ["ALEMBIC_CONFIG"])
        alembic_config.set_main_option("script_location", os.environ["ALEMBIC_SCRIPT_LOCATION"])
        alembic_config.set_main_option("version_locations", os.environ["ALEMBIC_VERSION_LOCATION"])
        command.upgrade(alembic_config, "head")
        """,
        backend_directory,
        environment,
    )

    database_path = project_root / "food_redist.db"
    backend_database_path = backend_directory / "food_redist.db"
    assert database_path.is_file()
    assert not backend_database_path.exists()
    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version == ("0002_single_admin",)

    _run_isolated_step(
        "bootstrap_admin",
        """
        import os

        from bootstrap_admin import bootstrap_admin

        administrator = bootstrap_admin()
        assert administrator.email == os.environ["ADMIN_EMAIL"]
        """,
        project_root,
        environment,
    )

    _run_isolated_step(
        "API login and admin access",
        """
        import os

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                data={
                    "username": os.environ["ADMIN_EMAIL"],
                    "password": os.environ["ADMIN_PASSWORD"],
                },
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            profile = client.get("/api/v1/users/profile", headers=headers)
            assert profile.status_code == 200
            assert profile.json()["email"] == os.environ["ADMIN_EMAIL"]

            admin_users = client.get("/api/v1/admin/users", headers=headers)
            assert admin_users.status_code == 200
            assert [user["email"] for user in admin_users.json()] == [os.environ["ADMIN_EMAIL"]]
        """,
        backend_directory,
        environment,
    )
