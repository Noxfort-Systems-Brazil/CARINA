# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_launcher_single_instance.py
# Author: Gabriel Moraes
# Date: September 2026

import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from launcher.single_instance import SingleInstanceLock


def test_single_instance_lock_acquire_and_release():
    """Tests acquiring and releasing single instance TCP lock on a free port."""
    lock = SingleInstanceLock(port=43999, host="127.0.0.1")
    acquired = lock.acquire()
    assert acquired is True
    assert lock.server_socket is not None

    # Releasing should close the socket
    lock.release()
    assert lock.server_socket is None


def test_single_instance_lock_secondary_instance_detection():
    """Tests that a secondary instance fails to acquire and sends restore_ui signal."""
    # First instance
    lock1 = SingleInstanceLock(port=43998, host="127.0.0.1")
    assert lock1.acquire() is True

    shutdown_ev = threading.Event()
    restore_ev = threading.Event()
    lock1.start_restore_listener(shutdown_requested=shutdown_ev, restore_requested=restore_ev)

    time.sleep(0.1)

    # Second instance attempts acquire on same port
    lock2 = SingleInstanceLock(port=43998, host="127.0.0.1")
    acquired2 = lock2.acquire()
    assert acquired2 is False

    # Wait for the listener to receive the restore signal
    restore_ev.wait(timeout=2.0)
    assert restore_ev.is_set() is True

    shutdown_ev.set()
    lock1.release()
    lock2.release()


def test_single_instance_release_when_already_none():
    """Tests release() safely handles uninitialized or already released socket."""
    lock = SingleInstanceLock(port=43997, host="127.0.0.1")
    lock.release()  # should not throw
    assert lock.server_socket is None
