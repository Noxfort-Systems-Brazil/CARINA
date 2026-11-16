# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Hardware-In-the-Loop (HIL) Loopback Integration Test:
Python GoGatewayClient <-> OS Pipes <-> Compiled bin/carina-go <-> Real UDP SNMPv2c Responder.

Note: Validates full IPC + SNMP BER serialization + Watchdog/Failsafe + SNMP Trap ingestion
over loopback UDP sockets without requiring a physical roadside signal cabinet.
"""

import os
import socket
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from src.drivers.go_gateway_client import GoGatewayClient


def _encode_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, val: bytes) -> bytes:
    return bytes([tag]) + _encode_len(len(val)) + val


def _encode_int(v: int) -> bytes:
    if v == 0:
        return _tlv(0x02, b"\x00")
    raw = v.to_bytes((v.bit_length() + 8) // 8, "big", signed=True)
    return _tlv(0x02, raw)


def _encode_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.strip(".").split(".")]
    out = bytearray([parts[0] * 40 + parts[1]])
    for sub in parts[2:]:
        if sub == 0:
            out.append(0)
            continue
        chunks = []
        while sub > 0:
            chunks.append(sub & 0x7F)
            sub >>= 7
        for i in range(len(chunks) - 1, -1, -1):
            out.append(chunks[i] | (0x80 if i > 0 else 0))
    return _tlv(0x06, bytes(out))


def _decode_tlv(buf: bytes, offset: int) -> Tuple[int, bytes, int]:
    tag = buf[offset]
    length_byte = buf[offset + 1]
    pos = offset + 2
    if length_byte < 0x80:
        length = length_byte
    else:
        num = length_byte & 0x7F
        length = int.from_bytes(buf[pos : pos + num], "big")
        pos += num
    return tag, buf[pos : pos + length], pos + length


def _decode_oid(raw: bytes) -> str:
    parts = [raw[0] // 40, raw[0] % 40]
    acc = 0
    for b in raw[1:]:
        acc = (acc << 7) | (b & 0x7F)
        if not (b & 0x80):
            parts.append(acc)
            acc = 0
    return ".".join(str(p) for p in parts)


def _decode_int(raw: bytes) -> int:
    return int.from_bytes(raw, "big", signed=True)


class _LoopbackSNMPAgent:
    """Minimal RFC 3416 SNMPv2c UDP responder & trap emitter for Go HIL verification."""

    def __init__(self, initial_oids: Dict[str, Tuple[int, bytes]]):
        self.oids = dict(initial_oids)
        self.sets_received: List[Tuple[str, int]] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("127.0.0.1", 0))
        self.port = self._sock.getsockname()[1]
        self._sock.settimeout(0.2)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._sock.close()

    def send_trap_v2(self, trap_port: int, trap_oid: str, detail_oid: str, detail_msg: str) -> None:
        vbl = _tlv(
            0x30,
            _tlv(0x30, _encode_oid("1.3.6.1.2.1.1.3.0") + _tlv(0x43, (12345).to_bytes(2, "big")))
            + _tlv(0x30, _encode_oid("1.3.6.1.6.3.1.1.4.1.0") + _encode_oid(trap_oid))
            + _tlv(0x30, _encode_oid(detail_oid) + _tlv(0x04, detail_msg.encode("utf-8"))),
        )
        pdu = _tlv(0xA7, _encode_int(77) + _encode_int(0) + _encode_int(0) + vbl)
        pkt = _tlv(0x30, _encode_int(1) + _tlv(0x04, b"public") + pdu)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(pkt, ("127.0.0.1", trap_port))

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr) -> None:
        _, msg, _ = _decode_tlv(data, 0)
        _, ver_raw, pos = _decode_tlv(msg, 0)
        _, comm_raw, pos = _decode_tlv(msg, pos)
        pdu_tag, pdu_body, _ = _decode_tlv(msg, pos)

        _, req_id_raw, pos = _decode_tlv(pdu_body, 0)
        _, _, pos = _decode_tlv(pdu_body, pos)
        _, _, pos = _decode_tlv(pdu_body, pos)
        _, vbl_raw, _ = _decode_tlv(pdu_body, pos)

        resp_vbs = []
        vpos = 0
        while vpos < len(vbl_raw):
            _, vb, vpos = _decode_tlv(vbl_raw, vpos)
            _, oid_raw, opos = _decode_tlv(vb, 0)
            vtag, val_raw, _ = _decode_tlv(vb, opos)
            oid_str = _decode_oid(oid_raw)

            if pdu_tag == 0xA3:  # SetRequest
                val_int = _decode_int(val_raw)
                self.sets_received.append((oid_str, val_int))
                self.oids[oid_str] = (
                    0x02,
                    val_int.to_bytes(max(1, (val_int.bit_length() + 8) // 8), "big", signed=True),
                )
                resp_vbs.append(_tlv(0x30, _encode_oid(oid_str) + _tlv(vtag, val_raw)))
            else:  # GetRequest
                if oid_str in self.oids:
                    rtag, rval = self.oids[oid_str]
                    resp_vbs.append(_tlv(0x30, _encode_oid(oid_str) + _tlv(rtag, rval)))
                else:
                    resp_vbs.append(_tlv(0x30, _encode_oid(oid_str) + _tlv(0x80, b"")))

        resp_pdu = _tlv(0xA2, _tlv(0x02, req_id_raw) + _encode_int(0) + _encode_int(0) + _tlv(0x30, b"".join(resp_vbs)))
        resp_pkt = _tlv(0x30, _tlv(0x02, ver_raw) + _tlv(0x04, comm_raw) + resp_pdu)
        self._sock.sendto(resp_pkt, addr)


def _find_free_port(proto: int) -> int:
    with socket.socket(socket.AF_INET, proto) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_compiled_go_gateway_full_snmp_loopback_lifecycle(monkeypatch):
    binary_path = Path("bin/carina-go").resolve()
    if not binary_path.exists():
        pytest.skip("bin/carina-go binary not present")

    trap_port = _find_free_port(socket.SOCK_DGRAM)
    web_port = _find_free_port(socket.SOCK_STREAM)
    monkeypatch.setenv("CARINA_TRAP_PORT", str(trap_port))
    monkeypatch.setenv("CARINA_GATEWAY_PORT", str(web_port))
    monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "hil-loopback-token")

    agent = _LoopbackSNMPAgent(
        {
            "1.3.6.1.2.1.1.1.0": (0x04, b"Econolite ASC/3 NTCIP Controller"),
            "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1": (0x04, b"\x05"),  # greens = 5
            "1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1": (0x02, b"\x02"),  # yellows = 2
            "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1": (0x02, b"\x08"),  # reds = 8
            "1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1": (0x02, b"\x00"),  # ped_calls = 0
        }
    )
    agent.start()

    client = GoGatewayClient(binary_path=str(binary_path))
    trap_events = []
    client.register_ui_callback(lambda ev: trap_events.append(ev) if ev.get("event_type") == "trap" else None)

    try:
        assert client.start() is True
        assert client.ping() is True

        # 1. Explicit NTCIP connection to closed port must fail Probe() immediately
        dead_conn = client.connect_intersection(
            intersection_id="J_DEAD",
            ip="127.0.0.1",
            port=1,
            protocol="NTCIP 1202",
            green_stages=[0, 1],
        )
        assert dead_conn.get("success") is False

        # 2. Connect via auto discovery against loopback UDP SNMP responder
        conn_res = client.connect_intersection(
            intersection_id="J_LOOP",
            ip="127.0.0.1",
            port=agent.port,
            community="public",
            protocol="auto",
            green_stages=[0, 1],
        )
        assert conn_res.get("success") is True, f"Connect failed: {conn_res}"
        assert conn_res["data"]["protocol"] == "NTCIP 1202"
        assert conn_res["data"]["brand"] == "Econolite"

        # 3. Telemetry query returns decoded binary OCTET STRING green bitmask
        tel = client.get_telemetry("J_LOOP")
        assert tel["status"] == "online"
        assert tel["active_greens"] == 5

        # 4. Logical action HOLD & NEXT_STAGE transmit real SNMP SET PDUs (NTCIP hold=.5.1.4.1, force_off=.5.1.5.1)
        assert client.apply_logical_action("J_LOOP", action=1, current_stage_idx=0, green_stages=[0, 1]) is True
        assert any(oid == "1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1" and val == 34 for oid, val in agent.sets_received)
        assert client.apply_logical_action("J_LOOP", action=0, current_stage_idx=0, green_stages=[0, 1]) is True
        assert any(oid == "1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1" for oid, _ in agent.sets_received)

        # 5. Send real UDP SNMPv2c Trap to CARINA_TRAP_PORT and confirm async push event over OS pipe
        agent.send_trap_v2(
            trap_port,
            "1.3.6.1.4.1.1206.4.2.1.99",
            "1.3.6.1.4.1.1206.4.2.1.1.1",
            "MMU Conflict Flash",
        )
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not trap_events:
            time.sleep(0.05)
        assert len(trap_events) >= 1, "Expected TrapListener on CARINA_TRAP_PORT to forward trap_alert"
        assert trap_events[0]["intersection_id"] == "J_LOOP"

        # 6. Emergency release preserves driver & trap listener while releasing controller, and resume recovers heartbeat
        assert client.emergency_release_all() is True
        assert client.resume_control_all() is True

        # Wait briefly for at least one heartbeat pulse SET (.2.1.21.1 = 1) after resume
        deadline = time.monotonic() + 2.8
        hb_oid = "1.3.6.1.4.1.1206.4.2.1.1.2.1.21.1"
        count_before_wait = sum(1 for oid, _ in agent.sets_received if oid == hb_oid)
        while time.monotonic() < deadline:
            if sum(1 for oid, _ in agent.sets_received if oid == hb_oid) > count_before_wait:
                break
            time.sleep(0.1)
        assert (
            sum(1 for oid, _ in agent.sets_received if oid == hb_oid) > count_before_wait
        ), "Expected heartbeat SET pulse to resume after resume_control_all()"

        assert client.disconnect_intersection("J_LOOP") is True
    finally:
        client.stop()
        agent.stop()
