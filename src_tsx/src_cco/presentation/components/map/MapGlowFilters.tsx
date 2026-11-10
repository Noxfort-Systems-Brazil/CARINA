// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';

export const MapGlowFilters: React.FC = () => {
  return (
    <defs>
      {/* GPU-friendly hardware accelerated Radial Gradients (zero convolution penalty) */}
      <radialGradient id="halo-green" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#00e676" stopOpacity="0.85" />
        <stop offset="60%" stopColor="#00e676" stopOpacity="0.35" />
        <stop offset="100%" stopColor="#00e676" stopOpacity="0" />
      </radialGradient>
      <radialGradient id="halo-red" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#ff334b" stopOpacity="0.85" />
        <stop offset="60%" stopColor="#ff334b" stopOpacity="0.35" />
        <stop offset="100%" stopColor="#ff334b" stopOpacity="0" />
      </radialGradient>
      <radialGradient id="halo-yellow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#ffd600" stopOpacity="0.85" />
        <stop offset="60%" stopColor="#ffd600" stopOpacity="0.35" />
        <stop offset="100%" stopColor="#ffd600" stopOpacity="0" />
      </radialGradient>

      {/* Lightweight fallback SVG filters */}
      <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.5" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.5" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id="glow-yellow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.5" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
  );
};

