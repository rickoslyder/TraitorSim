/**
 * BreakfastOrderChart - Visualize breakfast entry order patterns
 *
 * A key "tell" in The Traitors: Traitors often enter last because
 * they know who was murdered. This chart tracks entry order by day
 * and highlights suspicious patterns.
 *
 * Features:
 * - Line chart showing entry position by day for each player
 * - Highlight players who consistently enter last
 * - Correlation with murder victims
 * - Click to highlight player across all views
 */

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Player, GameEvent } from '../../types';
import { useGameStore } from '../../stores/gameStore';
import { usePOVVisibility } from '../../hooks';

interface BreakfastOrderChartProps {
  players: Record<string, Player>;
  events: GameEvent[];
}

interface BreakfastEntry {
  day: number;
  order: string[]; // Player IDs in entry order
  victim: string | null;
  lastToArrive: string | null;
}

interface PlayerBreakfastStats {
  playerId: string;
  playerName: string;
  role: string;
  positions: { day: number; position: number }[];
  averagePosition: number;
  lastEntries: number; // How many times entered last
  timesAfterMurder: number; // How many times entered last on murder days
  suspicionScore: number; // Computed suspicion based on breakfast patterns
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Extract breakfast order data from events
 */
function extractBreakfastData(events: GameEvent[]): BreakfastEntry[] {
  const breakfastEntries: BreakfastEntry[] = [];
  const days = new Set(events.map(e => e.day));

  for (const day of days) {
    // Look for BREAKFAST_ORDER events
    const breakfastEvent = events.find(
      e => e.type === 'BREAKFAST_ORDER' && e.day === day
    );

    // Look for murder victim on this day
    const murderEvent = events.find(
      e => (e.type === 'MURDER_SUCCESS' || e.type === 'MURDER') && e.day === day
    );

    if (breakfastEvent && breakfastEvent.data?.order) {
      breakfastEntries.push({
        day,
        order: breakfastEvent.data.order as string[],
        victim: breakfastEvent.data.victim_revealed as string | null || murderEvent?.target || null,
        lastToArrive: breakfastEvent.data.last_to_arrive as string | null,
      });
    }
  }

  return breakfastEntries.sort((a, b) => a.day - b.day);
}

/**
 * Calculate per-player breakfast statistics
 */
function calculatePlayerStats(
  breakfastData: BreakfastEntry[],
  players: Record<string, Player>
): PlayerBreakfastStats[] {
  const stats: Record<string, PlayerBreakfastStats> = {};

  // Initialize stats for all players
  for (const [id, player] of Object.entries(players)) {
    stats[id] = {
      playerId: id,
      playerName: player.name,
      role: player.role,
      positions: [],
      averagePosition: 0,
      lastEntries: 0,
      timesAfterMurder: 0,
      suspicionScore: 0,
    };
  }

  // Populate positions from breakfast data
  for (const entry of breakfastData) {
    const totalPlayers = entry.order.length;

    entry.order.forEach((playerId, index) => {
      if (stats[playerId]) {
        const position = index + 1; // 1-indexed
        stats[playerId].positions.push({ day: entry.day, position });

        // Track last entries
        if (position === totalPlayers) {
          stats[playerId].lastEntries++;
          if (entry.victim) {
            stats[playerId].timesAfterMurder++;
          }
        }
      }
    });
  }

  // Calculate averages and suspicion scores
  for (const stat of Object.values(stats)) {
    if (stat.positions.length > 0) {
      stat.averagePosition = stat.positions.reduce((sum, p) => sum + p.position, 0) / stat.positions.length;

      // Suspicion score: weighted by last entries and murder correlation
      const lastEntryRate = stat.lastEntries / stat.positions.length;
      const murderCorrelation = stat.positions.length > 0
        ? stat.timesAfterMurder / Math.max(1, stat.lastEntries)
        : 0;

      stat.suspicionScore = (lastEntryRate * 0.6) + (murderCorrelation * 0.4);
    }
  }

  return Object.values(stats)
    .filter(s => s.positions.length > 0)
    .sort((a, b) => b.suspicionScore - a.suspicionScore);
}

/**
 * Get color based on suspicion level
 */
function getSuspicionColor(score: number): string {
  if (score > 0.7) return '#ef4444'; // Red - very suspicious
  if (score > 0.5) return '#f97316'; // Orange - suspicious
  if (score > 0.3) return '#eab308'; // Yellow - notable
  return '#22c55e'; // Green - normal
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Mini sparkline showing position over time
 */
function PositionSparkline({
  positions,
  maxDays,
  maxPlayers,
}: {
  positions: { day: number; position: number }[];
  maxDays: number;
  maxPlayers: number;
}) {
  const width = 120;
  const height = 30;
  const padding = 2;

  if (positions.length === 0) return null;

  const xScale = (day: number) => padding + ((day - 1) / Math.max(1, maxDays - 1)) * (width - 2 * padding);
  const yScale = (pos: number) => padding + ((pos - 1) / Math.max(1, maxPlayers - 1)) * (height - 2 * padding);

  const pathData = positions
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.day)} ${yScale(p.position)}`)
    .join(' ');

  return (
    <svg width={width} height={height} className="flex-shrink-0">
      {/* Grid lines */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1" />

      {/* Position line */}
      <path
        d={pathData}
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Points */}
      {positions.map((p, i) => (
        <circle
          key={i}
          cx={xScale(p.day)}
          cy={yScale(p.position)}
          r="3"
          fill={p.position === maxPlayers ? '#ef4444' : '#3b82f6'}
        />
      ))}
    </svg>
  );
}

/**
 * Player row in the breakfast order table
 */
function PlayerBreakfastRow({
  stat,
  maxDays,
  maxPlayers,
  isHighlighted,
  onClick,
  showRole,
}: {
  stat: PlayerBreakfastStats;
  maxDays: number;
  maxPlayers: number;
  isHighlighted: boolean;
  onClick: () => void;
  showRole: boolean;
}) {
  return (
    <motion.tr
      className={`border-b border-gray-700 cursor-pointer transition-colors ${
        isHighlighted ? 'bg-blue-900/30' : 'hover:bg-gray-800'
      }`}
      onClick={onClick}
      whileHover={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
    >
      {/* Player name */}
      <td className="py-2 px-3">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{stat.playerName}</span>
          {showRole && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              stat.role === 'TRAITOR' ? 'bg-red-600 text-white' : 'bg-blue-600 text-white'
            }`}>
              {stat.role === 'TRAITOR' ? 'T' : 'F'}
            </span>
          )}
        </div>
      </td>

      {/* Sparkline */}
      <td className="py-2 px-3">
        <PositionSparkline
          positions={stat.positions}
          maxDays={maxDays}
          maxPlayers={maxPlayers}
        />
      </td>

      {/* Average position */}
      <td className="py-2 px-3 text-center text-gray-300">
        {stat.averagePosition.toFixed(1)}
      </td>

      {/* Last entries */}
      <td className="py-2 px-3 text-center">
        <span className={stat.lastEntries > 2 ? 'text-orange-400 font-bold' : 'text-gray-400'}>
          {stat.lastEntries}
        </span>
      </td>

      {/* Murder correlation */}
      <td className="py-2 px-3 text-center">
        <span className={stat.timesAfterMurder > 0 ? 'text-red-400 font-bold' : 'text-gray-500'}>
          {stat.timesAfterMurder}
        </span>
      </td>

      {/* Suspicion indicator */}
      <td className="py-2 px-3">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: getSuspicionColor(stat.suspicionScore) }}
          />
          <span className="text-xs text-gray-400">
            {(stat.suspicionScore * 100).toFixed(0)}%
          </span>
        </div>
      </td>
    </motion.tr>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function BreakfastOrderChart({ players, events }: BreakfastOrderChartProps) {
  const { selectedPlayerId, selectPlayer } = useGameStore();
  const [sortBy, setSortBy] = useState<'suspicion' | 'average' | 'last'>('suspicion');

  // POV-aware role visibility
  const { shouldShowRole } = usePOVVisibility(players);

  // Extract and process breakfast data
  const breakfastData = useMemo(() => extractBreakfastData(events), [events]);
  const playerStats = useMemo(
    () => calculatePlayerStats(breakfastData, players),
    [breakfastData, players]
  );

  // Sort players
  const sortedStats = useMemo(() => {
    const sorted = [...playerStats];
    switch (sortBy) {
      case 'suspicion':
        return sorted.sort((a, b) => b.suspicionScore - a.suspicionScore);
      case 'average':
        return sorted.sort((a, b) => b.averagePosition - a.averagePosition);
      case 'last':
        return sorted.sort((a, b) => b.lastEntries - a.lastEntries);
      default:
        return sorted;
    }
  }, [playerStats, sortBy]);

  // Calculate max values for scaling
  const maxDays = breakfastData.length > 0
    ? Math.max(...breakfastData.map(b => b.day))
    : 1;
  const maxPlayers = breakfastData.length > 0
    ? Math.max(...breakfastData.map(b => b.order.length))
    : Object.keys(players).length;

  // Find most suspicious players
  const mostSuspicious = playerStats
    .filter(s => s.suspicionScore > 0.5)
    .slice(0, 3);

  if (breakfastData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <span className="text-4xl mb-4">🍳</span>
        <p>No breakfast order data available</p>
        <p className="text-sm text-gray-500 mt-2">
          Breakfast order events are not exported in this game's data
        </p>
      </div>
    );
  }

  return (
    <div className="breakfast-order-chart space-y-4">
      {/* Header with insights */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>🍳</span>
            Breakfast Order Analysis
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            Track who enters breakfast last - a key "tell" for Traitor behavior
          </p>
        </div>

        {/* Quick insights */}
        <AnimatePresence>
          {mostSuspicious.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-2"
            >
              <div className="text-xs text-red-400 font-medium mb-1">Suspicious Patterns</div>
              <div className="flex gap-2">
                {mostSuspicious.map(s => (
                  <button
                    key={s.playerId}
                    onClick={() => selectPlayer(s.playerId)}
                    className="text-sm text-white hover:text-red-300 transition-colors"
                  >
                    {s.playerName.split(' ')[0]}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-400">Sort by:</span>
        <div className="flex rounded-lg bg-gray-800 p-1">
          {[
            { key: 'suspicion', label: 'Suspicion' },
            { key: 'average', label: 'Avg Position' },
            { key: 'last', label: 'Last Entries' },
          ].map(option => (
            <button
              key={option.key}
              onClick={() => setSortBy(option.key as typeof sortBy)}
              className={`px-3 py-1 rounded-md transition-colors ${
                sortBy === option.key
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Data table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-700">
              <th className="py-2 px-3 font-medium">Player</th>
              <th className="py-2 px-3 font-medium">Entry Position Over Time</th>
              <th className="py-2 px-3 font-medium text-center">Avg Pos</th>
              <th className="py-2 px-3 font-medium text-center">Last×</th>
              <th className="py-2 px-3 font-medium text-center">Murder×</th>
              <th className="py-2 px-3 font-medium">Suspicion</th>
            </tr>
          </thead>
          <tbody>
            {sortedStats.map(stat => {
              const player = players[stat.playerId];
              return (
                <PlayerBreakfastRow
                  key={stat.playerId}
                  stat={stat}
                  maxDays={maxDays}
                  maxPlayers={maxPlayers}
                  isHighlighted={selectedPlayerId === stat.playerId}
                  onClick={() => selectPlayer(stat.playerId === selectedPlayerId ? null : stat.playerId)}
                  showRole={player ? shouldShowRole(player) : false}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500 border-t border-gray-700 pt-3">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span>Normal pattern</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          <span>Notable (30-50%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-orange-500" />
          <span>Suspicious (50-70%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span>Very suspicious (70%+)</span>
        </div>
        <div className="flex items-center gap-1 ml-auto">
          <span className="text-blue-400">●</span>
          <span>Entry point</span>
          <span className="text-red-400 ml-2">●</span>
          <span>Entered last</span>
        </div>
      </div>
    </div>
  );
}

export default BreakfastOrderChart;
