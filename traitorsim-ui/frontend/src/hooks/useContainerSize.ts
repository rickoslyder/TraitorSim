/**
 * useContainerSize - Track container dimensions using ResizeObserver
 *
 * Returns the width and height of a container element, automatically updating
 * when the container is resized.
 */

import { useState, useEffect, RefObject } from 'react';

interface Size {
  width: number;
  height: number;
}

export function useContainerSize(ref: RefObject<HTMLElement>): Size {
  const [size, setSize] = useState<Size>({ width: 0, height: 0 });

  useEffect(() => {
    if (!ref.current) return;

    const element = ref.current;

    // Create observer
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setSize({ width, height });
      }
    });

    observer.observe(element);

    return () => observer.disconnect();
  }, [ref]);

  return size;
}

/**
 * useWindowSize - Track window dimensions
 */
export function useWindowSize(): Size {
  const [size, setSize] = useState<Size>(() => ({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  }));

  useEffect(() => {
    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return size;
}

/**
 * useReducedMotion - Check if user prefers reduced motion
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersReducedMotion;
}

/**
 * useTrustAnimation - Animate trust matrix transitions using requestAnimationFrame
 *
 * Provides smooth interpolation between trust matrix states with configurable duration
 * and easing. Respects reduced motion preference.
 */
export function useTrustAnimation(
  isAnimating: boolean,
  onProgress: (progress: number) => void,
  duration: number = 500 // ms
): void {
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!isAnimating) return;

    // Skip animation if user prefers reduced motion
    if (prefersReducedMotion) {
      onProgress(1);
      return;
    }

    let startTime: number | null = null;
    let animationFrameId: number;

    const animate = (timestamp: number) => {
      if (startTime === null) {
        startTime = timestamp;
      }

      const elapsed = timestamp - startTime;
      const linearProgress = Math.min(elapsed / duration, 1);

      // Apply easing (ease-out cubic for smooth deceleration)
      const easedProgress = 1 - Math.pow(1 - linearProgress, 3);

      onProgress(easedProgress);

      if (linearProgress < 1) {
        animationFrameId = requestAnimationFrame(animate);
      }
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isAnimating, onProgress, duration, prefersReducedMotion]);
}

/**
 * usePlaybackTimer - Auto-advance timeline based on playback state
 *
 * When playing, advances through phases/days at the specified speed.
 */
export function usePlaybackTimer(
  isPlaying: boolean,
  playbackSpeed: number,
  onAdvance: () => void,
  baseDurationMs: number = 2000 // Time per phase at 1x speed
): void {
  useEffect(() => {
    if (!isPlaying) return;

    const interval = baseDurationMs / playbackSpeed;

    const timerId = setInterval(() => {
      onAdvance();
    }, interval);

    return () => clearInterval(timerId);
  }, [isPlaying, playbackSpeed, onAdvance, baseDurationMs]);
}
