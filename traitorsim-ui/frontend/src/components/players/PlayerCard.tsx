/**
 * PlayerCard - Individual player display with personality radar and behavioral stats
 *
 * Implements the "Poker Tracker HUD" pattern from UX research:
 * - OCEAN personality radar chart
 * - Behavioral statistics (votes with majority, mission success, etc.)
 * - Player type classification
 * - Suspicion indicators
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Player, GameEvent, getArchetypeColor, getAverageSuspicion, TrustMatrix } from '../../types';
import {
  calculateBehavioralStats,
  classifyPlayerType,
  getPlayerTypeColor,
  BehavioralStats,
} from '../../utils/behavioralStats';
import { usePOVVisibility } from '../../hooks';

interface PlayerCardProps {
  player: Player;
  trustMatrix: TrustMatrix;
  isSelected: boolean;
  showRole: boolean;
  onClick: () => void;
  // Optional: for full behavioral stats calculation
  events?: GameEvent[];
  players?: Record<string, Player>;
  compact?: boolean; // For smaller display in lists
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Mini radar chart for OCEAN personality traits
 */
function OceanRadar({ personality }: { personality: Player['personality'] }) {
  if (!personality) return null;

  const traits = [
    { key: 'O', value: personality.openness, label: 'Openness' },
    { key: 'C', value: personality.conscientiousness, label: 'Conscientiousness' },
    { key: 'E', value: personality.extraversion, label: 'Extraversion' },
    { key: 'A', value: personality.agreeableness, label: 'Agreeableness' },
    { key: 'N', value: personality.neuroticism, label: 'Neuroticism' },
  ];

  const size = 60;
  const center = size / 2;
  const radius = size / 2 - 8;

  // Calculate polygon points
  const points = traits.map((trait, i) => {
    const angle = (i * 2 * Math.PI) / traits.length - Math.PI / 2;
    const r = radius * trait.value;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  });

  const polygonPoints = points.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <svg width={size} height={size} className="opacity-80">
      {/* Background pentagons */}
      {[0.2, 0.4, 0.6, 0.8, 1.0].map((level, i) => (
        <polygon
          key={i}
          points={traits.map((_, j) => {
            const angle = (j * 2 * Math.PI) / traits.length - Math.PI / 2;
            const r = radius * level;
            return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
          }).join(' ')}
          fill="none"
          stroke="#4b5563"
          strokeWidth="0.5"
        />
      ))}

      {/* Axes */}
      {traits.map((_, i) => {
        const angle = (i * 2 * Math.PI) / traits.length - Math.PI / 2;
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={center + radius * Math.cos(angle)}
            y2={center + radius * Math.sin(angle)}
            stroke="#4b5563"
            strokeWidth="0.5"
          />
        );
      })}

      {/* Value polygon */}
      <polygon
        points={polygonPoints}
        fill="rgba(59, 130, 246, 0.3)"
        stroke="#3b82f6"
        strokeWidth="1.5"
      />

      {/* Labels */}
      {traits.map((trait, i) => {
        const angle = (i * 2 * Math.PI) / traits.length - Math.PI / 2;
        const labelRadius = radius + 6;
        return (
          <text
            key={trait.key}
            x={center + labelRadius * Math.cos(angle)}
            y={center + labelRadius * Math.sin(angle)}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-gray-400 text-[8px]"
          >
            {trait.key}
          </text>
        );
      })}
    </svg>
  );
}

/**
 * Suspicion meter with animated fill
 */
