// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import fletPalette from '../../presentation/styles/flet_color_palette.json';

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ];
}

const HEATMAP_STOPS: Array<[number, [number, number, number]]> = [
  [0.00, hexToRgb(fletPalette.heatmap.freeFlow)],
  [0.25, hexToRgb(fletPalette.heatmap.moderate)],
  [0.50, hexToRgb(fletPalette.heatmap.retention)],
  [0.75, hexToRgb(fletPalette.heatmap.intense)],
  [1.00, hexToRgb(fletPalette.heatmap.congested)],
];

export class CongestionLevel {
  private readonly value: number; // 0.0 to 1.0

  constructor(rawCongestion: number) {
    // Normalizes 0-100 or 0.0-1.0 to strict [0.0, 1.0]
    let normalized = rawCongestion;
    if (normalized > 1.0) {
      normalized = normalized / 100.0;
    }
    this.value = Math.max(0.0, Math.min(1.0, normalized));
  }

  public getValue(): number {
    return this.value;
  }

  public getPercentage(): number {
    return Math.round(this.value * 100);
  }

  /**
   * Returns smooth RGB/HEX color matching CARINA HeatmapColorResolver.py and flet_color_palette.json:
   */
  public getColor(): string {
    const v = this.value;

    if (v <= 0) return fletPalette.heatmap.freeFlow;
    if (v >= 1) return fletPalette.heatmap.congested;

    for (let i = 0; i < HEATMAP_STOPS.length - 1; i++) {
      const [t1, c1] = HEATMAP_STOPS[i];
      const [t2, c2] = HEATMAP_STOPS[i + 1];
      if (v >= t1 && v <= t2) {
        const factor = (v - t1) / (t2 - t1);
        const r = Math.round(c1[0] + (c2[0] - c1[0]) * factor);
        const g = Math.round(c1[1] + (c2[1] - c1[1]) * factor);
        const b = Math.round(c1[2] + (c2[2] - c1[2]) * factor);
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
      }
    }

    return fletPalette.heatmap.congested;
  }

  /**
   * Road stroke width in pixels.
   */
  public getLineWidth(): number {
    return 6.5;
  }
}

