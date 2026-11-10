// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

export type EmergencyCorporation = 'SAMU' | 'BOMBEIROS' | 'BOMBEIRO' | 'POLICIA';

export type PreemptionLifecycleState =
  | 'IDLE'
  | 'APPROACHING'
  | 'PREEMPTING'
  | 'CLEARED'
  | 'LOST_TELEMETRY';

export interface EmergencyVehicle {
  vehicleId: string;
  corporation: EmergencyCorporation;
  x: number;
  y: number;
  latitude?: number;
  longitude?: number;
  speedKmh: number;
  headingDeg: number;
  sirenActive: boolean;
  state: PreemptionLifecycleState;
  targetIntersection?: string;
  distanceToIntersectionMeters?: number;
  lastSeenTimestamp: number;
  sourceTimestamp?: number;
  isEvpTriggered?: boolean;
}

