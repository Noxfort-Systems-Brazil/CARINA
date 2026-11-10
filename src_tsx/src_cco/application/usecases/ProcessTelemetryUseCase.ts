// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { TrafficLightPanelMap, SignalDisplayState } from '../../domain/models/TrafficLight';
import { CongestionStreamPayload } from '../../domain/contracts/ICcoStreamService';

export class ProcessTelemetryUseCase {
  public processCongestionPacket(rawPayload: Record<string, any>): CongestionStreamPayload {
    const congestionMap: Record<string, number> = {};

    const candidateSources = [
      rawPayload.payload,
      rawPayload.congestion_update,
      rawPayload.street_data,
      rawPayload.edges,
      rawPayload,
    ];

    for (const source of candidateSources) {
      if (source && typeof source === 'object') {
        for (const [streetId, value] of Object.entries<any>(source)) {
          if (streetId === 'type' || streetId === 'panel_data' || streetId === 'maturity_phases') continue;

          let numVal: number | null = null;
          if (typeof value === 'number') {
            numVal = value;
          } else if (value && typeof value === 'object' && typeof value.congestion === 'number') {
            numVal = value.congestion;
          }

          if (numVal !== null) {
            const noDash = streetId.startsWith('-') ? streetId.slice(1) : streetId;
            const noHash = noDash.split('#')[0];
            const noLane = noDash.split('_')[0];

            congestionMap[streetId] = numVal;
            congestionMap[noDash] = numVal;
            congestionMap[`-${noDash}`] = numVal;
            congestionMap[noHash] = numVal;
            congestionMap[`-${noHash}`] = numVal;
            congestionMap[noLane] = numVal;
            congestionMap[`-${noLane}`] = numVal;
          }
        }
      }
    }

    let panelData: TrafficLightPanelMap | undefined;
    if (rawPayload.panel_data && typeof rawPayload.panel_data === 'object') {
      panelData = {};
      const now = Date.now();
      for (const [tlsId, item] of Object.entries<any>(rawPayload.panel_data)) {
        const display = (item?.display_state || 'RED').toUpperCase() as SignalDisplayState;
        panelData[tlsId] = {
          intersectionId: tlsId,
          phase: typeof item?.phase === 'number' ? item.phase : 1,
          displayState: display,
          brand: item?.brand,
          model: item?.model,
          lastUpdated: now,
        };
      }
    }

    return { congestionMap, panelData };
  }
}
