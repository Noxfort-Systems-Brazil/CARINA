// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

export interface GeoBounds {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export interface MetricBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

// Default geographic and metric boundaries of CARINA network
export const DEFAULT_GEO_BOUNDS: GeoBounds = {
  minLon: -51.240163,
  minLat: -23.515986,
  maxLon: -51.233151,
  maxLat: -23.507576,
};

export const DEFAULT_METRIC_BOUNDS: MetricBounds = {
  minX: 0.0,
  minY: 0.0,
  maxX: 715.96,
  maxY: 930.36,
};

export class GeoProjectionService {
  /**
   * Checks if coordinate values are within WGS84 lat/lon ranges.
   */
  public static isWgs84(lat: number, lon: number): boolean {
    return Math.abs(lat) <= 90.0 && Math.abs(lon) <= 180.0;
  }

  /**
   * Converts WGS84 (latitude, longitude) to SUMO local metric (x, y).
   * Inverse of EVP_SIMULATOR parser.go and EVPTopologyService lat_lon_to_sumo.
   */
  public static geoToSumo(
    lat: number,
    lon: number,
    metricBounds: MetricBounds = DEFAULT_METRIC_BOUNDS,
    geoBounds: GeoBounds = DEFAULT_GEO_BOUNDS
  ): [number, number] {
    // If already in metric space, return as is
    if (!this.isWgs84(lat, lon)) {
      return [lon, lat];
    }

    const dLon = geoBounds.maxLon - geoBounds.minLon;
    const dLat = geoBounds.maxLat - geoBounds.minLat;

    if (Math.abs(dLon) < 1e-9 || Math.abs(dLat) < 1e-9) {
      return [metricBounds.minX, metricBounds.minY];
    }

    const ratioX = (lon - geoBounds.minLon) / dLon;
    const ratioY = (lat - geoBounds.minLat) / dLat;

    const x = metricBounds.minX + ratioX * (metricBounds.maxX - metricBounds.minX);
    const y = metricBounds.minY + ratioY * (metricBounds.maxY - metricBounds.minY);

    return [x, y];
  }

  /**
   * Converts SUMO local metric (x, y) to WGS84 (latitude, longitude).
   */
  public static sumoToGeo(
    x: number,
    y: number,
    metricBounds: MetricBounds = DEFAULT_METRIC_BOUNDS,
    geoBounds: GeoBounds = DEFAULT_GEO_BOUNDS
  ): [number, number] {
    const dX = metricBounds.maxX - metricBounds.minX;
    const dY = metricBounds.maxY - metricBounds.minY;

    if (Math.abs(dX) < 1e-9 || Math.abs(dY) < 1e-9) {
      return [geoBounds.minLat, geoBounds.minLon];
    }

    const ratioX = (x - metricBounds.minX) / dX;
    const ratioY = (y - metricBounds.minY) / dY;

    const lon = geoBounds.minLon + ratioX * (geoBounds.maxLon - geoBounds.minLon);
    const lat = geoBounds.minLat + ratioY * (geoBounds.maxLat - geoBounds.minLat);

    return [lat, lon];
  }
}
