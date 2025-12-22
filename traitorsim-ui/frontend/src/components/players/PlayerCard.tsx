/**
 * PlayerCard - Individual player display with personality radar chart
 */

import { motion } from 'framer-motion';
import { Player, getArchetypeColor, getAverageSuspicion, TrustMatrix } from '../../types';

interface PlayerCardProps {
  player: Player;
  trustMatrix: TrustMatrix;
  isSelected: boolean;
  showRole: boolean;
  onClick: () => void;
}

// Mini radar chart for OCEAN traits
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

// Suspicion meter
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

export function PlayerCard({ player, trustMatrix, isSelected, showRole, onClick }: PlayerCardProps) {
  const archetypeColor = getArchetypeColor(player.archetype_id || '');
  const avgSuspicion = getAverageSuspicion(trustMatrix, player.id);

  // Status badge
  const statusBadge = player.alive ? (
    <span className="status-alive px-2 py-0.5 rounded text-xs">Alive</span>
  ) : player.elimination_type === 'MURDERED' ? (
    <span className="status-murdered px-2 py-0.5 rounded text-xs">Murdered</span>
  ) : (
    <span className="status-banished px-2 py-0.5 rounded text-xs">Banished</span>
  );

  // Role badge
  const roleBadge = showRole && (
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
      } ${isSelected ? 'selected' : ''}`}
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
        {/* Left side: name and badges */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white truncate">{player.name}</h3>
          <p className="text-sm text-gray-400 truncate">{player.archetype_name || player.archetype_id}</p>

          <div className="flex flex-wrap gap-1 mt-2">
            {statusBadge}
            {roleBadge}
          </div>

          {/* Suspicion meter */}
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Suspicion</span>
              <span>{(avgSuspicion * 100).toFixed(0)}%</span>
            </div>
            <SuspicionMeter suspicion={avgSuspicion} />
          </div>
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
        </p>
      )}
    </motion.div>
  );
}

export default PlayerCard;
