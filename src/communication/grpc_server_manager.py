# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from concurrent import futures

import grpc

from communication.grpc_security import (
    BearerTokenServerInterceptor,
    build_grpc_server_credentials,
    resolve_grpc_security_config,
)


class GrpcServerManager:
    """
    Manages the lifecycle of the gRPC server (start, stop, bind) with optional TLS and token auth.
    """

    def __init__(self, settings, locale_manager, implementation_instance):
        self.settings = settings
        self.locale_manager = locale_manager
        self.implementation_instance = implementation_instance
        self.server = None

    def start(self):
        server_port = self.settings.get("SYNAPSE", "port", fallback="50051")
        max_workers = self.settings.getint("SYNAPSE", "max_workers", fallback=10)
        sec_cfg = resolve_grpc_security_config(self.settings)

        interceptors = [BearerTokenServerInterceptor(sec_cfg.auth_token)] if sec_cfg.auth_token else []
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers), interceptors=interceptors)

        try:
            import synapse_hft_pb2_grpc as pb2_grpc

            from communication.hft_server import CarinaHFTImpl

            pb2_grpc.add_HFTLinkServicer_to_server(
                CarinaHFTImpl(self.implementation_instance, locale_manager=self.locale_manager), self.server
            )
        except ImportError:
            logging.critical(
                self.locale_manager.get_string(
                    "hft_server.import_failed",
                    default="[GrpcServerManager] Failed to import generated gRPC modules. Ensure 'proto' folder exists.",
                )
            )
            return

        bind_address = f"[::]:{server_port}"
        creds = build_grpc_server_credentials(sec_cfg)
        if creds is not None:
            self.server.add_secure_port(bind_address, creds)
            logging.info(f"[gRPC] TLS security enabled on port {server_port} (mTLS={sec_cfg.require_client_cert}).")
        else:
            self.server.add_insecure_port(bind_address)

        logging.info(
            self.locale_manager.get_string(
                "grpc_server.starting", default="[gRPC] Starting gRPC HFT Server on port {port}...", port=server_port
            )
        )
        self.server.start()

    def stop(self):
        if self.server:
            self.server.stop(0)
            logging.info(
                self.locale_manager.get_string("grpc_server.stopped", default="[gRPC] gRPC HFT Server stopped.")
            )
