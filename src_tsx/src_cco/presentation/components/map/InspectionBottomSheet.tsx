// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useRef, useState } from 'react';
import { EmergencyVehicle } from '../../../domain/models/EmergencyVehicle';
import { RenderedTrafficLight, RenderedIntersection } from '../../hooks/useCcoMapLayers';
import { RenderedStreet } from '../../../domain/services/StreetTopologyGrouperService';
import { X } from 'lucide-react';
import { triggerHaptic } from '../../utils/haptics';
import {
  VehicleInspectionHeader,
  VehicleInspectionBody,
} from './inspection/VehicleInspectionCard';
import {
  TrafficLightInspectionHeader,
  TrafficLightInspectionBody,
} from './inspection/TrafficLightInspectionCard';
import {
  IntersectionInspectionHeader,
  IntersectionInspectionBody,
} from './inspection/IntersectionInspectionCard';
import {
  StreetInspectionHeader,
  StreetInspectionBody,
} from './inspection/StreetInspectionCard';

export interface InspectionData {
  vehicle?: EmergencyVehicle | null;
  trafficLight?: RenderedTrafficLight | null;
  intersection?: RenderedIntersection | null;
  street?: RenderedStreet | null;
}

interface InspectionBottomSheetProps {
  data: InspectionData | null;
  onClose: () => void;
}

export const InspectionBottomSheet: React.FC<InspectionBottomSheetProps> = ({
  data,
  onClose,
}) => {
  const [dragOffset, setDragOffset] = useState<number>(0);
  const touchStartY = useRef<number | null>(null);

  if (!data) return null;
  const { vehicle, trafficLight, intersection, street } = data;
  if (!vehicle && !trafficLight && !intersection && !street) return null;

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (touchStartY.current === null) return;
    const currentY = e.touches[0].clientY;
    const diff = currentY - touchStartY.current;
    if (diff > 0) {
      setDragOffset(diff);
    }
  };

  const handleTouchEnd = () => {
    if (dragOffset > 70) {
      triggerHaptic(30);
      onClose();
    }
    setDragOffset(0);
    touchStartY.current = null;
  };

  return (
    <div
      style={{
        transform: dragOffset > 0 ? `translateY(${dragOffset}px)` : undefined,
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      className="fixed inset-x-0 bottom-0 sm:inset-x-auto sm:top-4 sm:bottom-auto sm:left-4 z-40 bg-[#263238]/95 dark:bg-slate-900/95 border-t sm:border border-[#37474F] dark:border-slate-800 rounded-t-2xl sm:rounded-xl p-4 shadow-2xl backdrop-blur-md text-slate-100 max-w-none sm:max-w-xs w-auto sm:w-full pointer-events-auto select-none transition-transform"
    >
      {/* Mobile Swipe Grab Handle */}
      <div className="sm:hidden w-12 h-1.5 bg-slate-500/60 rounded-full mx-auto mb-2 cursor-grab" />

      {/* HEADER */}
      <div className="flex items-center justify-between pb-2 border-b border-[#37474F] dark:border-slate-800">
        <div className="flex items-center gap-2">
          {vehicle && <VehicleInspectionHeader vehicle={vehicle} />}
          {trafficLight && <TrafficLightInspectionHeader trafficLight={trafficLight} />}
          {intersection && <IntersectionInspectionHeader intersection={intersection} />}
          {street && <StreetInspectionHeader street={street} />}
        </div>

        <button
          onClick={() => {
            triggerHaptic(20);
            onClose();
          }}
          className="p-1 rounded-md hover:bg-[#37474F] dark:hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Fechar (Esc)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* BODY CONTENT */}
      <div className="mt-3 space-y-2 text-xs">
        {vehicle && <VehicleInspectionBody vehicle={vehicle} />}
        {trafficLight && <TrafficLightInspectionBody trafficLight={trafficLight} />}
        {intersection && <IntersectionInspectionBody intersection={intersection} />}
        {street && <StreetInspectionBody street={street} />}
      </div>
    </div>
  );
};
