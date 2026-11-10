# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys

print(f"[Runtime Hook] Initial sys.path: {sys.path}")

# sys._MEIPASS points to the _internal folder (bundle root)
bundle_dir = getattr(sys, "_MEIPASS", None)

if bundle_dir:
    # Constructs the absolute path to 'src' and 'proto' within the bundle
    src_path = os.path.abspath(os.path.join(bundle_dir, "src"))
    proto_path = os.path.abspath(os.path.join(bundle_dir, "proto"))

    for path_name, path_val in [("src", src_path), ("proto", proto_path)]:
        if os.path.isdir(path_val):
            if path_val not in sys.path:
                sys.path.insert(1, path_val)
                print(f"[Runtime Hook] Added bundle {path_name} path to sys.path: {path_val}")
            else:
                print(f"[Runtime Hook] Bundle {path_name} path already in sys.path: {path_val}")
        else:
            print(f"[Runtime Hook] Bundle {path_name} path NOT found: {path_val}")

    # Ensures the bundle root is also in the path (usually added automatically, but confirm)
    abs_bundle_dir = os.path.abspath(bundle_dir)
    if abs_bundle_dir not in sys.path:
        sys.path.append(abs_bundle_dir)  # Add at the end
        print(f"[Runtime Hook] Added bundle root path to sys.path: {abs_bundle_dir}")

else:
    print("[Runtime Hook] Not running in frozen mode (no _MEIPASS). Hook skipping modification.")

print(f"[Runtime Hook] sys.path after hook: {sys.path}")
