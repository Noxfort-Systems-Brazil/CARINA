// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

/**
 * Triggers a subtle tactile haptic vibration on supported mobile devices.
 * Gracefully no-ops on desktop or unsupported browsers.
 */
export function triggerHaptic(durationMs: number = 20): void {
  if (typeof window !== 'undefined' && 'navigator' in window && 'vibrate' in navigator) {
    try {
      navigator.vibrate(durationMs);
    } catch {
      // Ignore security or permission restrictions
    }
  }
}
