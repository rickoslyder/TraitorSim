/**
 * Event notification component.
 * Displays a single game event with appropriate styling.
 */

import type { GameEvent } from '../../types/live';

interface EventNotificationProps {
  event: GameEvent;
  showDayPhase?: boolean;
}

// Event type configuration
const EVENT_CONFIG: Record<
  string,
  { icon: string; color: string; label: string }
> = {
  ELIMINATION: { icon: '💀', color: 'text-red-400', label: 'Elimination' },
  BANISHMENT: { icon: '🚪', color: 'text-orange-400', label: 'Banished' },
  MURDER: { icon: '🗡️', color: 'text-red-500', label: 'Murdered' },
  VOTE: { icon: '🗳️', color: 'text-blue-400', label: 'Vote' },
  PHASE_CHANGE: { icon: '⏰', color: 'text-yellow-400', label: 'Phase Change' },
  MISSION_START: { icon: '🎯', color: 'text-blue-400', label: 'Mission' },
  MISSION_COMPLETE: { icon: '✅', color: 'text-green-400', label: 'Mission Complete' },
  MISSION_FAILED: { icon: '❌', color: 'text-red-400', label: 'Mission Failed' },
  SHIELD_USED: { icon: '🛡️', color: 'text-cyan-400', label: 'Shield' },
  SHIELD_AWARDED: { icon: '🛡️', color: 'text-cyan-400', label: 'Shield Awarded' },
  RECRUITMENT: { icon: '🎭', color: 'text-purple-400', label: 'Recruitment' },
  RECRUITMENT_ACCEPTED: { icon: '🎭', color: 'text-purple-400', label: 'Joined Traitors' },
  RECRUITMENT_DECLINED: { icon: '💙', color: 'text-blue-400', label: 'Stayed Faithful' },
  GAME_START: { icon: '🎮', color: 'text-green-400', label: 'Game Started' },
  GAME_END: { icon: '🏆', color: 'text-yellow-400', label: 'Game Over' },
  FAITHFUL_WIN: { icon: '💙', color: 'text-blue-400', label: 'Faithful Victory' },
  TRAITOR_WIN: { icon: '🗡️', color: 'text-red-400', label: 'Traitor Victory' },
};

export function EventNotification({
  event,
  showDayPhase = false,
}: EventNotificationProps) {
  const eventType = event.type.toUpperCase();
  const config = EVENT_CONFIG[eventType] || {
    icon: '📢',
    color: 'text-gray-400',
    label: event.type,
  };

  return (
    <div
      className={`
        flex items-start gap-3 p-3 rounded-lg bg-gray-700/50
        ${event.is_private ? 'border-l-2 border-red-500/50' : ''}
      `}
    >
      {/* Icon */}
      <span className="text-lg flex-shrink-0">{config.icon}</span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${config.color}`}>
            {config.label}
          </span>
          {showDayPhase && (
            <span className="text-xs text-gray-500">
              Day {event.day} · {formatPhase(event.phase)}
            </span>
          )}
          {event.is_private && (
            <span className="text-xs text-red-400">(Traitor Only)</span>
          )}
        </div>

        {/* Narrative */}
        {event.narrative && (
          <p className="text-sm text-gray-300 mt-1">{event.narrative}</p>
        )}
      </div>
    </div>
  );
}

function formatPhase(phase: string): string {
  const phaseNames: Record<string, string> = {
    breakfast: 'Breakfast',
    mission: 'Mission',
    social: 'Social',
    roundtable: 'Round Table',
    turret: 'Night',
  };
  const key = phase.toLowerCase().replace('state_', '');
  return phaseNames[key] || phase;
}
