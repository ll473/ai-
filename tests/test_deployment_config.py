from pathlib import Path

from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_image_copies_valid_alembic_configuration() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    config = Config(PROJECT_ROOT / "alembic.ini")

    assert any(
        line.split() == [
            "COPY",
            "pyproject.toml",
            "uv.lock",
            "README.md",
            "alembic.ini",
            "./",
        ]
        for line in dockerfile.splitlines()
    )
    assert config.get_main_option("script_location") == "backend/alembic"
