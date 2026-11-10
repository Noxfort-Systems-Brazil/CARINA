# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Setup sys.path so CARINA packages are accessible
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = None


def get_database_url() -> str:
    """Builds the database URL based on environment variables or settings.ini."""
    # 1. Environment variables override
    db_type = os.getenv("CARINA_DB_TYPE")
    db_host = os.getenv("CARINA_DB_HOST")
    db_port = os.getenv("CARINA_DB_PORT")
    db_user = os.getenv("CARINA_DB_USER")
    db_password = os.getenv("CARINA_DB_PASSWORD")
    db_name = os.getenv("CARINA_DB_NAME")

    # 2. settings.ini fallback
    settings_path = os.path.join(base_dir, "config", "settings.ini")
    if not db_type and os.path.exists(settings_path):
        parser = configparser.ConfigParser()
        parser.read(settings_path)
        if parser.has_section("DATABASE"):
            db_type = parser.get("DATABASE", "db_type", fallback="sqlite")
            db_host = parser.get("DATABASE", "db_host", fallback="localhost")
            db_port = parser.get("DATABASE", "db_port", fallback="5432")
            db_user = parser.get("DATABASE", "db_user", fallback="admin")
            db_password = parser.get("DATABASE", "db_password", fallback="admin")
            db_name = parser.get("DATABASE", "db_name", fallback="carina_data")

    db_type = db_type or "sqlite"

    if db_type == "postgres":
        host = db_host or "localhost"
        port = db_port or "5432"
        user = db_user or "admin"
        password = db_password or "admin"
        name = db_name or "carina_data"
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    else:
        # SQLite
        from src.utils.paths import get_base_output_dir

        db_dir = os.path.join(get_base_output_dir(), "results", "database")
        os.makedirs(db_dir, exist_ok=True)
        sqlite_file = os.path.join(db_dir, "carina_data.db")
        return f"sqlite:///{sqlite_file}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url", get_database_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    custom_url = config.get_main_option("sqlalchemy.url")
    if custom_url and custom_url != "sqlite:///results/database/carina_data.db":
        override_url = custom_url
    else:
        override_url = get_database_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = override_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        db_schema = os.getenv("CARINA_DB_SCHEMA", "schema_carina")
        is_postgres = connectable.dialect.name == "postgresql"

        if is_postgres:
            safe_schema = "".join(c for c in db_schema if c.isalnum() or c == "_") or "schema_carina"
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}"'))
            connection.execute(text(f'SET search_path TO "{safe_schema}", public'))
            connection.commit()

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema=safe_schema,
            )
        else:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
