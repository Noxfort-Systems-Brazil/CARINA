// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { useState, useRef, useCallback, useEffect } from 'react';

interface UseMapViewportOptions {
  onEscape?: () => void;
}

export function useMapViewport({ onEscape }: UseMapViewportOptions = {}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const rafPanRef = useRef<number | null>(null);
  const pendingPanRef = useRef<{ x: number; y: number } | null>(null);

  const schedulePan = useCallback((newPan: { x: number; y: number }) => {
    pendingPanRef.current = newPan;
    if (!rafPanRef.current) {
      rafPanRef.current = requestAnimationFrame(() => {
        if (pendingPanRef.current) {
          setPan(pendingPanRef.current);
        }
        rafPanRef.current = null;
      });
    }
  }, []);

  useEffect(() => {
    return () => {
      if (rafPanRef.current) {
        cancelAnimationFrame(rafPanRef.current);
      }
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  }, [pan.x, pan.y]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    schedulePan({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  }, [isDragging, schedulePan]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Touch support on mobile devices (1-finger pan, 2-finger pinch)
  const touchStartDistRef = useRef<number | null>(null);
  const touchStartZoomRef = useRef<number>(1);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      setIsDragging(true);
      dragStartRef.current = { x: touch.clientX - pan.x, y: touch.clientY - pan.y };
    } else if (e.touches.length === 2) {
      setIsDragging(false);
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      touchStartDistRef.current = Math.hypot(dx, dy);
      touchStartZoomRef.current = zoom;
    }
  }, [pan.x, pan.y, zoom]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 1 && isDragging) {
      const touch = e.touches[0];
      schedulePan({
        x: touch.clientX - dragStartRef.current.x,
        y: touch.clientY - dragStartRef.current.y,
      });
    } else if (e.touches.length === 2 && touchStartDistRef.current) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const ratio = dist / touchStartDistRef.current;
      setZoom(Math.min(Math.max(touchStartZoomRef.current * ratio, 0.5), 6.0));
    }
  }, [isDragging, schedulePan]);


  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    touchStartDistRef.current = null;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((prev) => Math.min(Math.max(prev * factor, 0.5), 6.0));
  }, []);

  const handleReset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    onEscape?.();
  }, [onEscape]);

  // Videowall keyboard shortcuts (+, -, 0 for reset, Esc to deselect)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '+' || e.key === '=') {
        setZoom((prev) => Math.min(prev * 1.25, 6.0));
      } else if (e.key === '-' || e.key === '_') {
        setZoom((prev) => Math.max(prev * 0.8, 0.5));
      } else if (e.key === '0') {
        handleReset();
      } else if (e.key === 'Escape') {
        onEscape?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleReset, onEscape]);

  const animationFrameRef = useRef<number | null>(null);

  const flyTo = useCallback(
    (
      targetX: number,
      targetY: number,
      centerX: number,
      centerY: number,
      targetZoom: number = 2.2
    ) => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      const startPan = { ...pan };
      const startZoom = zoom;
      const endZoom = Math.min(Math.max(targetZoom, 0.5), 6.0);
      const endPan = {
        x: -(targetX - centerX) * endZoom,
        y: -(targetY - centerY) * endZoom,
      };

      const startTime = performance.now();
      const duration = 450;

      const step = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);

        setZoom(startZoom + (endZoom - startZoom) * ease);
        setPan({
          x: startPan.x + (endPan.x - startPan.x) * ease,
          y: startPan.y + (endPan.y - startPan.y) * ease,
        });

        if (progress < 1) {
          animationFrameRef.current = requestAnimationFrame(step);
        } else {
          animationFrameRef.current = null;
        }
      };

      animationFrameRef.current = requestAnimationFrame(step);
    },
    [pan, zoom]
  );

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return {
    zoom,
    setZoom,
    pan,
    setPan,
    isDragging,
    flyTo,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    handleWheel,
    handleReset,
  };
}
