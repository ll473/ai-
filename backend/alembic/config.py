from alembic.config import Config


def set_database_url(config: Config, database_url: str) -> None:
    """Write a URL without changing the value returned by Alembic config."""
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
