/**
 * Phase indicator component.
 * Displays current day and phase with visual styling.
 */


interface PhaseIndicatorProps {
  day: number;
  phase: string;
  prizePot?: number;
  aliveCount?: number;
  totalPlayers?: number;
}

// Phase display configuration
const PHASE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  breakfast: { icon: '☀️', color: 'text-yellow-400', label: 'Breakfast' },
  mission: { icon: '🎯', color: 'text-blue-400', label: 'Mission' },
  social: { icon: '💬', color: 'text-purple-400', label: 'Social' },
  roundtable: { icon: '🗳️', color: 'text-orange-400', label: 'Round Table' },
  turret: { icon: '🗡️', color: 'text-red-400', label: 'Night' },
  complete: { icon: '🏆', color: 'text-green-400', label: 'Game Over' },
};

export function PhaseIndicator({
  day,
  phase,
  prizePot,
  aliveCount,
  totalPlayers,
}: PhaseIndicatorProps) {
  const phaseKey = phase.toLowerCase().replace('state_', '');
  const config = PHASE_CONFIG[phaseKey] || {
    icon: '⏳',
    color: 'text-gray-400',
    label: phase,
  };

  return (
    <div className="flex flex-wrap items-center gap-4 bg-gray-800 rounded-lg p-4">
      {/* Day */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">📅</span>
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">Day</p>
          <p className="text-xl font-bold text-white">{day}</p>
        </div>
      </div>

      {/* Divider */}
      <div className="h-10 w-px bg-gray-700" />

      {/* Phase */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">{config.icon}</span>
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">Phase</p>
          <p className={`text-xl font-bold ${config.color}`}>{config.label}</p>
        </div>
      </div>

      {/* Prize pot */}
      {prizePot !== undefined && (
        <>
          <div className="h-10 w-px bg-gray-700" />
          <div className="flex items-center gap-2">
            <span className="text-2xl">💰</span>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Prize Pot</p>
              <p className="text-xl font-bold text-green-400">
                £{new Intl.NumberFormat().format(prizePot)}
              </p>
            </div>
          </div>
        </>
      )}

      {/* Alive count */}
      {aliveCount !== undefined && totalPlayers !== undefined && (
        <>
          <div className="h-10 w-px bg-gray-700" />
          <div className="flex items-center gap-2">
            <span className="text-2xl">👥</span>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Alive</p>
              <p className="text-xl font-bold text-white">
                {aliveCount} / {totalPlayers}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
