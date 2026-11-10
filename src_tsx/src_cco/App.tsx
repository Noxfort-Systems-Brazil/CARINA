// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState, useEffect } from 'react';
import { useCcoViewModel } from './presentation/hooks/useCcoViewModel';
import { CcoHeader } from './presentation/components/CcoHeader';
import { CcoMap } from './presentation/components/CcoMap';
import { EvpAlertToast } from './presentation/components/EvpAlertToast';
import { ThemeProvider, useCcoTheme } from './presentation/context/ThemeContext';
import { QuickSearchModal, SearchTarget } from './presentation/components/map/QuickSearchModal';
import { RenderedTrafficLight, RenderedIntersection } from './presentation/hooks/useCcoMapLayers';
import { RenderedStreet } from './domain/services/StreetTopologyGrouperService';

const AppContent: React.FC = () => {
  const { isDark } = useCcoTheme();
  const {
    topology,
    congestionMap,
    signals,
    emergencyVehicles,
    fleetSummary,
    connectionStatus,
    errorMessage,
  } = useCcoViewModel();

  const [activeCorpFilter, setActiveCorpFilter] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchTarget, setSearchTarget] = useState<SearchTarget | null>(null);
  const [searchableLayers, setSearchableLayers] = useState<{
    trafficLights: RenderedTrafficLight[];
    intersections: RenderedIntersection[];
    streets: RenderedStreet[];
  }>({ trafficLights: [], intersections: [], streets: [] });

  const totalSignals =
    Object.keys(signals).length ||
    (topology?.nodes.filter((n) => n.type === 'traffic_light').length ?? 0);

  // Global keyboard shortcut to open Quick Search (Ctrl+K or '/')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      } else if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleToggleCorpFilter = (corp: string) => {
    setActiveCorpFilter((prev) => (prev === corp ? null : corp));
  };

  const bgClass = isDark ? 'bg-[#020617]' : 'bg-[#F7F7F7]';

  return (
    <div className={`w-screen h-screen flex flex-col ${bgClass} overflow-hidden relative select-none transition-colors duration-300`}>
      <CcoHeader
        connectionStatus={connectionStatus}
        fleetSummary={fleetSummary}
        totalSignals={totalSignals}
        activeCorpFilter={activeCorpFilter}
        onToggleCorpFilter={handleToggleCorpFilter}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      <main className={`flex-1 w-full min-h-0 relative overflow-hidden ${bgClass}`}>
        <CcoMap
          topology={topology}
          congestionMap={congestionMap}
          signals={signals}
          emergencyVehicles={emergencyVehicles}
          filteredCorporation={activeCorpFilter}
          searchTarget={searchTarget}
          onClearSearchTarget={() => setSearchTarget(null)}
          onLayersReady={setSearchableLayers}
        />
        <EvpAlertToast alerts={fleetSummary.activeAlerts} />

        {errorMessage && (
          <div className="absolute top-2 sm:top-4 right-2 sm:right-4 z-40 bg-rose-950/90 border border-rose-500 text-rose-200 text-xs px-3 py-2 rounded-lg shadow-lg font-mono max-w-[calc(100vw-1rem)]">
            {errorMessage}
          </div>
        )}
      </main>

      {/* Quick Search & Auto-Focus Modal */}
      <QuickSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        vehicles={emergencyVehicles}
        trafficLights={searchableLayers.trafficLights}
        intersections={searchableLayers.intersections}
        streets={searchableLayers.streets}
        onSelectTarget={(target) => setSearchTarget(target)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
