# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib
import importlib.abc
import importlib.machinery
import os
import sys


class _AliasLoader(importlib.abc.Loader):
    """Loader that aliases `src.<module>` to `<module>` in `sys.modules`."""

    def __init__(self, target_name: str, alias_name: str):
        self.target_name = target_name
        self.alias_name = alias_name

    def create_module(self, spec):
        mod = importlib.import_module(self.target_name)
        sys.modules[self.alias_name] = mod
        parent_name, _, child_name = self.alias_name.rpartition(".")
        if parent_name and parent_name in sys.modules:
            setattr(sys.modules[parent_name], child_name, mod)
        return mod

    def exec_module(self, module):
        pass


class SrcAliasFinder(importlib.abc.MetaPathFinder):
    """Ensures `src.<pkg>` and `<pkg>` resolve to the exact same module instance."""

    def __init__(self, src_dir: str):
        self.src_dir = src_dir
        if os.path.isdir(src_dir):
            self.top_level = {
                os.path.splitext(name)[0]
                for name in os.listdir(src_dir)
                if not name.startswith("_") and (os.path.isdir(os.path.join(src_dir, name)) or name.endswith(".py"))
            }
        else:
            self.top_level = set()

    def find_spec(self, fullname: str, path=None, target=None):
        if fullname.startswith("src."):
            bare = fullname[4:]
            top = bare.split(".")[0]
            if top in self.top_level:
                is_pkg = os.path.isdir(os.path.join(self.src_dir, *bare.split(".")))
                return importlib.machinery.ModuleSpec(
                    fullname,
                    _AliasLoader(bare, fullname),
                    is_package=is_pkg,
                )
        return None


def install_src_alias_finder(src_dir: str) -> None:
    """Installs `SrcAliasFinder` on `sys.meta_path` if not already registered."""
    if not any(isinstance(f, SrcAliasFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, SrcAliasFinder(src_dir))


def register_torch_safe_globals() -> None:
    """Allowlists CARINA memory and buffer classes for safe deserialization in PyTorch 2.6+."""
    try:
        import torch

        if not hasattr(torch, "serialization") or not hasattr(torch.serialization, "add_safe_globals"):
            return

        safe_classes = []
        try:
            from memory.replay_memory import ReplayMemory
            from memory.on_policy_buffer import OnPolicyBuffer

            safe_classes.extend([ReplayMemory, OnPolicyBuffer])
        except ImportError:
            pass

        try:
            from src.memory.replay_memory import ReplayMemory as SrcReplayMemory
            from src.memory.on_policy_buffer import OnPolicyBuffer as SrcOnPolicyBuffer

            safe_classes.extend([SrcReplayMemory, SrcOnPolicyBuffer])
        except ImportError:
            pass

        if safe_classes:
            torch.serialization.add_safe_globals(safe_classes)
    except Exception:
        pass


def setup_environment():
    """
    Configures sys.path directories and required environment variables for CARINA.
    Returns a tuple of (project_root, bundle_root, IS_FROZEN).
    """
    IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

    if IS_FROZEN:
        project_root = os.path.dirname(sys.executable)
        bundle_root = sys._MEIPASS
    else:
        # When executed from src/launcher/env_setup.py, project_root is 2 levels up
        launcher_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(launcher_dir, "..", ".."))
        bundle_root = project_root

    # Add critical paths to sys.path (src, proto, bundle_root, ui)
    # Order matters: 'src' and 'proto' MUST precede 'ui' so that backend modules
    # (e.g. src/handlers) are not shadowed by ui submodules (e.g. ui/handlers).
    paths_to_add = [
        os.path.join(bundle_root, "src"),
        os.path.join(bundle_root, "proto"),
        bundle_root,
        os.path.join(bundle_root, "ui"),
    ]
    if "SUMO_HOME" in os.environ:
        sumo_tools = os.path.join(os.environ["SUMO_HOME"], "tools")
        paths_to_add.append(sumo_tools)

    for p in reversed(paths_to_add):
        if p not in sys.path:
            sys.path.insert(0, p)

    install_src_alias_finder(os.path.join(bundle_root, "src"))
    register_torch_safe_globals()

    # Propagate paths to PYTHONPATH for spawned child processes
    existing_py_path = os.environ.get("PYTHONPATH", "")
    existing_parts = [p for p in existing_py_path.split(os.pathsep) if p]
    for p in paths_to_add:
        if p not in existing_parts:
            existing_parts.append(p)
    os.environ["PYTHONPATH"] = os.pathsep.join(existing_parts)

    # Environment settings & thread limiting
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

    # Hardware acceleration & GPU rendering configuration
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "0")
    os.environ.setdefault("__GL_SYNC_TO_VBLANK", "1")

    if sys.platform == "win32":
        try:
            os.system("chcp 65001 > nul")
        except OSError:
            pass

    return project_root, bundle_root, IS_FROZEN
