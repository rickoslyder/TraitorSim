/**
 * MissionBreakdown - Detailed mission performance analysis
 *
 * Analyze mission outcomes to distinguish sabotage from clumsiness.
 * Shows per-player skill check results and detects suspicious patterns.
 *
 * Features:
 * - Mission success/failure breakdown by day
 * - Per-player performance scores with probability analysis
 * - Sabotage detection (failed despite high stats)
 * - Shield/Dagger winner tracking
 * - Mission participation patterns
 */

import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Player } from '../../types/player';
import type { GameEvent } from '../../types/events';
import { useGameStore } from '../../stores/gameStore';
import { usePOVVisibility } from '../../hooks/usePOVVisibility';

interface MissionBreakdownProps {
  players: Record<string, Player>;
  events: GameEvent[];
}

interface MissionData {
  day: number;
  missionName: string;
  success: boolean;
  earnings: number;
  participants: string[];
  performanceScores: Record<string, number>;
  shieldWinner: string | null;
  daggerWinner: string | null;
  saboteur: string | null;
}

interface PlayerMissionStats {
  playerId: string;
  playerName: string;
  role: string;
  missionsParticipated: number;
  averagePerformance: number;
  totalEarnings: number;
  failedMissions: number;
  suspiciousFailures: number; // Failed despite high stats
  shieldsWon: number;
  daggersWon: number;
  expectedPerformance: number; // Based on stats
  performanceGap: number; // Expected - Actual (positive = underperforming)
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Extract mission data from events
 */
function extractMissionData(events: GameEvent[]): MissionData[] {
  const missions: MissionData[] = [];

  const missionEvents = events.filter(
    e => e.type === 'MISSION_COMPLETE' || e.type === 'MISSION_SUCCESS' || e.type === 'MISSION_FAIL'
  );

  for (const event of missionEvents) {
    const data = event.data || {};

    missions.push({
      day: event.day,
      missionName: (data.mission_name as string) || `Day ${event.day} Mission`,
      success: event.type === 'MISSION_SUCCESS' || (data.success as boolean) === true,
      earnings: (data.earnings as number) || 0,
      participants: (data.participants as string[]) || [],
      performanceScores: (data.performance_scores as Record<string, number>) || {},
      shieldWinner: (data.shield_winner as string) || null,
      daggerWinner: (data.dagger_winner as string) || null,
      saboteur: (data.saboteur as string) || null,
    });
  }

  return missions.sort((a, b) => a.day - b.day);
}

/**
 * Calculate per-player mission statistics
 */
function calculatePlayerMissionStats(
  missions: MissionData[],
  players: Record<string, Player>
): PlayerMissionStats[] {
  const stats: Record<string, PlayerMissionStats> = {};

  // Initialize stats for all players
  for (const [id, player] of Object.entries(players)) {
    const expectedPerf = player.stats
      ? (player.stats.intellect + player.stats.dexterity + player.stats.composure) / 3
      : 0.5;

    stats[id] = {
      playerId: id,
      playerName: player.name,
      role: player.role,
      missionsParticipated: 0,
      averagePerformance: 0,
      totalEarnings: 0,
      failedMissions: 0,
      suspiciousFailures: 0,
      shieldsWon: 0,
      daggersWon: 0,
      expectedPerformance: expectedPerf,
      performanceGap: 0,
    };
  }

  // Aggregate mission data
  const performanceSums: Record<string, number> = {};
  const performanceCounts: Record<string, number> = {};

  for (const mission of missions) {
    const earningsPerPlayer = mission.participants.length > 0
      ? mission.earnings / mission.participants.length
      : 0;

    for (const playerId of mission.participants) {
      if (stats[playerId]) {
        stats[playerId].missionsParticipated++;
        stats[playerId].totalEarnings += earningsPerPlayer;

        if (!mission.success) {
          stats[playerId].failedMissions++;

          // Check if this is a suspicious failure (high stats but failed)
          const player = players[playerId];
          if (player && player.stats) {
            const avgStat = (player.stats.intellect + player.stats.dexterity + player.stats.composure) / 3;
            if (avgStat > 0.6 && mission.performanceScores[playerId] < 0.4) {
              stats[playerId].suspiciousFailures++;
            }
          }
        }

        // Track performance scores
        if (mission.performanceScores[playerId] !== undefined) {
          performanceSums[playerId] = (performanceSums[playerId] || 0) + mission.performanceScores[playerId];
          performanceCounts[playerId] = (performanceCounts[playerId] || 0) + 1;
        }
      }
    }

    // Track shield/dagger winners
    if (mission.shieldWinner && stats[mission.shieldWinner]) {
      stats[mission.shieldWinner].shieldsWon++;
    }
    if (mission.daggerWinner && stats[mission.daggerWinner]) {
      stats[mission.daggerWinner].daggersWon++;
    }
  }

  // Calculate averages and gaps
  for (const [id, stat] of Object.entries(stats)) {
    if (performanceCounts[id] > 0) {
      stat.averagePerformance = performanceSums[id] / performanceCounts[id];
      stat.performanceGap = stat.expectedPerformance - stat.averagePerformance;
    }
  }

  return Object.values(stats)
    .filter(s => s.missionsParticipated > 0)
    .sort((a, b) => b.performanceGap - a.performanceGap); // Most underperforming first
}

/**
 * Get performance bar color
 */
function getPerformanceColor(performance: number): string {
  if (performance >= 0.8) return '#22c55e'; // Green
  if (performance >= 0.6) return '#84cc16'; // Light green
  if (performance >= 0.4) return '#eab308'; // Yellow
  if (performance >= 0.2) return '#f97316'; // Orange
  return '#ef4444'; // Red
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Mission card showing single mission result
 */
function MissionCard({
  mission,
  players,
  onClick,
}: {
  mission: MissionData;
  players: Record<string, Player>;
  onClick?: () => void;
}) {
  const topPerformers = Object.entries(mission.performanceScores)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);

  return (
    <motion.div
      className={`p-4 rounded-lg border cursor-pointer transition-colors ${
        mission.success
          ? 'bg-green-900/20 border-green-700 hover:bg-green-900/30'
          : 'bg-red-900/20 border-red-700 hover:bg-red-900/30'
      }`}
      onClick={onClick}
      onKeyDown={(e) => onClick && e.key === 'Enter' && onClick()}
      tabIndex={0}
      role="button"
      aria-label={`Mission ${mission.missionName} - ${mission.success ? 'Success' : 'Failed'}`}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="text-xs text-gray-400">Day {mission.day}</div>
          <div className="font-medium text-white">{mission.missionName}</div>
        </div>
        <div className={`text-2xl ${mission.success ? 'text-green-400' : 'text-red-400'}`}>
          {mission.success ? '✓' : '✗'}
        </div>
      </div>

      {mission.earnings > 0 && (
        <div className="text-sm text-green-400 mb-2">
          +£{new Intl.NumberFormat().format(mission.earnings)}
        </div>
      )}

      {/* Top performers */}
      {topPerformers.length > 0 && (
        <div className="mt-2 space-y-1">
          {topPerformers.map(([playerId, score]) => (
            <div key={playerId} className="flex items-center gap-2 text-xs">
              <div className="w-20 truncate text-gray-400">
                {players[playerId]?.name.split(' ')[0] || playerId}
              </div>
              <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: getPerformanceColor(score) }}
                  initial={{ width: 0 }}
                  animate={{ width: `${score * 100}%` }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                />
              </div>
              <div className="w-8 text-right text-gray-400">
                {(score * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Awards */}
      <div className="flex gap-2 mt-2">
        {mission.shieldWinner && (
          <span className="text-xs bg-yellow-600/30 text-yellow-300 px-2 py-0.5 rounded">
            🛡️ {players[mission.shieldWinner]?.name.split(' ')[0]}
          </span>
        )}
        {mission.daggerWinner && (
          <span className="text-xs bg-red-600/30 text-red-300 px-2 py-0.5 rounded">
            🗡️ {players[mission.daggerWinner]?.name.split(' ')[0]}
          </span>
        )}
      </div>
    </motion.div>
  );
}

/**
 * Player performance row
 */
function PlayerPerformanceRow({
  stat,
  isHighlighted,
  onClick,
  showRole,
}: {
  stat: PlayerMissionStats;
  isHighlighted: boolean;
  onClick: () => void;
  showRole: boolean;
}) {
  const gapColor = stat.performanceGap > 0.2
    ? 'text-red-400'
    : stat.performanceGap > 0.1
    ? 'text-orange-400'
    : stat.performanceGap < -0.1
    ? 'text-green-400'
    : 'text-gray-400';

  return (
    <motion.tr
      className={`border-b border-gray-700 cursor-pointer transition-colors ${
        isHighlighted ? 'bg-blue-900/30' : 'hover:bg-gray-800'
      }`}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      tabIndex={0}
      role="button"
      style={{ contentVisibility: 'auto', containIntrinsicSize: '0 48px' }}
    >
      <td className="py-2 px-3">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{stat.playerName}</span>
          {showRole && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              stat.role === 'TRAITOR' ? 'bg-red-600' : 'bg-blue-600'
            }`}>
              {stat.role === 'TRAITOR' ? 'T' : 'F'}
            </span>
          )}
        </div>
      </td>
      <td className="py-2 px-3 text-center text-gray-300">
        {stat.missionsParticipated}
      </td>
      <td className="py-2 px-3">
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${stat.averagePerformance * 100}%`,
                backgroundColor: getPerformanceColor(stat.averagePerformance),
              }}
            />
          </div>
          <span className="text-xs text-gray-400">
            {(stat.averagePerformance * 100).toFixed(0)}%
          </span>
        </div>
      </td>
      <td className="py-2 px-3 text-center">
        <span className={gapColor}>
          {stat.performanceGap > 0 ? '+' : ''}{(stat.performanceGap * 100).toFixed(0)}%
        </span>
      </td>
      <td className="py-2 px-3 text-center">
        {stat.suspiciousFailures > 0 ? (
          <span className="text-red-400 font-bold">{stat.suspiciousFailures}</span>
        ) : (
          <span className="text-gray-500">0</span>
        )}
      </td>
      <td className="py-2 px-3 text-center text-green-400">
        £{new Intl.NumberFormat().format(stat.totalEarnings)}
      </td>
      <td className="py-2 px-3 text-center">
        {stat.shieldsWon > 0 && <span className="mr-1">🛡️×{stat.shieldsWon}</span>}
        {stat.daggersWon > 0 && <span>🗡️×{stat.daggersWon}</span>}
        {stat.shieldsWon === 0 && stat.daggersWon === 0 && <span className="text-gray-500">-</span>}
      </td>
    </motion.tr>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function MissionBreakdown({ players, events }: MissionBreakdownProps) {
  const { selectedPlayerId, selectPlayer, currentDay } = useGameStore();
  const [view, setView] = useState<'timeline' | 'players'>('timeline');

  // POV-aware role visibility
  const { shouldShowRole } = usePOVVisibility(players);

  // Extract and process mission data
  const missions = useMemo(() => extractMissionData(events), [events]);
  const playerStats = useMemo(
    () => calculatePlayerMissionStats(missions, players),
    [missions, players]
  );

  // Summary stats
  const summary = useMemo(() => {
    const successCount = missions.filter(m => m.success).length;
    const totalEarnings = missions.reduce((sum, m) => sum + m.earnings, 0);
    const suspiciousPlayers = playerStats.filter(s => s.suspiciousFailures > 0);

    return {
      total: missions.length,
      successes: successCount,
      failures: missions.length - successCount,
      successRate: missions.length > 0 ? successCount / missions.length : 0,
      totalEarnings,
      suspiciousPlayers,
    };
  }, [missions, playerStats]);

  // Filter missions by current day if in timeline view
  const displayMissions = view === 'timeline'
    ? missions.filter(m => m.day <= currentDay)
    : missions;

  if (missions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <span className="text-4xl mb-4">🎯</span>
        <p>No mission data available</p>
        <p className="text-sm text-gray-500 mt-2">
          Mission events are not exported in this game's data
        </p>
      </div>
    );
  }

  return (
    <div className="mission-breakdown space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>🎯</span>
            Mission Performance Analysis
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            Analyze mission outcomes to detect sabotage vs. clumsiness
          </p>
        </div>

        {/* View toggle */}
        <div className="flex rounded-lg bg-gray-800 p-1">
          {[
            { key: 'timeline', label: 'Timeline' },
            { key: 'players', label: 'By Player' },
          ].map(option => (
            <button
              key={option.key}
              onClick={() => setView(option.key as typeof view)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                view === option.key
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              aria-label={`View missions ${option.label.toLowerCase()}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-400">Total Missions</div>
          <div className="text-2xl font-bold text-white">{summary.total}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-400">Success Rate</div>
          <div className={`text-2xl font-bold ${
            summary.successRate >= 0.7 ? 'text-green-400' : summary.successRate >= 0.5 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {(summary.successRate * 100).toFixed(0)}%
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-400">Total Earnings</div>
          <div className="text-2xl font-bold text-green-400">
            £{new Intl.NumberFormat().format(summary.totalEarnings)}
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-400">Suspicious Players</div>
          <div className={`text-2xl font-bold ${
            summary.suspiciousPlayers.length > 0 ? 'text-red-400' : 'text-gray-400'
          }`}>
            {summary.suspiciousPlayers.length}
          </div>
        </div>
      </div>

      {/* Suspicious players alert */}
      <AnimatePresence>
        {summary.suspiciousPlayers.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-900/30 border border-red-700 rounded-lg p-4"
          >
            <div className="flex items-center gap-2 text-red-300 font-medium mb-2">
              <span>⚠️</span>
              Suspicious Performance Detected
            </div>
            <div className="text-sm text-gray-300">
              {summary.suspiciousPlayers.map(p => p.playerName).join(', ')} showed
              unexpectedly poor performance despite high stats - possible sabotage.
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content based on view */}
      {view === 'timeline' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayMissions.map((mission, idx) => (
            <MissionCard
              key={`${mission.day}-${idx}`}
              mission={mission}
              players={players}
            />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="py-2 px-3 font-medium">Player</th>
                <th className="py-2 px-3 font-medium text-center">Missions</th>
                <th className="py-2 px-3 font-medium">Performance</th>
                <th className="py-2 px-3 font-medium text-center">Gap</th>
                <th className="py-2 px-3 font-medium text-center">Sus×</th>
                <th className="py-2 px-3 font-medium text-center">Earnings</th>
                <th className="py-2 px-3 font-medium text-center">Awards</th>
              </tr>
            </thead>
            <tbody>
              {playerStats.map(stat => {
                const player = players[stat.playerId];
                return (
                  <PlayerPerformanceRow
                    key={stat.playerId}
                    stat={stat}
                    isHighlighted={selectedPlayerId === stat.playerId}
                    onClick={() => selectPlayer(stat.playerId === selectedPlayerId ? null : stat.playerId)}
                    showRole={player ? shouldShowRole(player) : false}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500 border-t border-gray-700 pt-3">
        <div>
          <strong>Gap:</strong> Expected - Actual performance (+ = underperforming)
        </div>
        <div>
          <strong>Sus×:</strong> Suspicious failures (failed despite high stats)
        </div>
      </div>
    </div>
  );
}

export default React.memo(MissionBreakdown);
