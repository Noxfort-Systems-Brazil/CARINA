// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState, useEffect } from 'react';
import { StreamConnectionStatus } from '../../domain/contracts/ICcoStreamService';
import { FleetSummary } from '../../application/usecases/ManageEmergencyFleetUseCase';
import { ShieldAlert, Siren, Flame, Radio, Search, Sun, Moon, Maximize, Minimize } from 'lucide-react';
import { useCcoTheme } from '../context/ThemeContext';
import { triggerHaptic } from '../utils/haptics';
import carinaLogo from '../assets/carina-logo.png';

interface CcoHeaderProps {
  connectionStatus: StreamConnectionStatus;
  fleetSummary: FleetSummary;
  totalSignals: number;
  activeCorpFilter?: string | null;
  onToggleCorpFilter?: (corp: string) => void;
  onOpenSearch?: () => void;
}

export const CcoHeader: React.FC<CcoHeaderProps> = ({
  connectionStatus,
  fleetSummary,
  totalSignals,
  activeCorpFilter,
  onToggleCorpFilter,
  onOpenSearch,
}) => {
  const [timeStr, setTimeStr] = useState<string>('--:--:--');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const { isDark, toggleTheme } = useCcoTheme();

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleFsChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  const toggleFullscreen = () => {
    triggerHaptic(20);
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'CONNECTED':
        return (
          <div className="flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2.5 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/50 text-emerald-400 font-semibold tracking-wide shrink-0">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] sm:text-xs">ONLINE</span>
          </div>
        );
      case 'RECONNECTING':
        return (
          <div className="flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2.5 py-0.5 rounded-full bg-amber-950/80 border border-amber-500/50 text-amber-400 font-semibold tracking-wide shrink-0">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span className="text-[10px] sm:text-xs">REC</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2.5 py-0.5 rounded-full bg-rose-950/80 border border-rose-500/50 text-rose-400 font-semibold tracking-wide shrink-0">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-[10px] sm:text-xs">OFF</span>
          </div>
        );
    }
  };

  return (
    <header className="h-12 sm:h-14 md:h-16 bg-[#263238]/95 dark:bg-slate-950/95 border-b border-[#37474F] dark:border-slate-800 px-2 sm:px-4 md:px-6 flex items-center justify-between gap-1 sm:gap-3 z-20 shrink-0 shadow-md select-none overflow-hidden transition-colors">
      {/* Lado Esquerdo: Identidade do Sistema e Status de Conexão */}
      <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
        <div className="w-7 h-7 sm:w-8 sm:h-8 md:w-9 md:h-9 rounded-lg bg-[#37474F] dark:bg-slate-900 border border-cyan-500/40 flex items-center justify-center overflow-hidden p-0.5 sm:p-1 shadow-sm shrink-0">
          <img src={carinaLogo} alt="CARINA" className="w-full h-full object-contain" />
        </div>
        <div>
          <h1 className="text-xs sm:text-base md:text-lg font-bold tracking-wider text-white flex items-center gap-1">
            CARINA <span className="text-cyan-400 font-black">CCO</span>
          </h1>
          <p className="hidden md:block text-[10px] text-slate-300 dark:text-slate-400 font-mono tracking-widest uppercase">
            Videowall
          </p>
        </div>

        <div className="hidden xs:block h-4 sm:h-5 w-px bg-[#37474F] dark:bg-slate-800" />
        {getStatusBadge()}
      </div>

      {/* Centro: Crachás Interativos de Frota e Semáforos (Filtros Rápidos) */}
      <div className="flex items-center gap-1 sm:gap-2 overflow-x-auto scrollbar-none py-0.5 shrink-0 max-w-[40%] xs:max-w-none">
        {/* Semáforos */}
        <div
          className="flex items-center gap-1 px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded bg-[#37474F] dark:bg-slate-900 border border-[#455A64] dark:border-slate-800 shrink-0"
          title={`Semáforos Monitorados: ${totalSignals}`}
        >
          <Radio className="w-3 h-3 text-cyan-400 shrink-0" />
          <span className="hidden sm:inline text-[11px] text-slate-300 font-medium">Semáforos:</span>
          <span className="text-[11px] sm:text-xs font-bold text-white font-mono">{totalSignals}</span>
        </div>

        {/* SAMU */}
        <button
          onClick={() => {
            triggerHaptic(20);
            onToggleCorpFilter?.('SAMU');
          }}
          className={`flex items-center gap-1 px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded bg-rose-950/40 border transition-all cursor-pointer shrink-0 ${
            activeCorpFilter === 'SAMU'
              ? 'border-rose-400 ring-2 ring-rose-400/50 bg-rose-900/60'
              : 'border-rose-800/40 hover:border-rose-600/60'
          }`}
          title="Filtrar viaturas do SAMU"
        >
          <Siren className="w-3 h-3 text-rose-400 animate-pulse shrink-0" />
          <span className="hidden sm:inline text-[11px] text-rose-300 font-medium">SAMU:</span>
          <span className="text-[11px] sm:text-xs font-bold text-rose-200 font-mono">
            {fleetSummary.byCorporation.SAMU}
          </span>
        </button>

        {/* Bombeiros */}
        <button
          onClick={() => {
            triggerHaptic(20);
            onToggleCorpFilter?.('BOMBEIROS');
          }}
          className={`flex items-center gap-1 px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded bg-orange-950/40 border transition-all cursor-pointer shrink-0 ${
            activeCorpFilter === 'BOMBEIROS'
              ? 'border-orange-400 ring-2 ring-orange-400/50 bg-orange-900/60'
              : 'border-orange-800/40 hover:border-orange-600/60'
          }`}
          title="Filtrar viaturas dos Bombeiros"
        >
          <Flame className="w-3 h-3 text-orange-400 shrink-0" />
          <span className="hidden sm:inline text-[11px] text-orange-300 font-medium">Bombeiros:</span>
          <span className="text-[11px] sm:text-xs font-bold text-orange-200 font-mono">
            {fleetSummary.byCorporation.BOMBEIROS}
          </span>
        </button>

        {/* Polícia */}
        <button
          onClick={() => {
            triggerHaptic(20);
            onToggleCorpFilter?.('POLICIA');
          }}
          className={`flex items-center gap-1 px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded bg-blue-950/40 border transition-all cursor-pointer shrink-0 ${
            activeCorpFilter === 'POLICIA'
              ? 'border-blue-400 ring-2 ring-blue-400/50 bg-blue-900/60'
              : 'border-blue-800/40 hover:border-blue-600/60'
          }`}
          title="Filtrar viaturas da Polícia"
        >
          <ShieldAlert className="w-3 h-3 text-blue-400 shrink-0" />
          <span className="hidden sm:inline text-[11px] text-blue-300 font-medium">Polícia:</span>
          <span className="text-[11px] sm:text-xs font-bold text-blue-200 font-mono">
            {fleetSummary.byCorporation.POLICIA}
          </span>
        </button>
      </div>

      {/* Lado Direito: Ações (Busca, Tema, Tela Cheia) + Relógio Digital */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
        {/* Quick Search Button */}
        {onOpenSearch && (
          <button
            onClick={() => {
              triggerHaptic(20);
              onOpenSearch();
            }}
            className="p-1.5 sm:p-2 rounded-lg bg-[#37474F] dark:bg-slate-800 hover:bg-[#455A64] dark:hover:bg-slate-700 text-cyan-300 transition-colors cursor-pointer"
            title="Busca Rápida de Viaturas e Cruzamentos"
          >
            <Search className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </button>
        )}

        {/* Theme Toggle (☀️ Dia Cartográfico / 🌙 Noite Videowall) */}
        <button
          onClick={() => {
            triggerHaptic(20);
            toggleTheme();
          }}
          className="p-1.5 sm:p-2 rounded-lg bg-[#37474F] dark:bg-slate-800 hover:bg-[#455A64] dark:hover:bg-slate-700 text-amber-300 transition-colors cursor-pointer"
          title={isDark ? 'Mudar para Tema Cartográfico Claro' : 'Mudar para Tema Videowall Noturno'}
        >
          {isDark ? <Sun className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-300" /> : <Moon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-sky-300" />}
        </button>

        {/* Fullscreen Button */}
        <button
          onClick={toggleFullscreen}
          className="p-1.5 sm:p-2 rounded-lg bg-[#37474F] dark:bg-slate-800 hover:bg-[#455A64] dark:hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title={isFullscreen ? 'Sair da Tela Cheia' : 'Modo Tela Cheia (Imersivo)'}
        >
          {isFullscreen ? <Minimize className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Maximize className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
        </button>

        {/* Relógio Digital */}
        <div className="text-right pl-1">
          <div className="text-xs sm:text-base md:text-xl font-bold font-mono tracking-wider text-white tabular-nums">
            {timeStr}
          </div>
          <div className="hidden md:block text-[9px] text-slate-300 dark:text-slate-400 font-mono uppercase tracking-wider">
            Brasília
          </div>
        </div>
      </div>
    </header>
  );
};
