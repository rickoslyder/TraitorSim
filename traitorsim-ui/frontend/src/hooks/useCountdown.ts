import { useState, useEffect, useCallback, useMemo } from 'react';

export interface UseCountdownOptions {
  warningThreshold?: number;
  criticalThreshold?: number;
  onExpire?: () => void;
}

export interface UseCountdownReturn {
  seconds: number;
  formatted: string;
  percentage: number;
  urgency: 'normal' | 'warning' | 'critical';
  isActive: boolean;
  isExpired: boolean;
  start: () => void;
  pause: () => void;
  reset: () => void;
}

export function useCountdown(
  deadline: string | null,
  totalSeconds: number,
  options: UseCountdownOptions = {}
): UseCountdownReturn {
  const { warningThreshold = 30, criticalThreshold = 10, onExpire } = options;

  const calculateSeconds = useCallback(() => {
    if (!deadline) return totalSeconds;
    const remaining = Math.floor((new Date(deadline).getTime() - Date.now()) / 1000);
    return Math.max(0, remaining);
  }, [deadline, totalSeconds]);

  const [seconds, setSeconds] = useState(calculateSeconds);
  const [isActive, setIsActive] = useState(!!deadline);

  useEffect(() => {
    if (!deadline) {
      setIsActive(false);
      return;
    }
    setIsActive(true);
    setSeconds(calculateSeconds());

    const interval = setInterval(() => {
      const remaining = calculateSeconds();
      setSeconds(remaining);
      if (remaining <= 0) {
        setIsActive(false);
        onExpire?.();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [deadline, calculateSeconds, onExpire]);

  const formatted = useMemo(() => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, [seconds]);

  const percentage = useMemo(() => {
    return Math.min(100, (seconds / totalSeconds) * 100);
  }, [seconds, totalSeconds]);

  const urgency: 'normal' | 'warning' | 'critical' = useMemo(() => {
    if (seconds <= criticalThreshold) return 'critical';
    if (seconds <= warningThreshold) return 'warning';
    return 'normal';
  }, [seconds, warningThreshold, criticalThreshold]);

  const isExpired = seconds <= 0;

  const start = useCallback(() => setIsActive(true), []);
  const pause = useCallback(() => setIsActive(false), []);
  const reset = useCallback(() => {
    setIsActive(false);
    setSeconds(totalSeconds);
  }, [totalSeconds]);

  return {
    seconds,
    formatted,
    percentage,
    urgency,
    isActive,
    isExpired,
    start,
    pause,
    reset,
  };
}
