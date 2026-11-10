// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { MapTopology } from '../models/Topology';

export interface ITopologyRepository {
  fetchTopology(): Promise<MapTopology>;
}
