// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

export interface Coordinates {
  x: number;
  y: number;
}

export interface TrafficNode {
  id: string;
  x: number;
  y: number;
  type: 'traffic_light' | 'priority' | 'zipper' | 'unregulated';
}

export interface TrafficEdge {
  id: string;
  name: string;
  from: string;
  to: string;
  shape: [number, number][];
  lanes: number;
  speed: number;
  length: number;
}

export interface BoundingBox {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface MapTopology {
  bounds: BoundingBox;
  nodes: TrafficNode[];
  edges: TrafficEdge[];
  metadata?: {
    generated_at?: number;
    total_tls?: number;
    total_junctions?: number;
  };
}
