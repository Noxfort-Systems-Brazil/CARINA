// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { EmergencyVehicle } from '../../../domain/models/EmergencyVehicle';
import { GeoProjectionService } from '../../../domain/services/GeoProjectionService';
import { OrthographicProjection } from '../../../domain/services/MapProjectionService';
import fletPalette from '../../styles/flet_color_palette.json';

import { triggerHaptic } from '../../utils/haptics';

interface MapEmergencyVehiclesLayerProps {
  vehicles: EmergencyVehicle[];
  projection: OrthographicProjection;
  filteredCorporation?: string | null;
  onSelectVehicle: (vehicle: EmergencyVehicle) => void;
}

export const MapEmergencyVehiclesLayer: React.FC<MapEmergencyVehiclesLayerProps> = React.memo(({
  vehicles,
  projection,
  filteredCorporation,
  onSelectVehicle,
}) => {
  return (
    <g id="emergency-vehicles-layer">
      {/* Vehicle Markers */}
      <g id="emergency-vehicles">
        {vehicles.map((v) => {
          const corpUpper = String(v.corporation || '').toUpperCase();
          const isDimmed = filteredCorporation && !corpUpper.includes(filteredCorporation.toUpperCase());
        let px = v.x;
        let py = v.y;

        // Canonical projection without passing min_x offset (eliminates 16.7m error)
        if (v.latitude !== undefined && v.longitude !== undefined && GeoProjectionService.isWgs84(v.latitude, v.longitude)) {
          const [cx, cy] = GeoProjectionService.geoToSumo(v.latitude, v.longitude);
          px = cx;
          py = cy;
        } else if (GeoProjectionService.isWgs84(py, px)) {
          const [cx, cy] = GeoProjectionService.geoToSumo(py, px);
          px = cx;
          py = cy;
        }

        const vx = projection.tx(px);
        const vy = projection.ty(py);

        const isAlert = Boolean(v.sirenActive) || Boolean(v.isEvpTriggered) || v.state === 'PREEMPTING';

        // Colors and shapes according to ui/widgets/evp_vehicle_marker.py
        const corpStr = String(v.corporation || '').toUpperCase();
        const isSamu = corpStr.includes('SAMU');
        const isBombeiro = corpStr.includes('BOMB');

        let alertColor = fletPalette.evp.policia.alert;
        let baseColor = fletPalette.evp.policia.base;
        let auraColor = fletPalette.evp.policia.aura;
        let strokeColor = fletPalette.evp.policia.stroke;

        if (isSamu) {
          alertColor = fletPalette.evp.samu.alert;
          baseColor = fletPalette.evp.samu.base;
          auraColor = fletPalette.evp.samu.aura;
          strokeColor = fletPalette.evp.samu.stroke;
        } else if (isBombeiro) {
          alertColor = fletPalette.evp.bombeiros.alert;
          baseColor = fletPalette.evp.bombeiros.base;
          auraColor = fletPalette.evp.bombeiros.aura;
          strokeColor = fletPalette.evp.bombeiros.stroke;
        }

        const currentFill = isAlert ? alertColor : baseColor;
        const heading = v.headingDeg || 0;

        return (
          <g
            key={`evp-${v.vehicleId}`}
            style={{
              transform: `translate(${vx}px, ${vy}px)`,
              transition: 'transform 0.4s cubic-bezier(0.25, 0.1, 0.25, 1), opacity 0.3s ease',
              willChange: 'transform',
              opacity: isDimmed ? 0.22 : 1,
            }}
            className="cursor-pointer pointer-events-auto"
            onClick={(e) => {
              e.stopPropagation();
              triggerHaptic(25);
              onSelectVehicle(v);
            }}
          >
            <title>{`${v.corporation} | ${v.vehicleId} | ${v.speedKmh.toFixed(1)} km/h | Proa: ${Math.round(heading)}° | Estado: ${v.state}`}</title>

            {/* Siren ring expanding and pulsating smoothly (GPU Compositor Thread) */}
            {isAlert && (
              <circle
                cx={0}
                cy={0}
                r={10}
                fill="none"
                stroke={auraColor}
                strokeWidth={2}
                className="animate-evp-aura pointer-events-none"
              />
            )}

            {/* Geometric marker rotated by headingDeg with rhythmic smooth flashing (1.0s) */}
            <g
              style={{
                transform: `rotate(${heading}deg)`,
                transition: 'transform 0.35s ease-out',
                transformOrigin: '0px 0px',
              }}
            >
              {isSamu && (
                /* SAMU triangle (pointing north at 0° rotation) */
                <polygon
                  points="0,-8 7,7 -7,7"
                  fill={currentFill}
                  stroke={strokeColor}
                  strokeWidth={1.5}
                  strokeLinejoin="round"
                  className={isAlert ? 'animate-evp-blink' : undefined}
                />
              )}

              {isBombeiro && (
                /* Fire Department square with directional indicator */
                <g className={isAlert ? 'animate-evp-blink' : undefined}>
                  <rect
                    x={-6}
                    y={-6}
                    width={12}
                    height={12}
                    rx={2}
                    fill={currentFill}
                    stroke={strokeColor}
                    strokeWidth={1.5}
                  />
                  <polygon points="0,-8 2.5,-5.5 -2.5,-5.5" fill={strokeColor} />
                </g>
              )}

              {!isSamu && !isBombeiro && (
                /* Police circle with directional indicator */
                <g className={isAlert ? 'animate-evp-blink' : undefined}>
                  <circle
                    cx={0}
                    cy={0}
                    r={6.5}
                    fill={currentFill}
                    stroke={strokeColor}
                    strokeWidth={1.5}
                  />
                  <polygon points="0,-8.5 2.5,-5.5 -2.5,-5.5" fill={strokeColor} />
                </g>
              )}
            </g>

            {/* Subtle badge with vehicle ID from palette */}
            <rect
              x={-16}
              y={10}
              width={32}
              height={11}
              rx={2.5}
              fill={fletPalette.evp.badgeBackground}
              opacity={0.88}
            />
            <text
              x={0}
              y={18}
              textAnchor="middle"
              fill={fletPalette.evp.badgeText}
              fontSize={7.5}
              fontWeight="bold"
              fontFamily="monospace"
              className="select-none pointer-events-none"
            >
              {v.vehicleId.slice(-5)}
            </text>
          </g>
        );
      })}
      </g>
    </g>
  );
});

MapEmergencyVehiclesLayer.displayName = 'MapEmergencyVehiclesLayer';

