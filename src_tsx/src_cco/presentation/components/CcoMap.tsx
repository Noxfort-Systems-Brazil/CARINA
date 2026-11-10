// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState, useEffect } from 'react';
import { MapTopology } from '../../domain/models/Topology';
import { TrafficLightPanelMap } from '../../domain/models/TrafficLight';
import { EmergencyVehicle } from '../../domain/models/EmergencyVehicle';
import { useMapViewport } from '../hooks/useMapViewport';
import { useCcoMapLayers, RenderedTrafficLight, RenderedIntersection } from '../hooks/useCcoMapLayers';
import { RenderedStreet } from '../../domain/services/StreetTopologyGrouperService';
import { GeoProjectionService } from '../../domain/services/GeoProjectionService';
import { MapGlowFilters } from './map/MapGlowFilters';
import { MapRoadsLayer } from './map/MapRoadsLayer';
import { MapIntersectionsLayer } from './map/MapIntersectionsLayer';
import { MapTrafficLightsLayer } from './map/MapTrafficLightsLayer';
import { MapEmergencyVehiclesLayer } from './map/MapEmergencyVehiclesLayer';
import { MapLegend } from './map/MapLegend';
import { MapZoomControls } from './map/MapZoomControls';
import { MapScaleBar } from './map/MapScaleBar';
import { InspectionBottomSheet, InspectionData } from './map/InspectionBottomSheet';
import { SearchTarget } from './map/QuickSearchModal';
import { useCcoTheme } from '../context/ThemeContext';

interface CcoMapProps {
  topology: MapTopology | null;
  congestionMap: Record<string, number>;
  signals: TrafficLightPanelMap;
  emergencyVehicles: EmergencyVehicle[];
  filteredCorporation?: string | null;
  searchTarget?: SearchTarget | null;
  onClearSearchTarget?: () => void;
  onLayersReady?: (data: {
    trafficLights: RenderedTrafficLight[];
    intersections: RenderedIntersection[];
    streets: RenderedStreet[];
  }) => void;
}

export const CcoMap: React.FC<CcoMapProps> = ({
  topology,
  congestionMap,
  signals,
  emergencyVehicles,
  filteredCorporation,
  searchTarget,
  onClearSearchTarget,
  onLayersReady,
}) => {
  const { isDark } = useCcoTheme();
  const [inspectionData, setInspectionData] = useState<InspectionData | null>(null);

  const {
    zoom,
    setZoom,
    pan,
    flyTo,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    handleWheel,
    handleReset,
  } = useMapViewport({
    onEscape: () => setInspectionData(null),
  });

  const {
    projection,
    renderedStreets,
    intersectionNodes,
    trafficLightNodes,
  } = useCcoMapLayers(topology, congestionMap, signals);

  // Notify parent about available searchable layers
  useEffect(() => {
    if (onLayersReady && (renderedStreets.length > 0 || trafficLightNodes.length > 0)) {
      onLayersReady({
        trafficLights: trafficLightNodes,
        intersections: intersectionNodes,
        streets: renderedStreets,
      });
    }
  }, [onLayersReady, renderedStreets, trafficLightNodes, intersectionNodes]);

  // Handle Quick Search Auto-Focus (flyTo)
  useEffect(() => {
    if (!searchTarget || !projection) return;

    if (searchTarget.type === 'vehicle') {
      const v = searchTarget.payload as EmergencyVehicle;
      setInspectionData({ vehicle: v });
      let px = v.x;
      let py = v.y;
      if (v.latitude !== undefined && v.longitude !== undefined && GeoProjectionService.isWgs84(v.latitude, v.longitude)) {
        const [cx, cy] = GeoProjectionService.geoToSumo(v.latitude, v.longitude);
        px = cx;
        py = cy;
      }
      flyTo(projection.tx(px), projection.ty(py), projection.centerX, projection.centerY, 2.5);
    } else if (searchTarget.type === 'trafficLight') {
      const tl = searchTarget.payload as RenderedTrafficLight;
      setInspectionData({ trafficLight: tl });
      flyTo(tl.cx, tl.cy, projection.centerX, projection.centerY, 2.5);
    } else if (searchTarget.type === 'intersection') {
      const n = searchTarget.payload as RenderedIntersection;
      setInspectionData({ intersection: n });
      flyTo(n.cx, n.cy, projection.centerX, projection.centerY, 2.5);
    } else if (searchTarget.type === 'street') {
      const s = searchTarget.payload as RenderedStreet;
      setInspectionData({ street: s });
    }

    onClearSearchTarget?.();
  }, [searchTarget, projection, flyTo, onClearSearchTarget]);

  if (!topology || !projection) {
    return (
      <div
        className={`w-full h-full flex items-center justify-center select-none ${
          isDark ? 'bg-[#020617]' : 'bg-[#F7F7F7]'
        }`}
      >
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p
            className={`text-sm font-semibold tracking-wide ${
              isDark ? 'text-slate-300' : 'text-slate-700'
            }`}
          >
            Carregando Topologia Viária do CARINA...
          </p>
        </div>
      </div>
    );
  }

  const bgClass = isDark ? 'bg-[#020617]' : 'bg-[#F7F7F7]';

  return (
    <div
      className={`w-full h-full flex-1 relative ${bgClass} overflow-hidden select-none cursor-grab active:cursor-grabbing touch-none transition-colors duration-300`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchEnd}
      onWheel={handleWheel}
    >
      {/* Canvas SVG do Mapa */}
      <svg
        className="w-full h-full pointer-events-none"
        viewBox={projection.viewBox}
        preserveAspectRatio="xMidYMid meet"
        onClick={() => setInspectionData(null)}
      >
        <MapGlowFilters />

        {/* Grupo de Pan & Zoom com escala isotrópica ancorada no centro */}
        <g
          transform={`translate(${pan.x}, ${pan.y}) translate(${projection.centerX}, ${projection.centerY}) scale(${zoom}) translate(${-projection.centerX}, ${-projection.centerY})`}
        >
          <MapRoadsLayer
            streets={renderedStreets}
            selectedStreetId={inspectionData?.street?.id}
            onSelectStreet={(street) => setInspectionData({ street })}
          />
          <MapIntersectionsLayer
            nodes={intersectionNodes}
            onSelectIntersection={(intersection) => setInspectionData({ intersection })}
          />
          <MapTrafficLightsLayer
            trafficLights={trafficLightNodes}
            onSelectTrafficLight={(trafficLight) => setInspectionData({ trafficLight })}
          />
          <MapEmergencyVehiclesLayer
            vehicles={emergencyVehicles}
            projection={projection}
            filteredCorporation={filteredCorporation}
            onSelectVehicle={(vehicle) => setInspectionData({ vehicle })}
          />
        </g>
      </svg>

      {/* Widgets Flutuantes de Overlay */}
      <MapLegend />
      <MapScaleBar
        zoom={zoom}
        scaleFactor={typeof window !== 'undefined' ? window.innerWidth / (projection.width || 800) : 1.0}
      />
      <MapZoomControls
        onZoomIn={() => setZoom((prev) => Math.min(prev * 1.25, 6.0))}
        onZoomOut={() => setZoom((prev) => Math.max(prev * 0.8, 0.5))}
        onReset={handleReset}
      />

      {/* Unified Inspection Bottom Sheet (Mobile) & Floating Card (Desktop) */}
      <InspectionBottomSheet
        data={inspectionData}
        onClose={() => setInspectionData(null)}
      />
    </div>
  );
};
