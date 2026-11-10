// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { TrafficLightPanelMap } from '../models/TrafficLight';
import { EmergencyVehicle } from '../models/EmergencyVehicle';

export type StreamConnectionStatus = 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';

export interface CongestionStreamPayload {
  congestionMap: Record<string, number>;
  panelData?: TrafficLightPanelMap;
}

export interface StreamCallbacks {
  onConnectionChange: (status: StreamConnectionStatus) => void;
  onCongestionUpdate: (update: CongestionStreamPayload) => void;
  onEmergencyVehicleUpdate: (vehicle: EmergencyVehicle) => void;
  onError: (error: Error) => void;
}

export interface ICcoStreamService {
  connect(callbacks: StreamCallbacks): void;
  disconnect(): void;
  isConnected(): boolean;
}
