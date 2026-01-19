/**
 * Player slot component for the lobby view.
 * Displays player information or empty slot status.
 */

import type { LobbySlot } from '../../types/lobby';

interface PlayerSlotProps {
  slot: LobbySlot;
  isCurrentPlayer: boolean;
  canKick: boolean;
  onKick?: () => void;
}

export function PlayerSlot({
  slot,
  isCurrentPlayer,
  canKick,
  onKick,
}: PlayerSlotProps) {
  const isOccupied = slot.player_type !== 'empty' && slot.player_id;
  const isHuman = slot.player_type === 'human';
  const isAI = slot.player_type === 'ai';

  return (
    <div
      className={`
        relative flex items-center gap-3 p-4 rounded-lg border-2 transition-colors
        ${isOccupied ? 'bg-gray-800 border-gray-600' : 'bg-gray-900/50 border-dashed border-gray-700'}
        ${isCurrentPlayer ? 'ring-2 ring-blue-500' : ''}
        ${slot.is_ready ? 'border-green-500' : ''}
      `}
    >
      {/* Slot index */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm font-medium text-gray-300">
        {slot.slot_index + 1}
      </div>

      {/* Player info or empty state */}
      <div className="flex-1 min-w-0">
        {isOccupied ? (
          <>
            <div className="flex items-center gap-2">
              <span className="font-medium text-white truncate">
                {slot.display_name}
              </span>
              {slot.is_host && (
                <span className="px-2 py-0.5 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded">
                  Host
                </span>
              )}
              {isAI && (
                <span className="px-2 py-0.5 text-xs font-medium bg-purple-500/20 text-purple-400 rounded">
                  AI
                </span>
              )}
              {isCurrentPlayer && (
                <span className="px-2 py-0.5 text-xs font-medium bg-blue-500/20 text-blue-400 rounded">
                  You
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {/* Connection status */}
              <div
                className={`w-2 h-2 rounded-full ${
                  slot.is_connected ? 'bg-green-500' : 'bg-gray-500'
                }`}
                title={slot.is_connected ? 'Connected' : 'Disconnected'}
              />
              <span className="text-xs text-gray-400">
                {slot.is_connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </>
        ) : (
          <span className="text-gray-500 italic">Empty slot</span>
        )}
      </div>

      {/* Ready indicator */}
      {isOccupied && isHuman && (
        <div className="flex-shrink-0">
          {slot.is_ready ? (
            <span className="text-green-400 text-sm font-medium">Ready</span>
          ) : (
            <span className="text-gray-500 text-sm">Not ready</span>
          )}
        </div>
      )}

      {/* Kick button */}
      {canKick && !isCurrentPlayer && (
        <button
          onClick={onKick}
          className="flex-shrink-0 p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors"
          title="Kick player"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
