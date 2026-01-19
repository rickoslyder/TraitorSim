/**
 * Ready button component for the lobby.
 * Players toggle their ready status before the game starts.
 */

import { useState, useCallback } from 'react';

interface ReadyButtonProps {
  isReady: boolean;
  isConnected: boolean;
  onToggle: (ready: boolean) => void;
  disabled?: boolean;
}

export function ReadyButton({
  isReady,
  isConnected,
  onToggle,
  disabled = false,
}: ReadyButtonProps) {
  const [isToggling, setIsToggling] = useState(false);

  const handleClick = useCallback(async () => {
    if (disabled || isToggling || !isConnected) return;

    setIsToggling(true);
    try {
      onToggle(!isReady);
    } finally {
      // Small delay to prevent rapid toggling
      setTimeout(() => setIsToggling(false), 500);
    }
  }, [disabled, isToggling, isConnected, isReady, onToggle]);

  const isDisabled = disabled || isToggling || !isConnected;

  return (
    <button
      onClick={handleClick}
      disabled={isDisabled}
      className={`
        relative flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-semibold text-lg
        transition-transform transform
        ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 active:scale-95'}
        ${
          isReady
            ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-600/25'
            : 'bg-gray-600 hover:bg-gray-500 text-white'
        }
      `}
    >
      {/* Spinner when toggling */}
      {isToggling && (
        <svg
          className="w-5 h-5 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}

      {/* Icon */}
      {!isToggling && (
        <span className="text-xl">{isReady ? '✓' : '○'}</span>
      )}

      {/* Text */}
      <span>{isReady ? 'Ready!' : 'Ready Up'}</span>

      {/* Pulse animation when ready */}
      {isReady && !isToggling && (
        <span className="absolute inset-0 rounded-lg bg-green-400 animate-ping opacity-20" />
      )}
    </button>
  );
}
