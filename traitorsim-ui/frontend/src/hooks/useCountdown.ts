import { useState, useEffect, useCallback } from 'react';

export interface UseCountdownOptions {
  initialSeconds: number;
  onComplete?: () => void;
}

export interface UseCountdownReturn {
  seconds: number;
  isRunning: boolean;
  start: () => void;
  pause: () => void;
  reset: () => void;
}

export function useCountdown({
  initialSeconds,
  onComplete,
}: UseCountdownOptions): UseCountdownReturn {
  const [seconds, setSeconds] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (!isRunning || seconds <= 0) return;

    const interval = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          setIsRunning(false);
          onComplete?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, seconds, onComplete]);

  const start = useCallback(() => setIsRunning(true), []);
  const pause = useCallback(() => setIsRunning(false), []);
  const reset = useCallback(() => {
    setIsRunning(false);
    setSeconds(initialSeconds);
  }, [initialSeconds]);

  return { seconds, isRunning, start, pause, reset };
}
