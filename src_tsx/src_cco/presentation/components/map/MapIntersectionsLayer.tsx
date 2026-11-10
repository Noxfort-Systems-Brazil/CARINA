// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedIntersection } from '../../hooks/useCcoMapLayers';
import fletPalette from '../../styles/flet_color_palette.json';

import { triggerHaptic } from '../../utils/haptics';

interface MapIntersectionsLayerProps {
  nodes: RenderedIntersection[];
  onSelectIntersection?: (node: RenderedIntersection) => void;
}

export const MapIntersectionsLayer: React.FC<MapIntersectionsLayerProps> = React.memo(({
  nodes,
  onSelectIntersection,
}) => {
  return (
    <g id="intersections">
      {nodes.map((n) => (
        <g
          key={`node-${n.id}`}
          className="cursor-pointer pointer-events-auto transition-transform hover:scale-125"
          onClick={(e) => {
            e.stopPropagation();
            triggerHaptic(20);
            onSelectIntersection?.(n);
          }}
        >
          <title>{`Cruzamento ${n.id}`}</title>
          {/* Invisible touch area */}
          <circle cx={n.cx} cy={n.cy} r={16} fill="transparent" />
          <circle cx={n.cx} cy={n.cy} r={6.5} fill={fletPalette.map.intersectionBorder} />
          <circle cx={n.cx} cy={n.cy} r={4.5} fill={fletPalette.map.intersectionCore} />
        </g>
      ))}
    </g>
  );
});

MapIntersectionsLayer.displayName = 'MapIntersectionsLayer';

