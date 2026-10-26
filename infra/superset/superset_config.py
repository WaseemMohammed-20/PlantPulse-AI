import os
from pathlib import Path

SUPERSET_HOME = Path(os.environ.get("SUPERSET_HOME", "/app/superset_home"))
SUPERSET_HOME.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Set SUPERSET_SECRET_KEY in infra/superset/.env before starting Superset."
    )

SQLALCHEMY_DATABASE_URI = f"sqlite:///{SUPERSET_HOME / 'superset.db'}"
