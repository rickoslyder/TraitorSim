/**
 * TimelineScrubber - Navigate through game days and phases with event markers
 *
 * Features:
 * - Day navigation with phase buttons
 * - Inline event markers on timeline track (M=Murder, R=RoundTable, S=Shield, T=Turret, !=Drama)
 * - Keyboard navigation (arrow keys, Home/End)
 * - Event density visualization
 * - Click event markers to jump to that phase
 */

import { useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Phase, GameEvent, normalizePhase, EventType } from '../../types';
import { useGameStore } from '../../stores/gameStore';

// ============================================================================
// Constants
// ============================================================================

const PHASES: { id: Phase; label: string; icon: string; color: string }[] = [
  { id: 'breakfast', label: 'Breakfast', icon: '🍳', color: 'bg-yellow-500' },
  { id: 'mission', label: 'Mission', icon: '🎯', color: 'bg-green-500' },
  { id: 'social', label: 'Social', icon: '💬', color: 'bg-blue-500' },
  { id: 'roundtable', label: 'Round Table', icon: '🗳️', color: 'bg-purple-500' },
  { id: 'turret', label: 'Turret', icon: '🗡️', color: 'bg-red-500' },
];

// Event types that get markers on the timeline
const MARKER_EVENTS: EventType[] = [
  'MURDER_SUCCESS',
  'MURDER',
  'BANISHMENT',
  'VOTE_TALLY',
  'SHIELD_AWARDED',
  'SEER_AWARDED',
  'DAGGER_AWARDED',
  'TIE_VOTE',
  'RECRUITMENT_ACCEPTED',
  'RECRUITMENT_REFUSED',
  'MISSION_COMPLETE',
  'MISSION_SUCCESS',
  'MISSION_FAIL',
];

// Map event types to compact marker symbols
const EVENT_MARKERS: Record<string, { symbol: string; color: string; label: string }> = {
  MURDER_SUCCESS: { symbol: 'M', color: 'bg-red-600 text-white', label: 'Murder' },
  MURDER: { symbol: 'M', color: 'bg-red-600 text-white', label: 'Murder' },
  BANISHMENT: { symbol: 'B', color: 'bg-orange-500 text-white', label: 'Banishment' },
  VOTE_TALLY: { symbol: 'V', color: 'bg-purple-600 text-white', label: 'Vote' },
  SHIELD_AWARDED: { symbol: 'S', color: 'bg-yellow-500 text-black', label: 'Shield' },
  SEER_AWARDED: { symbol: '👁', color: 'bg-cyan-500 text-white', label: 'Seer Power' },
  DAGGER_AWARDED: { symbol: 'D', color: 'bg-red-500 text-white', label: 'Dagger' },
  TIE_VOTE: { symbol: '!', color: 'bg-orange-600 text-white', label: 'Tie Vote' },
  RECRUITMENT_ACCEPTED: { symbol: '!', color: 'bg-red-700 text-white', label: 'Recruitment' },
  RECRUITMENT_REFUSED: { symbol: '✋', color: 'bg-green-600 text-white', label: 'Refused' },
  MISSION_COMPLETE: { symbol: 'C', color: 'bg-blue-600 text-white', label: 'Mission' },
  MISSION_SUCCESS: { symbol: '✓', color: 'bg-green-600 text-white', label: 'Success' },
  MISSION_FAIL: { symbol: '✗', color: 'bg-red-500 text-white', label: 'Failed' },
};

// ============================================================================
// Types
// ============================================================================

interface TimelineScrubberProps {
  totalDays: number;
  events: GameEvent[];
}

