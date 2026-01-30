/**
 * Player list component for live game view.
 * Shows all players with their status (alive, role if visible).
 */

import type { LivePlayer } from '../../types/live';

interface PlayerListProps {
  players: LivePlayer[];
  myPlayerId: string;
  myRole?: 'FAITHFUL' | 'TRAITOR';
  fellowTraitors?: { id: string; name: string; alive: boolean }[];
}

export function PlayerList({
  players,
  myPlayerId,
  myRole,
  fellowTraitors = [],
}: PlayerListProps) {
  const traitorIds = new Set(fellowTraitors.map((t) => t.id));

  // Sort: alive first, then by name
  const sortedPlayers = [...players].sort((a, b) => {
    if (a.alive !== b.alive) return a.alive ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  const alivePlayers = sortedPlayers.filter((p) => p.alive);
  const eliminatedPlayers = sortedPlayers.filter((p) => !p.alive);

  return (
    <div className="bg-gray-800 rounded-xl p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
        Players ({alivePlayers.length} alive)
      </h3>

      {/* Alive players */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {alivePlayers.map((player) => (
          <PlayerCard
            key={player.id}
            player={player}
            isMe={player.id === myPlayerId}
            isKnownTraitor={myRole === 'TRAITOR' && traitorIds.has(player.id)}
            showRole={player.id === myPlayerId}
          />
        ))}
      </div>

      {/* Eliminated players */}
      {eliminatedPlayers.length > 0 && (
        <div className="pt-4 border-t border-gray-700">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Eliminated
          </h4>
          <div className="flex flex-wrap gap-2">
            {eliminatedPlayers.map((player) => (
              <div
                key={player.id}
                className="flex items-center gap-2 px-3 py-1.5 bg-gray-700/50 rounded-lg text-sm"
              >
                <span className="text-gray-500">💀</span>
                <span className="text-gray-400 line-through">{player.name}</span>
                <RoleBadge role={player.role} small />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface PlayerCardProps {
  player: LivePlayer;
  isMe: boolean;
  isKnownTraitor: boolean;
  showRole: boolean;
}

function PlayerCard({ player, isMe, isKnownTraitor, showRole }: PlayerCardProps) {
  return (
    <div
      className={`
        relative flex flex-col items-center gap-1 p-3 rounded-lg
        ${isMe ? 'bg-blue-500/20 ring-2 ring-blue-500' : 'bg-gray-700/50'}
        ${isKnownTraitor && !isMe ? 'ring-1 ring-red-500/50' : ''}
      `}
    >
      {/* Avatar */}
      <div
        className={`
          w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold
          ${isKnownTraitor ? 'bg-red-500/30 text-red-300' : 'bg-gray-600 text-gray-300'}
        `}
      >
        {player.name.charAt(0).toUpperCase()}
      </div>

      {/* Name */}
      <span className="text-sm font-medium text-white text-center truncate w-full">
        {player.name}
      </span>

      {/* Labels */}
      <div className="flex flex-wrap gap-1 justify-center">
        {isMe && (
          <span className="px-1.5 py-0.5 text-xs bg-blue-500/30 text-blue-300 rounded">
            You
          </span>
        )}
        {player.is_human === false && (
          <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded">
            AI
          </span>
        )}
        {(showRole || isKnownTraitor) && player.role && (
          <RoleBadge role={player.role} />
        )}
      </div>

      {/* Special items */}
      {(player.has_shield || player.has_dagger) && (
        <div className="absolute -top-1 -right-1 flex gap-0.5">
          {player.has_shield && <span title="Has Shield">🛡️</span>}
          {player.has_dagger && <span title="Has Dagger">🗡️</span>}
        </div>
      )}
    </div>
  );
}

function RoleBadge({
  role,
  small = false,
}: {
  role?: 'FAITHFUL' | 'TRAITOR';
  small?: boolean;
}) {
  if (!role) return null;

  const isTraitor = role === 'TRAITOR';
  const baseClasses = small ? 'px-1 py-0.5 text-xs' : 'px-1.5 py-0.5 text-xs';
  const colorClasses = isTraitor
    ? 'bg-red-500/30 text-red-300'
    : 'bg-blue-500/30 text-blue-300';

  return (
    <span className={`${baseClasses} ${colorClasses} rounded`}>
      {isTraitor ? '🗡️' : '💙'}
    </span>
  );
}
