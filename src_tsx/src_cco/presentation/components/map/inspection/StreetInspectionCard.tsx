// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedStreet } from '../../../../domain/services/StreetTopologyGrouperService';
import { Activity } from 'lucide-react';

interface StreetInspectionCardProps {
  street: RenderedStreet;
}

export const StreetInspectionHeader: React.FC<StreetInspectionCardProps> = ({ street }) => (
  <span className="text-sm sm:text-base font-bold tracking-wide text-amber-300 flex items-center gap-1.5">
    <Activity className="w-4 h-4 text-amber-400" /> {street.name || street.id}
  </span>
);

export const StreetInspectionBody: React.FC<StreetInspectionCardProps> = ({ street }) => (
  <>
    <div className="flex items-center justify-between">
      <span className="text-slate-400">Nível de Congestionamento:</span>
      <span className="font-mono font-bold text-slate-100">
        {Math.round(street.congestion)}%
      </span>
    </div>
    {/* Visual Congestion Bar */}
    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
      <div
        style={{
          width: `${Math.min(street.congestion, 100)}%`,
          backgroundColor: street.color,
        }}
        className="h-full rounded-full transition-all duration-300"
      />
    </div>
    <div className="flex items-center justify-between pt-1">
      <span className="text-slate-400 text-[11px]">Status:</span>
      <span className="font-bold text-[11px]" style={{ color: street.color }}>
        {street.congestion < 25
          ? 'Fluxo Livre'
          : street.congestion < 50
          ? 'Moderado'
          : street.congestion < 75
          ? 'Retenção'
          : 'Congestionado'}
      </span>
    </div>
  </>
);