interface TimelineMarker {
  day: number;
  phase: Phase;
  type: EventType;
  position: number; // 0-100% position on track
  event: GameEvent;
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Single event marker on the timeline track
 */
function EventMarker({
  marker,
  onClick,
  isCurrent,
}: {
  marker: TimelineMarker;
  onClick: () => void;
  isCurrent: boolean;
}) {
  const config = EVENT_MARKERS[marker.type];
  if (!config) return null;

  return (
    <motion.button
      className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${config.color} ${
        isCurrent ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-800 z-10' : ''
      } shadow-md hover:scale-125 transition-transform`}
      style={{ left: `${marker.position}%` }}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title={`${config.label}: Day ${marker.day} ${marker.phase}`}
      whileHover={{ scale: 1.3 }}
      whileTap={{ scale: 0.9 }}
    >
      {config.symbol}
    </motion.button>
  );
}

/**
 * Day marker button
 */
function DayMarker({
  day,
  isActive,
  hasEvents,
  onClick,
}: {
  day: number;
  isActive: boolean;
  hasEvents: boolean;
  onClick: () => void;
}) {
  return (
    <div className="flex flex-col items-center">
      <motion.button
        onClick={onClick}
        className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
          isActive
            ? 'bg-blue-500 text-white ring-2 ring-blue-400 ring-offset-2 ring-offset-gray-800'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        {day}
        {/* Event density indicator */}
        {hasEvents && !isActive && (
          <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
        )}
      </motion.button>
      <span className="text-xs text-gray-500 mt-1">Day {day}</span>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function TimelineScrubber({ totalDays, events }: TimelineScrubberProps) {
  const { currentDay, currentPhase, setTimelinePosition } = useGameStore();

  // Group events by day for quick lookup
  const eventsByDay = useMemo(() => {
    const grouped: Record<number, GameEvent[]> = {};
    for (const event of events) {
      if (!grouped[event.day]) grouped[event.day] = [];
      grouped[event.day].push(event);
    }
    return grouped;
  }, [events]);

  // Calculate timeline markers (significant events positioned on the track)
  const timelineMarkers = useMemo((): TimelineMarker[] => {
    const markers: TimelineMarker[] = [];
    const totalPhases = totalDays * PHASES.length;

    for (const event of events) {
      if (!MARKER_EVENTS.includes(event.type)) continue;

      const phaseIndex = PHASES.findIndex(p => p.id === normalizePhase(event.phase));
      if (phaseIndex === -1) continue;

      // Calculate position as percentage of total timeline
      const absolutePosition = (event.day - 1) * PHASES.length + phaseIndex;
      const position = (absolutePosition / (totalPhases - 1)) * 100;

      markers.push({
        day: event.day,
        phase: normalizePhase(event.phase) as Phase,
        type: event.type,
        position: Math.max(2, Math.min(98, position)), // Keep within bounds
        event,
      });
    }

    // Deduplicate markers at same position (keep most significant)
    const deduplicated = markers.reduce((acc, marker) => {
      const existing = acc.find(m => Math.abs(m.position - marker.position) < 2);
      if (!existing) {
        acc.push(marker);
      } else if (getEventPriority(marker.type) > getEventPriority(existing.type)) {
        const idx = acc.indexOf(existing);
        acc[idx] = marker;
      }
      return acc;
    }, [] as TimelineMarker[]);

    return deduplicated;
  }, [events, totalDays]);

  // Get significant events for a day (for old-style display above day markers)
  const getSignificantEvents = (day: number): GameEvent[] => {
    const dayEvents = eventsByDay[day] || [];
    return dayEvents.filter(e =>
      ['BANISHMENT', 'MURDER_SUCCESS', 'MURDER', 'SHIELD_AWARDED', 'SEER_AWARDED', 'RECRUITMENT_ACCEPTED'].includes(e.type)
    ).slice(0, 3);
  };

  // Check if day has significant events
  const dayHasEvents = (day: number): boolean => {
    return getSignificantEvents(day).length > 0;
  };

  // Calculate current position on timeline
  const currentPosition = useMemo(() => {
    const phaseIndex = PHASES.findIndex(p => p.id === currentPhase);
    const totalPhases = totalDays * PHASES.length;
    const absolutePosition = (currentDay - 1) * PHASES.length + phaseIndex;
    return (absolutePosition / (totalPhases - 1)) * 100;
  }, [currentDay, currentPhase, totalDays]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target instanceof HTMLSelectElement
    ) {
      return;
    }

    const phaseIndex = PHASES.findIndex(p => p.id === currentPhase);

    switch (e.key) {
      case 'ArrowRight':
        e.preventDefault();
        if (phaseIndex < PHASES.length - 1) {
          setTimelinePosition(currentDay, PHASES[phaseIndex + 1].id);
        } else if (currentDay < totalDays) {
          setTimelinePosition(currentDay + 1, PHASES[0].id);
        }
        break;
      case 'ArrowLeft':
        e.preventDefault();
        if (phaseIndex > 0) {
          setTimelinePosition(currentDay, PHASES[phaseIndex - 1].id);
        } else if (currentDay > 1) {
          setTimelinePosition(currentDay - 1, PHASES[PHASES.length - 1].id);
        }
        break;
      case 'Home':
        e.preventDefault();
        setTimelinePosition(1, PHASES[0].id);
        break;
      case 'End':
        e.preventDefault();
        setTimelinePosition(totalDays, PHASES[PHASES.length - 1].id);
        break;
    }
  }, [currentDay, currentPhase, totalDays, setTimelinePosition]);

  const handleDayClick = (day: number) => {
    setTimelinePosition(day, currentPhase);
  };

  const handlePhaseClick = (phase: Phase) => {
    setTimelinePosition(currentDay, phase);
  };

  const handleMarkerClick = (marker: TimelineMarker) => {
    setTimelinePosition(marker.day, marker.phase);
  };

  return (
    <div
      className="timeline-container space-y-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Phase selector */}
      <div className="flex justify-center gap-2">
        {PHASES.map(phase => (
          <button
            key={phase.id}
            onClick={() => handlePhaseClick(phase.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-colors ${
              currentPhase === phase.id
                ? `${phase.color} text-white`
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <span>{phase.icon}</span>
            <span className="text-sm hidden sm:inline">{phase.label}</span>
          </button>
        ))}
      </div>

      {/* Timeline track with event markers */}
      <div className="relative px-6">
        {/* Main track background */}
        <div className="absolute top-1/2 left-6 right-6 h-2 bg-gray-700 rounded-full transform -translate-y-1/2" />

        {/* Progress fill (shows how far we are) */}
        <motion.div
          className="absolute top-1/2 left-6 h-2 bg-blue-500/50 rounded-full transform -translate-y-1/2"
          style={{ width: `${currentPosition}%` }}
          animate={{ width: `${currentPosition}%` }}
          transition={{ duration: 0.3 }}
        />

        {/* Event markers on track */}
        <div className="relative h-8">
          {timelineMarkers.map((marker, idx) => (
            <EventMarker
              key={`${marker.type}-${marker.day}-${idx}`}
              marker={marker}
              onClick={() => handleMarkerClick(marker)}
              isCurrent={marker.day === currentDay && marker.phase === currentPhase}
            />
          ))}

          {/* Current position indicator */}
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-500 rounded-full border-2 border-white shadow-lg z-20"
            style={{ left: `${currentPosition}%` }}
            animate={{ left: `${currentPosition}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Day markers below track */}
      <div className="relative flex justify-between px-4">
        {Array.from({ length: totalDays }, (_, i) => i + 1).map(day => (
          <DayMarker
            key={day}
            day={day}
            isActive={day === currentDay}
            hasEvents={dayHasEvents(day)}
            onClick={() => handleDayClick(day)}
          />
        ))}
      </div>

      {/* Current position indicator text */}
      <div className="text-center text-sm text-gray-400">
        Day {currentDay} - {PHASES.find(p => p.id === currentPhase)?.label}
        <span className="text-gray-600 ml-2">(Focus the timeline to use arrow keys)</span>
      </div>

      {/* Legend for markers */}
      <div className="flex flex-wrap justify-center gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded-full bg-red-600 text-white flex items-center justify-center text-[8px] font-bold">M</span>
          Murder
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded-full bg-orange-500 text-white flex items-center justify-center text-[8px] font-bold">B</span>
          Banishment
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded-full bg-yellow-500 text-black flex items-center justify-center text-[8px] font-bold">S</span>
          Shield
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded-full bg-orange-600 text-white flex items-center justify-center text-[8px] font-bold">!</span>
          Drama
        </span>
      </div>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Get priority of event type for marker deduplication
 * Higher priority events replace lower priority ones at same position
 */
function getEventPriority(type: EventType): number {
  const priorities: Record<string, number> = {
    MURDER_SUCCESS: 100,
    MURDER: 100,
    RECRUITMENT_ACCEPTED: 90,
    TIE_VOTE: 85,
    BANISHMENT: 80,
    SHIELD_AWARDED: 70,
    SEER_AWARDED: 70,
    DAGGER_AWARDED: 70,
    VOTE_TALLY: 50,
    MISSION_FAIL: 40,
    MISSION_SUCCESS: 30,
    MISSION_COMPLETE: 20,
  };
  return priorities[type] || 0;
}

export default TimelineScrubber;
