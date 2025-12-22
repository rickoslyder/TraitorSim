/**
 * VotingHeatmap - Matrix visualization of voting patterns
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Player, GameEvent } from '../../types';
import { useGameStore } from '../../stores/gameStore';

interface VotingHeatmapProps {
  players: Record<string, Player>;
  events: GameEvent[];
  maxDay?: number;
}

export function VotingHeatmap({ players, events, maxDay }: VotingHeatmapProps) {
  const { selectPlayer, selectedPlayerId, currentDay } = useGameStore();
  const effectiveMaxDay = maxDay ?? currentDay;

  // Build vote matrix
  const { voteMatrix, maxVotes, playerList } = useMemo(() => {
    const matrix: Record<string, Record<string, number>> = {};
    let maxVotes = 0;

    // Filter to only vote events up to current day
    const voteEvents = events.filter(
      e => e.type === 'VOTE' && e.day <= effectiveMaxDay
    );

    // Count votes
    for (const event of voteEvents) {
      const voter = event.actor;
      const target = event.target;

      if (!voter || !target) continue;

      if (!matrix[voter]) matrix[voter] = {};
      matrix[voter][target] = (matrix[voter][target] || 0) + 1;
      maxVotes = Math.max(maxVotes, matrix[voter][target]);
    }

    // Get sorted player list (alive first, then alphabetical)
    const playerList = Object.values(players)
      .sort((a, b) => {
        if (a.alive !== b.alive) return a.alive ? -1 : 1;
        return a.name.localeCompare(b.name);
      })
      .map(p => ({ id: p.id, name: p.name, alive: p.alive, role: p.role }));

    return { voteMatrix: matrix, maxVotes, playerList };
  }, [players, events, effectiveMaxDay]);

  // Get cell color based on vote count
  const getCellColor = (count: number): string => {
    if (count === 0) return 'bg-gray-800';
    const intensity = count / maxVotes;
    if (intensity < 0.33) return 'bg-purple-900';
    if (intensity < 0.66) return 'bg-purple-700';
    return 'bg-purple-500';
  };

  if (playerList.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        No voting data available
      </div>
    );
  }

  return (
    <div className="overflow-auto">
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-gray-900 p-2 text-left text-gray-400">
              Voter \ Target
            </th>
            {playerList.map(player => (
              <th
                key={player.id}
                className={`p-2 text-center cursor-pointer transition-colors ${
                  selectedPlayerId === player.id
                    ? 'bg-blue-900'
                    : 'hover:bg-gray-700'
                } ${!player.alive ? 'text-gray-500' : 'text-gray-300'}`}
                onClick={() => selectPlayer(player.id)}
                title={player.name}
              >
                <div className="w-16 truncate transform -rotate-45 origin-left translate-x-4">
                  {player.name.split(' ')[0]}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {playerList.map(voter => (
            <tr key={voter.id}>
              <td
                className={`sticky left-0 z-10 bg-gray-900 p-2 cursor-pointer transition-colors ${
                  selectedPlayerId === voter.id
                    ? 'bg-blue-900'
                    : 'hover:bg-gray-700'
                } ${!voter.alive ? 'text-gray-500' : 'text-gray-300'}`}
                onClick={() => selectPlayer(voter.id)}
              >
                {voter.name}
              </td>
              {playerList.map(target => {
                const count = voteMatrix[voter.id]?.[target.id] || 0;
                const isHighlighted =
                  selectedPlayerId === voter.id || selectedPlayerId === target.id;

                return (
                  <td
                    key={target.id}
                    className={`p-0 ${isHighlighted ? 'ring-1 ring-blue-400' : ''}`}
                  >
                    <motion.div
                      className={`w-8 h-8 flex items-center justify-center ${getCellColor(count)} ${
                        voter.id === target.id ? 'bg-gray-900' : ''
                      }`}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.01 }}
                      title={`${voter.name} voted for ${target.name}: ${count} times`}
                    >
                      {count > 0 && voter.id !== target.id && (
                        <span className="text-white font-medium">{count}</span>
                      )}
                    </motion.div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
        <span>Votes:</span>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-gray-800 rounded" />
          <span>0</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-purple-900 rounded" />
          <span>Low</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-purple-700 rounded" />
          <span>Medium</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-purple-500 rounded" />
          <span>High</span>
        </div>
      </div>
    </div>
  );
}

export default VotingHeatmap;
