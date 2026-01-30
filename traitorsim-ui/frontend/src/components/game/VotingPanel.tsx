/**
 * Voting panel for round table banishment votes.
 * Displays available targets and allows vote selection.
 */

import { useState } from 'react';
import { CountdownTimer } from './CountdownTimer';

interface VotingTarget {
  id: string;
  name: string;
  alive: boolean;
}

interface VotingPanelProps {
  targets: VotingTarget[];
  deadline: string;
  totalSeconds?: number;
  onVote: (targetId: string) => void;
  disabled?: boolean;
  myPlayerId?: string;
}

export function VotingPanel({
  targets,
  deadline,
  totalSeconds = 120,
  onVote,
  disabled = false,
  myPlayerId,
}: VotingPanelProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);

  const handleConfirm = () => {
    if (selectedTarget && !isConfirmed && !disabled) {
      setIsConfirmed(true);
      onVote(selectedTarget);
    }
  };

  const availableTargets = targets.filter(
    (t) => t.alive && t.id !== myPlayerId
  );

  return (
    <div className="bg-gray-800 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🗳️</span> Round Table Vote
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Choose wisely. A wrong vote could doom the Faithful.
          </p>
        </div>
        <CountdownTimer
          deadline={deadline}
          totalSeconds={totalSeconds}
          size="md"
          showProgress={false}
        />
      </div>

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
                  ? 'border-red-500 bg-red-500/20'
                  : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
              }
              ${isConfirmed || disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            aria-label={`Vote for ${target.name}`}
          >
            {/* Avatar placeholder */}
            <div className="w-12 h-12 rounded-full bg-gray-600 flex items-center justify-center text-xl" aria-hidden="true">
              {target.name.charAt(0).toUpperCase()}
            </div>

            {/* Name */}
            <span className="text-sm font-medium text-white text-center truncate w-full">
              {target.name}
            </span>

            {/* Selection indicator */}
            {selectedTarget === target.id && (
              <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
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
                ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/25'
                : 'bg-gray-600 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          {isConfirmed ? (
            <>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              Vote Cast
            </>
          ) : (
            <>Confirm Vote</>
          )}
        </button>
      </div>

      {/* Confirmation text */}
      {isConfirmed && selectedTarget && (
        <p className="text-center text-gray-400">
          You voted to banish{' '}
          <span className="text-red-400 font-medium">
            {targets.find((t) => t.id === selectedTarget)?.name}
          </span>
        </p>
      )}
    </div>
  );
}
