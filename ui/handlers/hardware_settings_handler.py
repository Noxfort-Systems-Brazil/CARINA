# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import flet as ft

from src.controller.connection_manager import HardwareConnectionManager
from src.repositories.connection_csv_store import ConnectionCSVStore
from src.repositories.hardware_connection_repo import HardwareConnectionRepository


class HardwareSettingsHandler:
    """
    SRP: Manages all business logic related to Hardware configuration,
    including CSV spreadsheet import/export and connection toggles.
    """

    def __init__(
        self,
        connection_manager: HardwareConnectionManager,
        settings_client=None,
        locale_manager=None,
        connection_repo=None,
        csv_store=None,
    ):
        self.connection_manager = connection_manager
        self.settings_client = settings_client
        self.locale_manager = locale_manager
        self._connection_repo = connection_repo or HardwareConnectionRepository(locale_manager=locale_manager)
        self._csv_store = csv_store or ConnectionCSVStore()
        self.page = None
        self.hardware_card = None

        self.import_picker = ft.FilePicker(on_result=self._on_import_result)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)

        self._initial_saved_ips = dict(self.connection_manager.saved_ips)
        self._initial_active_connections = set(
            tl_id
            for tl_id, drv in self.connection_manager.active_connections.items()
            if getattr(drv, "is_connected", False)
        )

    def mount(self, page: ft.Page, hardware_card):
        self.page = page
        self.hardware_card = hardware_card
        if self.hardware_card:
            self.hardware_card.handler = self
        self.page.overlay.extend([self.import_picker, self.export_picker])
        self._initial_saved_ips = {
            k: v.strip() for k, v in self.connection_manager.saved_ips.items() if v and v.strip()
        }
        self._initial_active_connections = set(
            tl_id
            for tl_id, drv in self.connection_manager.active_connections.items()
            if getattr(drv, "is_connected", False)
        )
        self.refresh_ui()

    def refresh_ui(self):
        """Updates the visual component (Hardware Card) using data from the Connection Manager."""
        if self.hardware_card:
            ui_data = self.connection_manager.get_ui_status_list()
            self.hardware_card.load_agents_data(ui_data)

    def on_import_click(self, e):
        dialog_title = "Select Configuration CSV"
        if self.locale_manager:
            dialog_title = self.locale_manager.get_string(
                "settings_view.hardware_card.select_dialog_title", default=dialog_title
            )
        self.import_picker.pick_files(dialog_title=dialog_title, allowed_extensions=["csv"])

    def _on_import_result(self, e):
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            from src.drivers.go_gateway_client import GoGatewayClient

            if GoGatewayClient.is_remote_gateway_role() and self.settings_client:
                entries = self._csv_store.import_csv_entries(filepath)
                total = len(entries)
                success_count = total
                for tl_id, entry in entries.items():
                    if not isinstance(entry, dict):
                        continue
                    ip = str(entry.get("ip", "")).strip()
                    if ip:
                        self.connection_manager.saved_ips[tl_id] = ip
                    if entry.get("snmp_config") and hasattr(self.connection_manager, "saved_snmp_configs"):
                        self.connection_manager.saved_snmp_configs[tl_id] = dict(entry["snmp_config"])
                self.settings_client.send_command(
                    "sync_hardware_csv",
                    {"entries": entries, "save_to_db": False},
                )
            else:
                success_count, total = self.connection_manager.import_csv_config(filepath, save_to_db=False)
            self.refresh_ui()

            if self.page:
                default_msg = f"Import complete: {success_count} out of {total} traffic lights connected successfully."
                msg = default_msg
                if self.locale_manager:
                    msg = self.locale_manager.get_string(
                        "settings_view.hardware_card.import_success",
                        default=default_msg,
                        success=success_count,
                        total=total,
                    )
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def on_export_click(self, e):
        dialog_title = "Save Template CSV"
        if self.locale_manager:
            dialog_title = self.locale_manager.get_string(
                "settings_view.hardware_card.save_dialog_title", default=dialog_title
            )
        self.export_picker.save_file(
            dialog_title=dialog_title, file_name="carina_hardware_template.csv", allowed_extensions=["csv"]
        )

    def _on_export_result(self, e):
        if e.path:
            save_path = e.path if e.path.lower().endswith(".csv") else f"{e.path}.csv"
            success = self.connection_manager.export_csv_template(save_path)
            if self.page:
                if success:
                    msg = (
                        self.locale_manager.get_string(
                            "settings_view.hardware_card.export_success", default="Template exported successfully!"
                        )
                        if self.locale_manager
                        else "Template exported successfully!"
                    )
                else:
                    msg = (
                        self.locale_manager.get_string(
                            "settings_view.hardware_card.export_error", default="Error exporting template."
                        )
                        if self.locale_manager
                        else "Error exporting template."
                    )
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def on_toggle_connection(self, intersection_id: str, ip_address: str, action: str = "toggle"):
        from src.drivers.go_gateway_client import GoGatewayClient

        saved_snmp = getattr(self.connection_manager, "saved_snmp_configs", {})
        snmp_cfg = saved_snmp.get(str(intersection_id)) if isinstance(saved_snmp, dict) else None

        if GoGatewayClient.is_remote_gateway_role() and self.settings_client:
            if ip_address:
                self.connection_manager.saved_ips[str(intersection_id)] = str(ip_address).strip()
            was_connected = self.connection_manager.is_intersection_connected(intersection_id)
            target_connect = action == "connect" or (action == "toggle" and not was_connected)
            is_conn = target_connect
            if hasattr(self.connection_manager, "update_remote_hardware_status"):
                self.connection_manager.update_remote_hardware_status(
                    {
                        str(intersection_id): {
                            "is_connected": target_connect,
                            "ip_address": self.connection_manager.saved_ips.get(str(intersection_id), ip_address),
                            "protocol": "RemoteGatewayIPC" if target_connect else "none",
                        }
                    }
                )
            cmd_payload = {"intersection_id": intersection_id, "ip_address": ip_address, "action": action}
            if snmp_cfg:
                cmd_payload["snmp_config"] = snmp_cfg
            self.settings_client.send_command("set_hardware_connection", cmd_payload)
        else:
            is_conn = self.connection_manager.toggle_connection(
                intersection_id, ip_address, action=action, save_to_db=True
            )
            if self.settings_client:
                cmd_payload = {"intersection_id": intersection_id, "ip_address": ip_address, "action": action}
                if snmp_cfg:
                    cmd_payload["snmp_config"] = snmp_cfg
                self.settings_client.send_command("set_hardware_connection", cmd_payload)

        alt_id = (
            str(intersection_id).replace("tl_", "")
            if str(intersection_id).startswith("tl_")
            else f"tl_{intersection_id}"
        )

        if action == "disconnect" or not is_conn:
            self._initial_active_connections.discard(str(intersection_id))
            self._initial_active_connections.discard(alt_id)
        else:
            self._initial_active_connections.add(str(intersection_id))
            resolved_ip = self.connection_manager.saved_ips.get(str(intersection_id), ip_address)
            if resolved_ip:
                self._initial_saved_ips[str(intersection_id)] = resolved_ip.strip()

        self.refresh_ui()

    def has_unsaved_changes(self) -> bool:
        current_ips = {k: v.strip() for k, v in self.connection_manager.saved_ips.items() if v and v.strip()}
        if self.hardware_card and hasattr(self.hardware_card, "ip_fields"):
            for tl_id, field in self.hardware_card.ip_fields.items():
                val = (field.value or "").strip() if field else ""
                if val:
                    current_ips[tl_id] = val
                elif tl_id in current_ips:
                    del current_ips[tl_id]

        if current_ips != self._initial_saved_ips:
            return True

        return False

    def save_changes(self) -> None:
        current_ips = dict(self.connection_manager.saved_ips)
        if self.hardware_card and hasattr(self.hardware_card, "ip_fields"):
            for tl_id, field in self.hardware_card.ip_fields.items():
                if field and field.value:
                    current_ips[tl_id] = field.value.strip()

        current_active = set(
            tl_id
            for tl_id, drv in self.connection_manager.active_connections.items()
            if getattr(drv, "is_connected", False)
        )
        remote_map = getattr(self.connection_manager, "remote_hardware_status", {})
        if isinstance(remote_map, dict):
            for tl_id, info in remote_map.items():
                if isinstance(info, dict) and info.get("is_connected"):
                    current_active.add(tl_id)

        # 1. Clean up from DB any intersections that are NOT currently active
        all_known = (
            set(self._initial_saved_ips.keys())
            | set(current_ips.keys())
            | set(self.connection_manager.saved_ips.keys())
        )
        for tl_id in all_known:
            if tl_id not in current_active:
                self._connection_repo.remove_connection_db(tl_id, self.locale_manager)

        # 2. Persist active connections to DB
        saved_snmp = getattr(self.connection_manager, "saved_snmp_configs", {})
        for tl_id in current_active:
            ip = current_ips.get(tl_id, self.connection_manager.saved_ips.get(tl_id, ""))
            snmp_cfg = saved_snmp.get(tl_id) if isinstance(saved_snmp, dict) else None
            if ip:
                self._connection_repo.save_connection_db(tl_id, ip, self.locale_manager, snmp_config=snmp_cfg)
                if self.settings_client:
                    cmd_payload = {"intersection_id": tl_id, "ip_address": ip, "action": "connect"}
                    if snmp_cfg:
                        cmd_payload["snmp_config"] = snmp_cfg
                    self.settings_client.send_command("set_hardware_connection", cmd_payload)

        # Update initial snapshot
        self._initial_saved_ips = dict(current_ips)
        self._initial_active_connections = set(current_active)

    def discard_changes(self) -> None:
        """
        Discards uncommitted IP text field modifications back to the last saved IPs.
        Does NOT automatically reconnect traffic lights that the user explicitly chose to disconnect.
        """
        # Restore saved IPs dictionary
        self.connection_manager.saved_ips.clear()
        self.connection_manager.saved_ips.update(self._initial_saved_ips)

        self.refresh_ui()
