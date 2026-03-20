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

# File: src/sas/analyzer_engine.py (Lazy Import for Pandas/Sklearn)
# Author: Gabriel Moraes
# Date: October 24, 2025 # <-- DATE UPDATED

import logging
import os
import json
import configparser
from collections import defaultdict
from multiprocessing import Queue
import sys
from typing import TYPE_CHECKING, List, Dict

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Imports that are *not* heavy or essential to begin with
from analysis.infrastructure_analyzer import InfrastructureAnalyzer
from rendering.static_map_renderer import StaticMapRenderer
from utils.network_topology_parser import NetworkTopologyParser

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# --- CHANGE 1: Check availability WITHOUT importing at the top ---
# Try to import just to set the flag, but it doesn't maintain the global import
SKLEARN_AVAILABLE = False
try:
    # It just checks if the modules exist, doesn't permanently load them here
    import importlib
    importlib.import_module('pandas')
    importlib.import_module('sklearn.linear_model')
    SKLEARN_AVAILABLE = True
    logging.debug("[ANALYZER_ENGINE] Pandas e Scikit-learn detectados.")
except ImportError:
    logging.warning("[ANALYZER_ENGINE] Bibliotecas 'pandas' ou 'sklearn' não encontradas. Calibração do heatmap desativada.")
# --- END OF CHANGE 1 ---

