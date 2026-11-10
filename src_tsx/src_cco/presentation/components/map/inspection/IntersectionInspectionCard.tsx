// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedIntersection } from '../../../hooks/useCcoMapLayers';
import { MapPin } from 'lucide-react';

interface IntersectionInspectionCardProps {
  intersection: RenderedIntersection;
}

export const IntersectionInspectionHeader: React.FC<IntersectionInspectionCardProps> = ({ intersection }) => (
  <span className="text-sm sm:text-base font-bold tracking-wide text-cyan-300 flex items-center gap-1.5">
    <MapPin className="w-4 h-4 text-cyan-400" /> Nó: {intersection.id}
  </span>
);

export const IntersectionInspectionBody: React.FC<IntersectionInspectionCardProps> = ({ intersection }) => (
  <>
    <div className="flex items-center justify-between">
      <span className="text-slate-400">Tipo de Nó:</span>
      <span className="font-bold text-slate-100">Cruzamento Físico</span>
    </div>
    <div className="flex items-center justify-between">
      <span className="text-slate-400">Posição:</span>
      <span className="font-mono text-slate-300 text-[11px]">
        X: {Math.round(intersection.cx)} • Y: {Math.round(intersection.cy)}
      </span>
    </div>
    <div className="pt-2 border-t border-[#37474F] dark:border-slate-800">
      <span className="text-slate-400 text-[11px]">Prioridade Viária: Normal</span>
    </div>
  </>
);
