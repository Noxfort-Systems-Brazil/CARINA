// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { EmergencyVehicle, EmergencyCorporation } from '../../domain/models/EmergencyVehicle';

export interface FleetSummary {
  totalActive: number;
  byCorporation: Record<EmergencyCorporation, number>;
  preemptingCount: number;
  activeAlerts: EmergencyVehicle[];
}

export class ManageEmergencyFleetUseCase {
  private readonly staleThresholdMs = 30000; // 30s timeout

  public updateVehicleInFleet(
    currentFleet: Map<string, EmergencyVehicle>,
    incomingVehicle: EmergencyVehicle
  ): Map<string, EmergencyVehicle> {
    const existing = currentFleet.get(incomingVehicle.vehicleId);
    let resolvedVehicle = incomingVehicle;

    if (existing) {
      // 1. Discard out-of-order stale packets
      if (
        incomingVehicle.sourceTimestamp !== undefined &&
        existing.sourceTimestamp !== undefined &&
        incomingVehicle.sourceTimestamp < existing.sourceTimestamp
      ) {
        return currentFleet;
      }

      // 2. Preservation of enriched preemption engine state:
      const isRawWithoutPreemptionData =
        incomingVehicle.isEvpTriggered === undefined ||
        (!incomingVehicle.isEvpTriggered && !incomingVehicle.targetIntersection);

      const existingHasActivePreemption =
        Boolean(existing.isEvpTriggered) || existing.state === 'PREEMPTING' || !!existing.targetIntersection;

      const isRecentPreemption = (Date.now() - existing.lastSeenTimestamp) < 3500;

      if (isRawWithoutPreemptionData && existingHasActivePreemption && isRecentPreemption) {
        resolvedVehicle = {
          ...incomingVehicle,
          isEvpTriggered: existing.isEvpTriggered,
          targetIntersection: existing.targetIntersection,
          distanceToIntersectionMeters: incomingVehicle.distanceToIntersectionMeters ?? existing.distanceToIntersectionMeters,
          state: existing.state,
        };
      }
    }

    const updated = new Map(currentFleet);
    updated.set(resolvedVehicle.vehicleId, resolvedVehicle);
    return this.cleanupStaleVehicles(updated);
  }

  public cleanupStaleVehicles(fleet: Map<string, EmergencyVehicle>): Map<string, EmergencyVehicle> {
    const now = Date.now();
    const clean = new Map<string, EmergencyVehicle>();

    for (const [id, vehicle] of fleet.entries()) {
      if (now - vehicle.lastSeenTimestamp < this.staleThresholdMs) {
        clean.set(id, vehicle);
      }
    }
    return clean;
  }

  public getSummary(fleet: Map<string, EmergencyVehicle>): FleetSummary {
    const byCorporation: Record<EmergencyCorporation, number> = {
      SAMU: 0,
      BOMBEIROS: 0,
      BOMBEIRO: 0,
      POLICIA: 0,
    };

    let preemptingCount = 0;
    const activeAlerts: EmergencyVehicle[] = [];

    for (const vehicle of fleet.values()) {
      const corpKey: EmergencyCorporation = vehicle.corporation === 'BOMBEIRO' ? 'BOMBEIROS' : vehicle.corporation;
      byCorporation[corpKey] = (byCorporation[corpKey] || 0) + 1;
      const isVehicleInAlert = Boolean(vehicle.sirenActive) || Boolean(vehicle.isEvpTriggered) || vehicle.state === 'PREEMPTING';
      if (isVehicleInAlert) {
        if (Boolean(vehicle.isEvpTriggered) || vehicle.state === 'PREEMPTING') {
          preemptingCount++;
        }
        activeAlerts.push(vehicle);
      }
    }

    return {
      totalActive: fleet.size,
      byCorporation,
      preemptingCount,
      activeAlerts,
    };
  }
}
