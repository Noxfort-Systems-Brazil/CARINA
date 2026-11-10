// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { ITopologyRepository } from '../../domain/contracts/ITopologyRepository';
import { MapTopology } from '../../domain/models/Topology';

export class HttpTopologyRepository implements ITopologyRepository {
  constructor(private readonly endpoint: string = '/cco/topology') {}

  public async fetchTopology(): Promise<MapTopology> {
    const response = await fetch(this.endpoint);
    if (!response.ok) {
      throw new Error(`Falha ao carregar topologia: HTTP ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    return data as MapTopology;
  }
}
