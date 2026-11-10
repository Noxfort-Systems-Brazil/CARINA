// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedTrafficLight } from '../../hooks/useCcoMapLayers';
import fletPalette from '../../styles/flet_color_palette.json';

import { triggerHaptic } from '../../utils/haptics';

interface MapTrafficLightsLayerProps {
  trafficLights: RenderedTrafficLight[];
  onSelectTrafficLight?: (trafficLight: RenderedTrafficLight) => void;
}

export const MapTrafficLightsLayer: React.FC<MapTrafficLightsLayerProps> = React.memo(({
  trafficLights,
  onSelectTrafficLight,
}) => {
  return (
    <g id="traffic-lights">
      {trafficLights.map((tl) => {
        const isGreen = tl.displayState === 'GREEN';
        const isYellow = tl.displayState === 'YELLOW' || tl.displayState === 'FLASHING_YELLOW';
        const isRed = tl.displayState === 'RED' || (!isGreen && !isYellow);

        return (
          <g
            key={`tl-${tl.id}`}
            transform={`translate(${tl.cx}, ${tl.cy})`}
            className="pointer-events-auto cursor-pointer transition-transform hover:scale-110"
            onClick={(e) => {
              e.stopPropagation();
              triggerHaptic(25);
              onSelectTrafficLight?.(tl);
            }}
          >
            <title>{`Semáforo ${tl.id} | Fase ${tl.phase} | Estado: ${tl.displayState}`}</title>
            {/* Expanded invisible touch hit area for mobile fingertips */}
            <rect x={-16} y={-26} width={32} height={52} fill="transparent" />
            {/* Caixa do semáforo com cantos arredondados */}
            <rect
              x={-9}
              y={-22}
              width={18}
              height={44}
              rx={4.5}
              fill={fletPalette.trafficLights.box}
              stroke={fletPalette.trafficLights.border}
              strokeWidth={1.2}
            />

            {/* Lâmpada Vermelha (Topo) */}
            {isRed && <circle cx={0} cy={-12} r={8.5} fill="url(#halo-red)" pointerEvents="none" />}
            <circle
              cx={0}
              cy={-12}
              r={4.2}
              fill={fletPalette.trafficLights.red}
              opacity={isRed ? 1.0 : fletPalette.trafficLights.inactiveOpacity}
            />

            {/* Lâmpada Amarela (Centro) */}
            {isYellow && <circle cx={0} cy={0} r={8.5} fill="url(#halo-yellow)" pointerEvents="none" />}
            <circle
              cx={0}
              cy={0}
              r={4.2}
              fill={fletPalette.trafficLights.yellow}
              opacity={isYellow ? 1.0 : fletPalette.trafficLights.inactiveOpacity}
            />

            {/* Lâmpada Verde (Base) */}
            {isGreen && <circle cx={0} cy={12} r={8.5} fill="url(#halo-green)" pointerEvents="none" />}
            <circle
              cx={0}
              cy={12}
              r={4.2}
              fill={fletPalette.trafficLights.green}
              opacity={isGreen ? 1.0 : fletPalette.trafficLights.inactiveOpacity}
            />
          </g>
        );
      })}
    </g>
  );
});

MapTrafficLightsLayer.displayName = 'MapTrafficLightsLayer';

