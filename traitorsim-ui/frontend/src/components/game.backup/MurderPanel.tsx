/**
 * Murder target selection panel for Traitors.
 * Shown during the night phase for traitor players.
 */

import { useState } from 'react';
import { CountdownTimer } from './CountdownTimer';

interface MurderTarget {
  id: string;
  name: string;
  alive: boolean;
}

interface MurderPanelProps {
  targets: MurderTarget[];
  deadline: string;
  totalSeconds?: number;
  onSelect: (targetId: string) => void;
  disabled?: boolean;
  fellowTraitors?: { id: string; name: string }[];
}

export function MurderPanel({
  targets,
  deadline,
  totalSeconds = 120,
  onSelect,
  disabled = false,
  fellowTraitors = [],
}: MurderPanelProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);

  const handleConfirm = () => {
    if (selectedTarget && !isConfirmed && !disabled) {
      setIsConfirmed(true);
      onSelect(selectedTarget);
    }
  };

  // Filter out fellow traitors and dead players
  const traitorIds = new Set(fellowTraitors.map((t) => t.id));
  const availableTargets = targets.filter(
    (t) => t.alive && !traitorIds.has(t.id)
  );

  return (
    <div className="bg-gradient-to-br from-gray-900 to-red-950/30 border border-red-800/50 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-red-400 flex items-center gap-2">
            <span>🗡️</span> Choose Your Victim
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Select a Faithful to murder tonight.
          </p>
        </div>
        <CountdownTimer
          deadline={deadline}
          totalSeconds={totalSeconds}
          size="md"
          showProgress={false}
        />
      </div>

      {/* Fellow traitors reminder */}
      {fellowTraitors.length > 0 && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-red-400">Fellow Traitors:</span>
          <span className="text-gray-300">
            {fellowTraitors.map((t) => t.name).join(', ')}
          </span>
        </div>
      )}

      {/* Target selection */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {availableTargets.map((target) => (
          <button
            key={target.id}
            onClick={() => !isConfirmed && !disabled && setSelectedTarget(target.id)}
            disabled={isConfirmed || disabled}
            className={`
              relative flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors transition-transform
              ${
                selectedTarget === target.id
                  ? 'border-red-500 bg-red-500/20 shadow-lg shadow-red-500/20'
                  : 'border-gray-700 bg-gray-800/50 hover:border-red-600/50'
              }
              ${isConfirmed || disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {/* Avatar */}
            <div className="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center text-xl">
              {target.name.charAt(0).toUpperCase()}
            </div>

            {/* Name */}
            <span className="text-sm font-medium text-white text-center truncate w-full">
              {target.name}
            </span>

            {/* Selection indicator */}
            {selectedTarget === target.id && (
              <div className="absolute top-2 right-2">
                <span className="text-xl">🗡️</span>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Confirm button */}
      <div className="flex justify-center">
        <button
          onClick={handleConfirm}
          disabled={!selectedTarget || isConfirmed || disabled}
          className={`
            flex items-center gap-2 px-8 py-3 rounded-lg font-semibold text-lg transition-colors transition-transform
            ${
              selectedTarget && !isConfirmed && !disabled
                ? 'bg-gradient-to-r from-red-700 to-red-600 hover:from-red-600 hover:to-red-500 text-white shadow-lg shadow-red-600/25'
                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          {isConfirmed ? (
            <>
              <span>🗡️</span>
              Target Confirmed
            </>
          ) : (
            <>Confirm Target</>
          )}
        </button>
      </div>

      {/* Confirmation text */}
      {isConfirmed && selectedTarget && (
        <p className="text-center text-gray-400">
          <span className="text-red-400 font-medium">
            {targets.find((t) => t.id === selectedTarget)?.name}
          </span>{' '}
          will not survive the night.
        </p>
      )}
    </div>
  );
}
