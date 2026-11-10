// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedStreet } from '../../../domain/services/StreetTopologyGrouperService';
import fletPalette from '../../styles/flet_color_palette.json';

import { triggerHaptic } from '../../utils/haptics';

interface MapRoadsLayerProps {
  streets: RenderedStreet[];
  selectedStreetId?: string;
  onSelectStreet?: (street: RenderedStreet) => void;
}

export const MapRoadsLayer: React.FC<MapRoadsLayerProps> = React.memo(({
  streets,
  selectedStreetId,
  onSelectStreet,
}) => {
  return (
    <>
      {/* Camada 1: Casing externo das Vias (strokeWidth=11.5) */}
      <g id="roads-casing">
        {streets.map((street) => {
          const isSelected = selectedStreetId === street.id;
          return (
            <path
              key={`casing-${street.id}`}
              d={street.pathD}
              fill="none"
              stroke={isSelected ? '#00e5ff' : fletPalette.map.roadCasing}
              strokeWidth={isSelected ? 14 : 11.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={isSelected ? 1.0 : 0.92}
            />
          );
        })}
      </g>

      {/* Camada 2: Preenchimento do Heatmap das Vias (strokeWidth=7.0) */}
      <g id="roads-heatmap">
        {streets.map((street) => (
          <path
            key={`heatmap-${street.id}`}
            d={street.pathD}
            fill="none"
            stroke={street.color}
            strokeWidth={7.0}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="cursor-pointer pointer-events-auto transition-opacity hover:opacity-80"
            onClick={(e) => {
              e.stopPropagation();
              triggerHaptic(15);
              onSelectStreet?.(street);
            }}
          >
            <title>{`${street.name || street.id} | Congestionamento: ${Math.round(street.congestion)}%`}</title>
          </path>
        ))}
      </g>
    </>
  );
});

MapRoadsLayer.displayName = 'MapRoadsLayer';

