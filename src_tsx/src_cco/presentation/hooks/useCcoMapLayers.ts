// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { useMemo } from 'react';
import { MapTopology } from '../../domain/models/Topology';
import { TrafficLightPanelMap } from '../../domain/models/TrafficLight';
import { MapProjectionService, OrthographicProjection } from '../../domain/services/MapProjectionService';
import { StreetTopologyGrouperService, RenderedStreet } from '../../domain/services/StreetTopologyGrouperService';

export interface RenderedIntersection {
  id: string;
  cx: number;
  cy: number;
}

export interface RenderedTrafficLight {
  id: string;
  cx: number;
  cy: number;
  displayState: string;
  phase: number;
}

export function useCcoMapLayers(
  topology: MapTopology | null,
  congestionMap: Record<string, number>,
  signals: TrafficLightPanelMap
) {
  const projection: OrthographicProjection | null = useMemo(() => {
    return MapProjectionService.computeProjection(topology);
  }, [topology]);

  // 1. Base geometries cached on topology & projection changes (computed once!)
  const baseGeometries = useMemo(() => {
    if (!topology || !projection) return [];
    return StreetTopologyGrouperService.computeBaseStreetGeometries(topology.edges, projection);
  }, [topology, projection]);

  // 2. Only congestion colors and values mapped on updates (zero string allocation)
  const renderedStreets: RenderedStreet[] = useMemo(() => {
    if (baseGeometries.length === 0) return [];
    return StreetTopologyGrouperService.applyCongestionToStreets(baseGeometries, congestionMap);
  }, [baseGeometries, congestionMap]);


  const { intersectionNodes, trafficLightNodes } = useMemo(() => {
    if (!topology || !projection) {
      return { intersectionNodes: [], trafficLightNodes: [] };
    }

    const { tx, ty } = projection;
    const intersections: RenderedIntersection[] = [];
    const trafficLights: RenderedTrafficLight[] = [];

    const nodeDegree = new Map<string, number>();
    for (const edge of topology.edges) {
      if (edge.from) nodeDegree.set(edge.from, (nodeDegree.get(edge.from) || 0) + 1);
      if (edge.to) nodeDegree.set(edge.to, (nodeDegree.get(edge.to) || 0) + 1);
    }

    for (const node of topology.nodes) {
      const cx = tx(node.x);
      const cy = ty(node.y);
      const isSemaphore = node.type === 'traffic_light' || !!signals[node.id];

      if (isSemaphore) {
        const sig = signals[node.id];
        trafficLights.push({
          id: node.id,
          cx,
          cy,
          displayState: sig?.displayState || 'RED',
          phase: sig?.phase ?? 1,
        });
      } else {
        const degree = nodeDegree.get(node.id) || 0;
        if (degree >= 2) {
          intersections.push({ id: node.id, cx, cy });
        }
      }
    }

    return { intersectionNodes: intersections, trafficLightNodes: trafficLights };
  }, [topology, projection, signals]);

  return {
    projection,
    renderedStreets,
    intersectionNodes,
    trafficLightNodes,
  };
}
