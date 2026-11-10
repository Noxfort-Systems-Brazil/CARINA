// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

export type SignalDisplayState = 'GREEN' | 'YELLOW' | 'RED' | 'FLASHING_YELLOW' | 'OFF';

export interface TrafficLightState {
  intersectionId: string;
  phase: number;
  displayState: SignalDisplayState;
  brand?: string;
  model?: string;
  lastUpdated: number;
}

export interface TrafficLightPanelMap {
  [intersectionId: string]: TrafficLightState;
}
