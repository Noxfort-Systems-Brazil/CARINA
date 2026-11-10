# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import ipaddress
import re
from typing import Tuple


class NetworkAddressParser:
    """
    Utility for parsing, extracting, and validating IPv4 network addresses and port numbers
    from user input strings.
    """

    @staticmethod
    def parse_and_validate_ip(target_ip: str, default_port: int = 161) -> Tuple[bool, str, int, str]:
        """
        Parses an input string to extract a valid IPv4 address and port number.

        Args:
            target_ip (str): Raw user-provided IP string (e.g., '192.168.1.10:161').
            default_port (int): Default TCP/UDP port if omitted in input.

        Returns:
            Tuple[bool, str, int, str]:
                - is_valid (bool): True if valid IPv4, False otherwise.
                - connect_ip (str): Extracted IP address string (or '' if invalid).
                - connect_port (int): Extracted port integer (or default_port).
                - clean_saved (str): Formatted IP string (e.g. '192.168.1.10:80161' or '192.168.1.10').
        """
        if not target_ip or not isinstance(target_ip, str):
            return False, "", default_port, ""

        ip_port_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?", target_ip)
        if not ip_port_match:
            return False, "", default_port, ""

        connect_ip = ip_port_match.group(1)
        connect_port = int(ip_port_match.group(2)) if ip_port_match.group(2) else default_port

        try:
            ipaddress.ip_address(connect_ip)
        except ValueError:
            return False, "", default_port, ""

        clean_saved = f"{connect_ip}:{connect_port}" if connect_port != default_port else connect_ip
        return True, connect_ip, connect_port, clean_saved
