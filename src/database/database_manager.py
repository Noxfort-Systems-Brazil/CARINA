# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/database/database_manager.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 1, 2025

import sqlite3
import logging
import os
from datetime import datetime
import sys
import configparser
from typing import TYPE_CHECKING, Any

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class DatabaseManager:
    """
    Gerencia todas as interações com o banco de dados (SQLite local ou PostgreSQL Remoto).
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend', db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        # Parse settings directly
        self.config = configparser.ConfigParser()
        settings_path = os.path.join(project_root_local, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)
            
        self.db_type = self.config.get("DATABASE", "db_type", fallback="sqlite")
        self.db_host = self.config.get("DATABASE", "db_host", fallback="localhost")
        self.db_port = self.config.get("DATABASE", "db_port", fallback="5432")
        self.db_user = self.config.get("DATABASE", "db_user", fallback="postgres")
        self.db_password = self.config.get("DATABASE", "db_password", fallback="")
        self.db_name_pg = self.config.get("DATABASE", "db_name", fallback="carina_data")
        
        # SQLite local path
        from src.utils.paths import get_base_output_dir
        db_dir = os.path.join(get_base_output_dir(), "results", "database")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, db_name)
        
        self._initialize_db()
        logging.info(f"[DB_MANAGER] Gerenciador Base Inicializado. Motor: {self.db_type}")

    def _get_connection(self) -> Any:
        """Retorna uma conexão (psycopg2 ou sqlite3) dependendo da config."""
        if self.db_type == "postgres":
            import psycopg2
            return psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                dbname=self.db_name_pg
            )
        else:
            return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        """
        Cria as tabelas necessárias no banco de dados com dialeto SQL específico.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if self.db_type == "postgres":
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id SERIAL PRIMARY KEY,
                    start_time TIMESTAMP NOT NULL,
                    scenario_name TEXT
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL REFERENCES simulation_runs(run_id),
                    episode_number INTEGER NOT NULL,
                    total_reward REAL,
                    end_time TIMESTAMP
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    report_id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL REFERENCES simulation_runs(run_id),
                    timestamp TIMESTAMP NOT NULL,
                    summary TEXT,
                    report_content TEXT
                );
                """)
            else:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    scenario_name TEXT
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    total_reward REAL,
                    end_time TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    summary TEXT,
                    report_content TEXT,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                );
                """)
            
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.init.db_error", error=e))
        finally:
            conn.close()

    def create_simulation_run(self, scenario_name: str) -> int | None:
        """
        Registra uma nova execução usando queries parametrizadas pelo dialeto.
        """
        lm = self.locale_manager
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            start_time = datetime.now()
            
            if self.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (%s, %s) RETURNING run_id;",
                    (start_time, scenario_name)
                )
                run_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (?, ?);",
                    (start_time, scenario_name)
                )
                run_id = cursor.lastrowid
                
            conn.commit()
            logging.info(lm.get_string("db_manager.create_run.success", scenario=scenario_name))
            return run_id
        except Exception as e:
            logging.error(lm.get_string("db_manager.create_run.error", error=e))
            return None
        finally:
            conn.close()

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        """Salva as métricas de um episódio finalizado no banco de dados."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            end_time = datetime.now()
            
            if self.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (%s, %s, %s, %s);",
                    (run_id, episode_number, total_reward, end_time)
                )
            else:
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (?, ?, ?, ?);",
                    (run_id, episode_number, total_reward, end_time)
                )
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.log_episode.error", episode=episode_number, error=e))
        finally:
            conn.close()
            
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        """Salva um relatório de análise de infraestrutura."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.now()
            
            if self.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (%s, %s, %s, %s);",
                    (run_id, timestamp, summary, report_content)
                )
            else:
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (?, ?, ?, ?);",
                    (run_id, timestamp, summary, report_content)
                )
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.log_report.error", error=e))
        finally:
            conn.close()