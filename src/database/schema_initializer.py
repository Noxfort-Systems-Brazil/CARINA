# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Any, Optional


class DatabaseSchemaInitializer:
    """Handles database schema bootstrap, JSON table/index creation, and Alembic migrations."""

    @staticmethod
    def load_schema_config() -> dict:
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(base_dir, "config", "database", "schema_queries.json"),
                os.path.join(base_dir, "config", "schema_queries.json"),
            ]
            for json_path in candidates:
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception as e:
            logging.error(f"[SCHEMA_INIT] Failed to load schema_queries.json: {e}", exc_info=True)
        return {}

    @classmethod
    def apply_migrations(cls, engine: Any, db_url: Optional[str] = None) -> bool:
        """Applies pending Alembic database migrations up to 'head'."""
        try:
            from alembic import command
            from alembic.config import Config

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            alembic_ini_path = os.path.join(project_root, "alembic.ini")
            if not os.path.exists(alembic_ini_path):
                return False

            alembic_cfg = Config(alembic_ini_path)
            if not db_url:
                if engine.db_type == "sqlite" and engine.db_path:
                    db_url = f"sqlite:///{os.path.abspath(engine.db_path)}"
                elif engine.db_type == "postgres" and hasattr(engine, "db_host") and engine.db_host:
                    db_url = (
                        f"postgresql://{engine.db_user}:{engine.db_password}@{engine.db_host}:{engine.db_port}/{engine.db_name_pg}"
                    )

            if db_url:
                alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            try:
                command.upgrade(alembic_cfg, "head")
            except Exception as up_err:
                if "already exists" in str(up_err).lower():
                    # If tables were pre-created by fallback bootstrap, stamp to head
                    command.stamp(alembic_cfg, "head")
                    logging.info("[DB_ENGINE] Baseline schema already existed; stamped Alembic version to 'head'.")
                else:
                    raise up_err

            logging.info("[DB_ENGINE] Alembic migrations successfully applied to 'head'.")
            return True
        except Exception as e:
            logging.warning(f"[DB_ENGINE] Alembic migration skipped or failed: {e}", exc_info=True)
            return False

    @classmethod
    def initialize_db(cls, engine: Any) -> None:
        """Initializes tables, migrations, and indexes dynamically from queries and Alembic."""
        conn = engine.get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            # Ensure PostgreSQL schema exists and search_path is set
            if engine.db_type == "postgres":
                safe_schema = "".join(c for c in engine.db_schema if c.isalnum() or c == "_") or "schema_carina"
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}";')
                cursor.execute(f'SET search_path TO "{safe_schema}", public;')
                conn.commit()

            if engine.run_migrations:
                try:
                    cls.apply_migrations(engine)
                except Exception as mig_err:
                    logging.warning(f"[DB_ENGINE] Failed to apply migrations: {mig_err}", exc_info=True)

            schema_config = cls.load_schema_config()
            dialect_config = schema_config.get(engine.db_type, schema_config.get("sqlite", {}))

            for table_sql in dialect_config.get("tables", []):
                try:
                    cursor.execute(table_sql)
                    conn.commit()
                except Exception:
                    pass

            # Migrations
            migrations = dialect_config.get("migrations", [])
            if engine.db_type == "postgres":
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'synapse_fluid_dynamics'
                      AND table_schema = CURRENT_SCHEMA;
                """
                )
                existing_cols = {row[0] for row in cursor.fetchall()}
                for m in migrations:
                    if isinstance(m, dict) and m.get("column") not in existing_cols:
                        try:
                            cursor.execute(m["sql"])
                            conn.commit()
                        except Exception:
                            pass
            else:
                for migration_sql in migrations:
                    sql_stmt = migration_sql if isinstance(migration_sql, str) else migration_sql.get("sql")
                    try:
                        cursor.execute(sql_stmt)
                        conn.commit()
                    except Exception:
                        pass

            # Indexes
            for index_sql in dialect_config.get("indexes", []):
                cursor.execute(index_sql)
                conn.commit()

        except Exception as e:
            if conn and hasattr(conn, "rollback"):
                conn.rollback()
            logging.error(f"[DB_ENGINE] Error during _initialize_db: {e}", exc_info=True)
            try:
                logging.error(engine.locale_manager.get_string("db_manager.init.db_error", error=e), exc_info=True)
            except Exception:
                pass
        finally:
            if conn and hasattr(conn, "close"):
                conn.close()
