// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { MapTopology } from '../models/Topology';

export interface OrthographicProjection {
  viewBox: string;
  minX: number;
  minY: number;
  width: number;
  height: number;
  tx: (x: number) => number;
  ty: (y: number) => number;
  centerX: number;
  centerY: number;
}

export class MapProjectionService {
  /**
   * Computes an isotropic (1:1) 2D bounding box with a 10% safety margin (minimum 35m)
   * and inverts the Y-axis to convert SUMO Cartesian reference (+Y North) to SVG (+Y down).
   */
  public static computeProjection(topology: MapTopology | null): OrthographicProjection | null {
    if (!topology) return null;

    let minX = topology.bounds?.min_x ?? 0;
    let maxX = topology.bounds?.max_x ?? 715.96;
    let minY = topology.bounds?.min_y ?? 0;
    let maxY = topology.bounds?.max_y ?? 930.36;

    if (topology.nodes && topology.nodes.length > 0) {
      for (const node of topology.nodes) {
        if (node.x < minX) minX = node.x;
        if (node.x > maxX) maxX = node.x;
        if (node.y < minY) minY = node.y;
        if (node.y > maxY) maxY = node.y;
      }
    }

    if (topology.edges && topology.edges.length > 0) {
      for (const edge of topology.edges) {
        if (edge.shape) {
          for (const pt of edge.shape) {
            if (pt[0] < minX) minX = pt[0];
            if (pt[0] > maxX) maxX = pt[0];
            if (pt[1] < minY) minY = pt[1];
            if (pt[1] > maxY) maxY = pt[1];
          }
        }
      }
    }

    const mapW = maxX - minX || 1;
    const mapH = maxY - minY || 1;

    const padX = Math.max(mapW * 0.10, 35);
    const padY = Math.max(mapH * 0.10, 35);

    const viewBoxMinX = minX - padX;
    const viewBoxMaxX = maxX + padX;
    const viewBoxMinY = minY - padY;
    const viewBoxMaxY = maxY + padY;

    const width = viewBoxMaxX - viewBoxMinX;
    const height = viewBoxMaxY - viewBoxMinY;

    const tx = (x: number) => x;
    const ty = (y: number) => (viewBoxMaxY + viewBoxMinY) - y;

    return {
      viewBox: `${viewBoxMinX} ${viewBoxMinY} ${width} ${height}`,
      minX: viewBoxMinX,
      minY: viewBoxMinY,
      width,
      height,
      tx,
      ty,
      centerX: (viewBoxMinX + viewBoxMaxX) / 2,
      centerY: (viewBoxMinY + viewBoxMaxY) / 2,
    };
  }
}
