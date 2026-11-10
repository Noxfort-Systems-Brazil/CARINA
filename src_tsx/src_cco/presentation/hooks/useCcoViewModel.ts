// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { useState, useEffect, useMemo, useRef } from 'react';
import { MapTopology } from '../../domain/models/Topology';
import { TrafficLightPanelMap } from '../../domain/models/TrafficLight';
import { EmergencyVehicle } from '../../domain/models/EmergencyVehicle';
import { StreamConnectionStatus } from '../../domain/contracts/ICcoStreamService';
import { HttpTopologyRepository } from '../../infrastructure/api/HttpTopologyRepository';
import { SseCcoStreamService } from '../../infrastructure/stream/SseCcoStreamService';
import { LoadTopologyUseCase } from '../../application/usecases/LoadTopologyUseCase';
import { ManageEmergencyFleetUseCase, FleetSummary } from '../../application/usecases/ManageEmergencyFleetUseCase';

export function useCcoViewModel() {
  const [topology, setTopology] = useState<MapTopology | null>(null);
  const [congestionMap, setCongestionMap] = useState<Record<string, number>>({});
  const [signals, setSignals] = useState<TrafficLightPanelMap>({});
  const [fleet, setFleet] = useState<Map<string, EmergencyVehicle>>(new Map());
  const [connectionStatus, setConnectionStatus] = useState<StreamConnectionStatus>('CONNECTING');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Instantiate use cases and services via Clean Architecture
  const topologyRepo = useMemo(() => new HttpTopologyRepository(), []);
  const loadTopologyUseCase = useMemo(() => new LoadTopologyUseCase(topologyRepo), [topologyRepo]);
  const fleetUseCase = useMemo(() => new ManageEmergencyFleetUseCase(), []);
  const streamServiceRef = useRef<SseCcoStreamService | null>(null);

  // 1. Load road topology on initialization
  useEffect(() => {
    let isMounted = true;
    loadTopologyUseCase
      .execute()
      .then((data) => {
        if (isMounted) setTopology(data);
      })
      .catch((err) => {
        if (isMounted) setErrorMessage(err.message);
      });

    return () => {
      isMounted = false;
    };
  }, [loadTopologyUseCase]);

  // 2. Page Visibility detection to reduce CPU/GPU when minimized or hidden in background
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (typeof document !== 'undefined') {
        document.body.classList.toggle('tab-hidden', document.hidden);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // 3. Connect to real-time SSE stream with frame-batched fleet updates
  useEffect(() => {
    const stream = new SseCcoStreamService('/cco/stream');
    streamServiceRef.current = stream;

    const pendingVehicles: EmergencyVehicle[] = [];
    let rafVehicleId: number | null = null;

    const flushVehicleUpdates = () => {
      if (pendingVehicles.length > 0) {
        const batch = pendingVehicles.splice(0, pendingVehicles.length);
        setFleet((prevFleet) => {
          let current = prevFleet;
          for (const v of batch) {
            current = fleetUseCase.updateVehicleInFleet(current, v);
          }
          return current;
        });
      }
      rafVehicleId = null;
    };

    stream.connect({
      onConnectionChange: (status) => {
        setConnectionStatus(status);
        if (status === 'CONNECTED') setErrorMessage(null);
      },
      onCongestionUpdate: (update) => {
        setCongestionMap((prev) => ({ ...prev, ...update.congestionMap }));
        if (update.panelData) {
          setSignals((prev) => ({ ...prev, ...update.panelData }));
        }
      },
      onEmergencyVehicleUpdate: (vehicle) => {
        pendingVehicles.push(vehicle);
        if (!rafVehicleId) {
          rafVehicleId = requestAnimationFrame(flushVehicleUpdates);
        }
      },
      onError: (err) => {
        setErrorMessage(err.message);
      },
    });

    // Timer to clean up stale/disconnected emergency vehicles every 5s
    const cleanupInterval = setInterval(() => {
      setFleet((prevFleet) => fleetUseCase.cleanupStaleVehicles(prevFleet));
    }, 5000);

    return () => {
      if (rafVehicleId) cancelAnimationFrame(rafVehicleId);
      clearInterval(cleanupInterval);
      stream.disconnect();
    };
  }, [fleetUseCase]);


  const emergencyVehicles = useMemo(() => Array.from(fleet.values()), [fleet]);
  const fleetSummary: FleetSummary = useMemo(() => fleetUseCase.getSummary(fleet), [fleet, fleetUseCase]);

  return {
    topology,
    congestionMap,
    signals,
    emergencyVehicles,
    fleetSummary,
    connectionStatus,
    errorMessage,
  };
}
