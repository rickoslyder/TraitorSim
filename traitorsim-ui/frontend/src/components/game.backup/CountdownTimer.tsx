/**
 * Visual countdown timer component.
 * Shows remaining time with urgency indicators.
 */

import { useCountdown } from '../../hooks/useCountdown';

interface CountdownTimerProps {
  deadline: string | null;
  totalSeconds?: number;
  warningThreshold?: number;
  criticalThreshold?: number;
  onExpire?: () => void;
  size?: 'sm' | 'md' | 'lg';
  showProgress?: boolean;
}

export function CountdownTimer({
  deadline,
  totalSeconds = 120,
  warningThreshold = 30,
  criticalThreshold = 10,
  onExpire,
  size = 'md',
  showProgress = true,
}: CountdownTimerProps) {
  const { formatted, percentage, urgency, isActive, isExpired } = useCountdown(
    deadline,
    totalSeconds,
    {
      warningThreshold,
      criticalThreshold,
      onExpire,
    }
  );

  if (!isActive && !isExpired) {
    return null;
  }

  // Size classes
  const sizeClasses = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-4xl',
  };

  // Color classes based on urgency
  const colorClasses = {
    normal: 'text-white',
    warning: 'text-yellow-400',
    critical: 'text-red-400 animate-pulse',
  };

  const progressColorClasses = {
    normal: 'bg-blue-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500',
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Timer display */}
      <div
        className={`font-mono font-bold tabular-nums ${sizeClasses[size]} ${colorClasses[urgency]}`}
      >
        {isExpired ? '00:00' : formatted}
      </div>

      {/* Progress bar */}
      {showProgress && !isExpired && (
        <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-[width] duration-1000 ease-linear ${progressColorClasses[urgency]}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}

      {/* Urgency indicator */}
      {urgency === 'critical' && !isExpired && (
        <p className="text-xs text-red-400 animate-pulse">Time running out!</p>
      )}
    </div>
  );
}
