# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import os
from typing import List


class MFDMapResolver:
    """
    Responsibility: Resolve active SUMO network topology (.net.xml) and discover
    real signalized traffic light junction IDs under CARINA active control.
    Adheres strictly to Single Responsibility Principle (SRP).
    """

    @staticmethod
    def discover_signalized_ids() -> List[str]:
        """
        Dynamically inspects active results directories to discover junctions
        with type="traffic_light" from SUMO network XML file.
        Returns empty list if discovery fails or no signalized junctions are found.
        """
        try:
            from utils.paths import get_base_output_dir

            results_dir = os.path.join(get_base_output_dir(), "results")
            if os.path.exists(results_dir):
                for root, dirs, files in os.walk(results_dir):
                    for f in files:
                        if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                            net_file = os.path.join(root, f)
                            try:
                                import sumolib

                                from utils.sumo_net_cache import read_sumo_net_cached

                                net = read_sumo_net_cached(
                                    net_file, reader_fn=sumolib.net.readNet, with_programs=False, with_internal=False
                                )
                                tls = [node.getID() for node in net.getNodes() if node.getType() == "traffic_light"]
                                if tls:
                                    logging.info(
                                        f"[MFDMapResolver] Dynamically discovered {len(tls)} signalized IDs from {net_file}: {tls}"
                                    )
                                    return tls
                            except Exception as e:
                                logging.debug(f"[MFDMapResolver] sumolib read error on {net_file}: {e}")
        except Exception as e:
            logging.warning(f"[MFDMapResolver] Error discovering signalized IDs: {e}", exc_info=True)

        logging.warning("[MFDMapResolver] No signalized junctions discovered in network map. Returning empty list.")
        return []
