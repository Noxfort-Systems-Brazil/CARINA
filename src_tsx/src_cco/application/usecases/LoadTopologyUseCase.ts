// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { ITopologyRepository } from '../../domain/contracts/ITopologyRepository';
import { MapTopology } from '../../domain/models/Topology';

export class LoadTopologyUseCase {
  constructor(private readonly repository: ITopologyRepository) {}

  public async execute(): Promise<MapTopology> {
    return await this.repository.fetchTopology();
  }
}
