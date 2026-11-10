// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { TrafficEdge } from '../models/Topology';
import { CongestionLevel } from '../models/CongestionLevel';
import { OrthographicProjection } from './MapProjectionService';

export interface BaseStreetGeometry {
  id: string;
  topoKey: string;
  siblings: string[];
  pathD: string;
  name?: string;
}

export interface RenderedStreet {
  id: string;
  pathD: string;
  color: string;
  congestion: number;
  name?: string;
}

export class StreetTopologyGrouperService {
  /**
   * Resolves the congestion level of a street by checking identifier variations
   * (opposite directions with hyphen, hashed identifiers, and lane suffixes).
   */
  public static getCongestionForId(id: string, congestionMap: Record<string, number>): number {
    if (congestionMap[id] !== undefined) return congestionMap[id];
    const noDash = id.startsWith('-') ? id.slice(1) : id;
    if (congestionMap[noDash] !== undefined) return congestionMap[noDash];
    if (congestionMap[`-${noDash}`] !== undefined) return congestionMap[`-${noDash}`];
    const noHash = noDash.split('#')[0];
    if (congestionMap[noHash] !== undefined) return congestionMap[noHash];
    if (congestionMap[`-${noHash}`] !== undefined) return congestionMap[`-${noHash}`];
    const noLane = noDash.split('_')[0];
    if (congestionMap[noLane] !== undefined) return congestionMap[noLane];
    if (congestionMap[`-${noLane}`] !== undefined) return congestionMap[`-${noLane}`];
    return 0;
  }

  /**
   * Pre-computes base street geometries (pathD, topological grouping, sibling mappings)
   * once on topology/projection change, completely eliminating GC string allocations on updates.
   */
  public static computeBaseStreetGeometries(
    edges: TrafficEdge[],
    projection: OrthographicProjection
  ): BaseStreetGeometry[] {
    const { tx, ty } = projection;
    const processedTopology = new Set<string>();
    const baseList: BaseStreetGeometry[] = [];

    // Maps road groups sharing the same intersections (two-way roads)
    const edgeGroupMap = new Map<string, string[]>();
    for (const edge of edges) {
      if (edge.from && edge.to) {
        const key = [edge.from, edge.to].sort().join('__');
        const list = edgeGroupMap.get(key) || [];
        list.push(edge.id);
        edgeGroupMap.set(key, list);
      }
    }

    for (const edge of edges) {
      if (!edge.shape || edge.shape.length < 2) continue;

      const fromN = edge.from;
      const toN = edge.to;

      const topoKey = fromN && toN ? [fromN, toN].sort().join('__') : edge.id;
      if (processedTopology.has(topoKey)) continue;
      processedTopology.add(topoKey);

      const siblings = edgeGroupMap.get(topoKey) || [edge.id];
      const pathD = edge.shape
        .map((pt: [number, number], i: number) => `${i === 0 ? 'M' : 'L'} ${tx(pt[0]).toFixed(2)} ${ty(pt[1]).toFixed(2)}`)
        .join(' ');

      baseList.push({
        id: edge.id,
        topoKey,
        siblings,
        pathD,
        name: edge.name,
      });
    }

    return baseList;
  }

  /**
   * Applies congestion values and heatmap colors to pre-computed base geometries.
   * Runs in O(N) where N is the number of roads, reusing pre-allocated pathD strings.
   */
  public static applyCongestionToStreets(
    baseGeometries: BaseStreetGeometry[],
    congestionMap: Record<string, number>
  ): RenderedStreet[] {
    return baseGeometries.map((base) => {
      let maxVal = 0;
      for (const sid of base.siblings) {
        const v = this.getCongestionForId(sid, congestionMap);
        if (v > maxVal) maxVal = v;
      }

      const level = new CongestionLevel(maxVal);
      return {
        id: base.id,
        pathD: base.pathD,
        color: level.getColor(),
        congestion: maxVal,
        name: base.name,
      };
    });
  }

  /**
   * Backward-compatible convenience wrapper combining computation and congestion mapping.
   */
  public static groupAndRenderStreets(
    edges: TrafficEdge[],
    projection: OrthographicProjection,
    congestionMap: Record<string, number>
  ): RenderedStreet[] {
    const base = this.computeBaseStreetGeometries(edges, projection);
    return this.applyCongestionToStreets(base, congestionMap);
  }
}