class AnalyzerEngine:
    """Executa a análise de infraestrutura e gera os arquivos de resultado."""

    def __init__(self, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.analyzer = InfrastructureAnalyzer(self.settings, self.locale_manager)
        self.map_renderer = StaticMapRenderer(self.locale_manager)
        self.topology_parser = NetworkTopologyParser(self.locale_manager)
        self.db_data_queue = db_data_queue

        self.scenario_dir = None
        self.analysis_dir = None
        self.cache_path = None
        self.ui_status_path = None

        # Log message about sklearn moved to above check
        logging.info(lm.get_string("sas_engine.init.engine_created"))

    def run_analysis(self, accumulated_data: dict, sim_duration: float, scenario_name: str,
                     net_file_path: str, run_id: int, calibration_data_points: list):
        lm = self.locale_manager

        if sim_duration <= 0 or not net_file_path:
            logging.warning(lm.get_string("sas_engine.run.analysis_skipped_no_data"))
            return

        from src.utils.paths import get_base_output_dir
        self.scenario_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
        self.analysis_dir = os.path.join(self.scenario_dir, "infrastructure_analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)
        self.cache_path = os.path.join(self.analysis_dir, "analysis_cache.json")
        self.ui_status_path = os.path.join(self.analysis_dir, "analysis_status.json")

        processed_data, true_traffic_light_ids = self._process_accumulated_data(accumulated_data, sim_duration, net_file_path)

        last_analysis_cache = self._load_cache()

        analysis_result = self.analyzer.analyze_collected_data(
            collected_data=processed_data,
            last_analysis_cache=last_analysis_cache,
            scenario_name=scenario_name,
            true_traffic_light_ids=true_traffic_light_ids
        )

        try:
            log_payload = { "run_id": run_id, "summary": analysis_result.get("summary", "N/A"), "report_content": analysis_result.get("report_content", "") }
            data_packet = {"type": "log_report", "payload": log_payload}
            self.db_data_queue.put(data_packet)
            logging.info(lm.get_string("sas_engine.run.report_sent_to_db"))
        except Exception as e:
            logging.error(lm.get_string("sas_engine.run.db_queue_error", error=e))

        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            self._generate_planning_map(analysis_result["analysis_results"], net_file_path)

        self._save_cache(analysis_result.get("new_cache_data", {}))
        self._notify_ui(analysis_result)

        # Only attempts to calibrate if SKLEARN_AVAILABLE is True AND there is data
        if SKLEARN_AVAILABLE and calibration_data_points:
            new_weights = self._calibrate_heatmap_weights(calibration_data_points)
            if new_weights:
                self._save_live_weights(new_weights)

        logging.info(lm.get_string("sas_engine.run.analysis_complete"))

    def _calibrate_heatmap_weights(self, data_points: List[Dict]) -> Dict | None:
        # --- CHANGE 2: Import pandas and sklearn HERE ---
        # Ensures we only import if SKLEARN_AVAILABLE is True (already before checked calling)
        try:
            import pandas as pd
            from sklearn.linear_model import LinearRegression
        except ImportError:
             # This shouldn't happen if SKLEARN_AVAILABLE is True, but it's extra security
             logging.error("[ANALYZER_ENGINE] Falha ao importar pandas/sklearn DENTRO da calibração.")
             return None
        # --- END OF CHANGE 2 ---

        logging.info(f"[ANALYZER_ENGINE] Iniciando calibração do mapa de calor com {len(data_points)} pontos de dados.")
        if len(data_points) < 100: # Minimum points for a minimally stable regression
            logging.warning(f"[ANALYZER_ENGINE] Dados insuficientes para calibração (< 100 pontos, temos {len(data_points)}). Abortando.")
            return None
        try:
            df = pd.DataFrame(data_points)
            # Data cleaning (important!)
            df.replace([float('inf'), -float('inf')], float('nan'), inplace=True) # Replace infinities with NaN
            df.dropna(inplace=True) # Remove lines with NaN

            if df.empty or len(df) < 2: # Need at least 2 points for regression
                logging.warning("[ANALYZER_ENGINE] Nenhum dado válido restante após a limpeza ou dados insuficientes. Abortando calibração.")
                return None

            features = ['occupancy', 'waiting_time', 'flow']
            target = 'bad_events' # Bad events (teleports + braking)

            # Ensures columns exist
            if not all(feat in df.columns for feat in features) or target not in df.columns:
                 logging.error(f"[ANALYZER_ENGINE] Colunas necessárias ({features + [target]}) não encontradas no DataFrame. Colunas presentes: {df.columns.tolist()}. Abortando calibração.")
                 return None

            X = df[features]
            y = df[target]

            # Add simple data validation
            if X.isnull().values.any() or y.isnull().values.any():
                 logging.warning("[ANALYZER_ENGINE] Dados NaN encontrados mesmo após dropna. Abortando calibração.")
                 return None
            if not pd.api.types.is_numeric_dtype(y):
                 logging.warning(f"[ANALYZER_ENGINE] Coluna target '{target}' não é numérica. Abortando calibração.")
                 return None
            if not all(pd.api.types.is_numeric_dtype(X[col]) for col in X.columns):
                 logging.warning(f"[ANALYZER_ENGINE] Uma ou mais colunas de features não são numéricas. Abortando calibração.")
                 return None


            # Linear Regression with non-negative coefficients for occupancy and waiting_time
            # (Flow can be negative, indicating that more flow reduces "bad_events")
            model = LinearRegression(positive=False) # Allows negative coefficients
            model.fit(X, y)

            # Ensures that occupancy and waiting time weights are >= 0
            coef_occupancy = max(0.0, model.coef_[0])
            coef_waiting = max(0.0, model.coef_[1])
            coef_flow = model.coef_[2] # Flow can be negative

            # Normalizes the weights so that they add up (in absolute value) to approximately 1 or a reasonable value
            # This prevents very large weights from dominating the calculation
            total_abs_weight = abs(coef_occupancy) + abs(coef_waiting) + abs(coef_flow)
            if total_abs_weight > 1e-6: # Avoid dividing by zero
                 norm_factor = 3.0 / total_abs_weight # Scale so that the sum of absolute values ​​is ~3 (similar to the original weights)
                 coef_occupancy *= norm_factor
                 coef_waiting *= norm_factor
                 coef_flow *= norm_factor


            # Assembles the final dictionary, ensuring that the flow weight is negative
            new_weights = {
                'weight_occupancy': round(coef_occupancy, 4),
                'weight_waiting_time': round(coef_waiting, 4),
                'weight_flow': round(-abs(coef_flow), 4) # Ensures that flow is negative or zero
            }

            logging.info(f"[ANALYZER_ENGINE] Calibração concluída. Novos pesos do mapa de calor: {new_weights}")
            return new_weights

        except Exception as e:
            logging.error(f"[ANALYZER_ENGINE] Erro durante a calibração do mapa de calor: {e}", exc_info=True)
            return None

    def _save_live_weights(self, weights: Dict):
        # Ensures the scenario directory exists
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário não definido ou não existe. Não é possível salvar pesos.")
            return

        live_weights_path = os.path.join(self.scenario_dir, "heatmap_weights_live.json")
        try:
            with open(live_weights_path, "w", encoding="utf-8") as f:
                json.dump(weights, f, indent=4)
            logging.info(f"[ANALYZER_ENGINE] Pesos do mapa de calor ao vivo salvos em: {live_weights_path}")
        except IOError as e:
            logging.error(f"[ANALYZER_ENGINE] Falha ao salvar os pesos do mapa de calor ao vivo: {e}")

    def _process_accumulated_data(self, accumulated_data: dict, sim_duration: float, net_file_path: str) -> tuple[dict, list]:
        lm = self.locale_manager
        logging.info(lm.get_string("sas_engine.run.processing_data"))

        # --- AMENDED: Now call the external expert ---
        junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)

        if not junction_types or not junction_incoming_edges:
            logging.error(lm.get_string("sas_engine.topology.cannot_continue_error"))
            return {}, []

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        processed_data = {}
        sim_duration_hours = sim_duration / 3600.0 if sim_duration > 0 else 1.0

        # Calculates metrics per join (maintained logic)
        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges: continue
            # Sort incoming streets by number of lanes (proxy for main/secondary)
            sorted_edges = sorted(incoming_edges.items(), key=lambda item: item[1]['num_lanes'], reverse=True)
            max_lanes = sorted_edges[0][1]['num_lanes'] if sorted_edges else 0
            primary_lanes, secondary_lanes = [], []
            for edge_id, edge_data in sorted_edges:
                if edge_data['num_lanes'] == max_lanes: primary_lanes.extend(edge_data['lanes'])
                else: secondary_lanes.extend(edge_data['lanes'])

            # Sums vehicles that left the primary and secondary lanes
            primary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in primary_lanes)
            secondary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in secondary_lanes)
            # Adds waiting time only on secondary lanes
            secondary_wait_time = sum(accumulated_data.get('total_waiting_time_per_lane', {}).get(lane, 0) for lane in secondary_lanes)

            # Calculates hourly or average metrics
            vol_primary = int(primary_vehicles / sim_duration_hours)
            vol_secondary = int(secondary_vehicles / sim_duration_hours)
            avg_delay_secondary = (secondary_wait_time / secondary_vehicles) if secondary_vehicles > 0 else 0

            # Adds processed data to the dictionary
            processed_data[j_id] = {
                "volume": vol_primary, # Main track volume (now called 'volume')
                "vol_secondary": vol_secondary, # Secondary road volume
                "avg_delay": avg_delay_secondary, # Average delay only in secondary
                "conflict_events": accumulated_data.get('conflict_events_per_junction', {}).get(j_id, 0), # Junction conflict events
                "type": junction_types.get(j_id, 'unknown') # Joint type
            }

        logging.info(lm.get_string("sas_engine.run.data_processed", count=len(processed_data)))
        return processed_data, true_traffic_light_ids

    def _generate_planning_map(self, analysis_results: dict, net_file_path: str):
        lm = self.locale_manager
        # Ensures we have a valid scenario directory
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário inválido. Não é possível gerar mapa de planejamento.")
            return

        logging.info(lm.get_string("sas_engine.map.generating"))
        # Maps recommendations to icon types
        rec_add = lm.get_string("warrant_evaluator.rec_add")
        rec_remove = lm.get_string("warrant_evaluator.rec_remove")
        icon_requests = {
            j_id: "add" if rec_add in r.get('recommendation', '') else "remove" if rec_remove in r.get('recommendation', '') else "existing"
            for j_id, r in analysis_results.items()
        }
        if net_file_path:
            self.map_renderer.create_map_with_icons(
                net_file_path=net_file_path,
                scenario_results_dir=self.scenario_dir, # Use the scenario directory
                icon_requests=icon_requests,
                output_filename="map_planning.png" # Output file name
            )
        else:
             logging.warning("[ANALYZER_ENGINE] Caminho do net_file não disponível. Mapa de planejamento não gerado.")


    def _load_cache(self) -> dict:
        if not self.cache_path or not os.path.exists(self.cache_path): return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f: return json.load(f)
        except (json.JSONDecodeError, IOError): return {}

    def _save_cache(self, cache_data: dict):
        if not cache_data or not self.cache_path: return
        try:
            # Ensures the directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f: json.dump(cache_data, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.cache.save_error"))

    def _notify_ui(self, analysis_result: dict):
        if not analysis_result or not analysis_result.get("analysis_results") or not self.ui_status_path: return
        try:
            # Ensures the directory exists
            os.makedirs(os.path.dirname(self.ui_status_path), exist_ok=True)
            with open(self.ui_status_path, "w", encoding="utf-8") as f: json.dump(analysis_result, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.ui.status_save_error"))