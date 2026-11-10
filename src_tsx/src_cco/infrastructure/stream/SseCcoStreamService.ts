// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { ICcoStreamService, StreamCallbacks } from '../../domain/contracts/ICcoStreamService';
import { ProcessTelemetryUseCase } from '../../application/usecases/ProcessTelemetryUseCase';
import { EmergencyVehicle, EmergencyCorporation, PreemptionLifecycleState } from '../../domain/models/EmergencyVehicle';
import { GeoProjectionService } from '../../domain/services/GeoProjectionService';

export class SseCcoStreamService implements ICcoStreamService {
  private eventSource: EventSource | null = null;
  private isExplicitlyDisconnected = false;
  private reconnectTimeout: any = null;
  private reconnectDelayMs = 2000;
  private readonly maxReconnectDelayMs = 15000;
  private readonly telemetryProcessor = new ProcessTelemetryUseCase();

  constructor(private readonly endpoint: string = '/cco/stream') {}

  public connect(callbacks: StreamCallbacks): void {
    this.isExplicitlyDisconnected = false;
    this.initEventSource(callbacks);
  }

  private initEventSource(callbacks: StreamCallbacks): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    callbacks.onConnectionChange('CONNECTING');

    try {
      this.eventSource = new EventSource(this.endpoint);

      this.eventSource.onopen = () => {
        this.reconnectDelayMs = 2000;
        callbacks.onConnectionChange('CONNECTED');
      };

      this.eventSource.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          this.handleIncomingPacket(raw, callbacks);
        } catch (err) {
          // Non-JSON or comment heartbeat
        }
      };

      this.eventSource.onerror = () => {
        if (this.isExplicitlyDisconnected) return;

        callbacks.onConnectionChange('RECONNECTING');
        callbacks.onError(new Error('Conexão SSE interrompida. Tentando reconectar...'));

        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }

        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = setTimeout(() => {
          if (!this.isExplicitlyDisconnected) {
            this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 1.5, this.maxReconnectDelayMs);
            this.initEventSource(callbacks);
          }
        }, this.reconnectDelayMs);
      };
    } catch (e: any) {
      callbacks.onConnectionChange('DISCONNECTED');
      callbacks.onError(e);
    }
  }

  private handleIncomingPacket(packet: any, callbacks: StreamCallbacks): void {
    if (!packet || typeof packet !== 'object') return;

    const packetType = packet.type;

    if (
      packetType === 'congestion_update' ||
      packetType === 'initial_map_geometry' ||
      packetType === 'update_heatmap' ||
      packetType === 'update_dashboard_data' ||
      packetType === 'fast_update' ||
      packetType === 'hft_rich_update' ||
      packet.panel_data ||
      packet.payload ||
      packet.street_data ||
      packet.congestion_update ||
      packet.edges
    ) {
      const processed = this.telemetryProcessor.processCongestionPacket(packet);
      callbacks.onCongestionUpdate(processed);
    } else if (packetType === 'evp_telemetry') {
      const v = packet.vehicle || packet;
      if (v && v.vehicle_id) {
        // Normalize corporation to SAMU, BOMBEIROS, or POLICIA
        const rawCorp = String(v.corporation || 'SAMU').toUpperCase();
        let corp: EmergencyCorporation = 'SAMU';
        if (rawCorp.includes('BOMB')) {
          corp = 'BOMBEIROS';
        } else if (rawCorp.includes('POLIC')) {
          corp = 'POLICIA';
        } else {
          corp = 'SAMU';
        }

        // Extract geographic coordinates and metrics
        const rawLat = typeof v.latitude === 'number' ? v.latitude : (typeof v.lat === 'number' ? v.lat : undefined);
        const rawLon = typeof v.longitude === 'number' ? v.longitude : (typeof v.lon === 'number' ? v.lon : undefined);

        let finalX = 0;
        let finalY = 0;

        if (rawLat !== undefined && rawLon !== undefined && GeoProjectionService.isWgs84(rawLat, rawLon)) {
          const [projX, projY] = GeoProjectionService.geoToSumo(rawLat, rawLon);
          finalX = projX;
          finalY = projY;
        } else if (typeof v.x === 'number' && typeof v.y === 'number') {
          finalX = v.x;
          finalY = v.y;
        } else if (rawLon !== undefined && rawLat !== undefined) {
          finalX = rawLon;
          finalY = rawLat;
        }

        const isEvpTriggered = Boolean(v.is_evp_triggered);
        const sirenActive = Boolean(v.siren_active);
        let state: PreemptionLifecycleState = 'IDLE';
        if (v.state) {
          state = (v.state as string).toUpperCase() as PreemptionLifecycleState;
        } else if (isEvpTriggered) {
          state = 'PREEMPTING';
        } else if (sirenActive) {
          state = 'APPROACHING';
        }

        let sourceTimestamp = Date.now();
        if (typeof v.last_update_time === 'number' && v.last_update_time > 0) {
          sourceTimestamp = Math.round(v.last_update_time * 1000);
        } else if (typeof v.timestamp === 'number' && v.timestamp > 0) {
          sourceTimestamp = v.timestamp;
        }

        const domainVehicle: EmergencyVehicle = {
          vehicleId: v.vehicle_id,
          corporation: corp,
          x: finalX,
          y: finalY,
          latitude: rawLat,
          longitude: rawLon,
          speedKmh: typeof v.speed_kmh === 'number' ? v.speed_kmh : 0,
          headingDeg: typeof v.heading_deg === 'number' ? v.heading_deg : 0,
          sirenActive: Boolean(v.siren_active),
          state,
          targetIntersection: v.target_intersection || v.active_intersection_id,
          distanceToIntersectionMeters: v.distance_to_intersection,
          lastSeenTimestamp: Date.now(),
          sourceTimestamp,
          isEvpTriggered,
        };
        callbacks.onEmergencyVehicleUpdate(domainVehicle);
      }
    }
  }

  public disconnect(): void {
    this.isExplicitlyDisconnected = true;
    clearTimeout(this.reconnectTimeout);
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  public isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}