function SuspicionMeter({ suspicion }: { suspicion: number }) {
  const percentage = suspicion * 100;
  const color = suspicion < 0.3 ? 'bg-green-500' : suspicion < 0.6 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <motion.div
        className={`h-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

/**
 * Single stat display with label and value
 */
function StatRow({
  label,
  value,
  suffix = '%',
  color = 'text-gray-300',
  icon,
}: {
  label: string;
  value: number | string;
  suffix?: string;
  color?: string;
  icon?: string;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-500 flex items-center gap-1">
        {icon && <span>{icon}</span>}
        {label}
      </span>
      <span className={color}>
        {typeof value === 'number' ? Math.round(value) : value}
        {typeof value === 'number' && suffix}
      </span>
    </div>
  );
}

/**
 * Behavioral stats section (poker tracker HUD style)
 */
function BehavioralStatsDisplay({ stats }: { stats: BehavioralStats }) {
  // Determine color based on value (higher = better for faithful)
  const getVoteColor = (value: number) => {
    if (value >= 70) return 'text-green-400';
    if (value >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getMissionColor = (value: number) => {
    if (value >= 80) return 'text-green-400';
    if (value >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="space-y-1.5 mt-2 pt-2 border-t border-gray-700/50">
      <StatRow
        label="Votes w/ majority"
        value={stats.votesWithMajority}
        color={getVoteColor(stats.votesWithMajority)}
        icon="🗳️"
      />
      <StatRow
        label="Mission success"
        value={stats.missionSuccessRate}
        color={getMissionColor(stats.missionSuccessRate)}
        icon="🎯"
      />
      {stats.missionsParticipated > 0 && (
        <StatRow
          label="Avg performance"
          value={(stats.averagePerformanceScore * 100)}
          color={getMissionColor(stats.averagePerformanceScore * 100)}
          icon="📊"
        />
      )}
      {stats.averageBreakfastPosition !== null && (
        <StatRow
          label="Breakfast order"
          value={stats.averageBreakfastPosition.toFixed(1)}
          suffix=""
          color="text-amber-400"
          icon="☀️"
        />
      )}
      {stats.conversationsInitiated > 0 && (
        <StatRow
          label="Social connections"
          value={stats.uniqueConversationPartners}
          suffix=""
          color="text-blue-400"
          icon="💬"
        />
      )}
    </div>
  );
}

/**
 * Player type badge
 */
function PlayerTypeBadge({
  type,
  label,
  confidence,
}: {
  type: string;
  label: string;
  confidence: number;
}) {
  if (type === 'unknown' || confidence < 0.5) return null;

  const colorClass = getPlayerTypeColor(type as any);

  return (
    <span
      className={`px-2 py-0.5 rounded text-[10px] border ${colorClass}`}
      title={`${Math.round(confidence * 100)}% confidence`}
    >
      {label}
    </span>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function PlayerCard({
  player,
  trustMatrix,
  isSelected,
  showRole,
  onClick,
  events = [],
  players = {},
  compact = false,
}: PlayerCardProps) {
  const archetypeColor = getArchetypeColor(player.archetype_id || '');
  const avgSuspicion = getAverageSuspicion(trustMatrix, player.id);

  // POV-aware visibility - combines prop override with viewing mode
  const { shouldShowRole, shouldRevealTraitor } = usePOVVisibility(players);
  const displayRole = showRole || shouldShowRole(player);
  const isRevealedTraitor = shouldRevealTraitor(player);

  // Calculate behavioral stats (memoized for performance)
  const behavioralStats = useMemo(() => {
    if (events.length === 0 || Object.keys(players).length === 0) {
      return null;
    }
    return calculateBehavioralStats(player, events, players, trustMatrix);
  }, [player, events, players, trustMatrix]);

  // Classify player type
  const playerType = useMemo(() => {
    if (!behavioralStats) return null;
    return classifyPlayerType(player, behavioralStats);
  }, [player, behavioralStats]);

  // Status badge
  const statusBadge = player.alive ? (
    <span className="status-alive px-2 py-0.5 rounded text-xs">Alive</span>
  ) : player.elimination_type === 'MURDERED' ? (
    <span className="status-murdered px-2 py-0.5 rounded text-xs">Murdered</span>
  ) : (
    <span className="status-banished px-2 py-0.5 rounded text-xs">Banished</span>
  );

  // Role badge - uses POV-aware visibility
  const roleBadge = displayRole && (
    <span
      className={`px-2 py-0.5 rounded text-xs ${
        player.role === 'TRAITOR' ? 'role-traitor' : 'role-faithful'
      }`}
    >
      {player.role}
    </span>
  );

  return (
    <motion.div
      className={`player-card cursor-pointer ${
        !player.alive ? 'eliminated' : ''
      } ${isSelected ? 'selected' : ''} ${
        isRevealedTraitor ? 'ring-1 ring-red-500/50' : ''
      }`}
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      layout
    >
      {/* Header with archetype color accent */}
      <div
        className="h-1 rounded-t -mx-4 -mt-4 mb-3"
        style={{ backgroundColor: archetypeColor }}
      />

      <div className="flex justify-between items-start gap-3">
        {/* Left side: name, badges, and stats */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white truncate">{player.name}</h3>
          <p className="text-sm text-gray-400 truncate">{player.archetype_name || player.archetype_id}</p>

          {/* Badges row */}
          <div className="flex flex-wrap gap-1 mt-2">
            {statusBadge}
            {roleBadge}
            {playerType && (
              <PlayerTypeBadge
                type={playerType.type}
                label={playerType.label}
                confidence={playerType.confidence}
              />
            )}
          </div>

          {/* Suspicion meter */}
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Suspicion</span>
              <span>{(avgSuspicion * 100).toFixed(0)}%</span>
            </div>
            <SuspicionMeter suspicion={avgSuspicion} />
          </div>

          {/* Behavioral stats (if available and not compact) */}
          {!compact && behavioralStats && (
            <BehavioralStatsDisplay stats={behavioralStats} />
          )}
        </div>

        {/* Right side: OCEAN radar */}
        <div className="flex-shrink-0">
          <OceanRadar personality={player.personality} />
        </div>
      </div>

      {/* Elimination info */}
      {!player.alive && player.eliminated_day && (
        <p className="text-xs text-gray-500 mt-2">
          Day {player.eliminated_day}
          {behavioralStats?.wasMurdered && ' - Murdered by Traitors'}
          {behavioralStats?.wasBanished && ' - Banished by vote'}
        </p>
      )}

      {/* Power items indicators */}
      {(player.has_shield || player.has_dagger || behavioralStats?.hadShield || behavioralStats?.hadDagger) && (
        <div className="flex gap-1 mt-2">
          {(player.has_shield || behavioralStats?.hadShield) && (
            <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded" title="Has/Had Shield">
              🛡️
            </span>
          )}
          {(player.has_dagger || behavioralStats?.hadDagger) && (
            <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded" title="Has/Had Dagger">
              🗡️
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default PlayerCard;
