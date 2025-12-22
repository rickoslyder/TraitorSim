/**
 * TimelineScrubber - Navigate through game days and phases
 */

import { useCallback, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Phase, GameEvent, getEventInfo } from '../../types';
import { useGameStore } from '../../stores/gameStore';

const PHASES: { id: Phase; label: string; icon: string; color: string }[] = [
  { id: 'breakfast', label: 'Breakfast', icon: '🍳', color: 'bg-yellow-500' },
  { id: 'mission', label: 'Mission', icon: '🎯', color: 'bg-green-500' },
  { id: 'social', label: 'Social', icon: '💬', color: 'bg-blue-500' },
  { id: 'roundtable', label: 'Round Table', icon: '🗳️', color: 'bg-purple-500' },
  { id: 'turret', label: 'Turret', icon: '🗡️', color: 'bg-red-500' },
];

interface TimelineScrubberProps {
  totalDays: number;
  events: GameEvent[];
}

export function TimelineScrubber({ totalDays, events }: TimelineScrubberProps) {
  const { currentDay, currentPhase, setTimelinePosition } = useGameStore();

  // Group events by day
  const eventsByDay = useMemo(() => {
    const grouped: Record<number, GameEvent[]> = {};
    for (const event of events) {
      if (!grouped[event.day]) grouped[event.day] = [];
      grouped[event.day].push(event);
    }
    return grouped;
  }, [events]);

  // Get significant events for a day (for display)
  const getSignificantEvents = (day: number): GameEvent[] => {
    const dayEvents = eventsByDay[day] || [];
    return dayEvents.filter(e =>
      ['BANISHMENT', 'MURDER_SUCCESS', 'SHIELD_AWARDED', 'SEER_AWARDED', 'RECRUITMENT_ACCEPTED'].includes(e.type)
    );
  };

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
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

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleDayClick = (day: number) => {
    setTimelinePosition(day, currentPhase);
  };

  const handlePhaseClick = (phase: Phase) => {
    setTimelinePosition(currentDay, phase);
  };

  return (
    <div className="timeline-container space-y-4">
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

      {/* Day timeline */}
      <div className="relative">
        {/* Track */}
        <div className="absolute top-1/2 left-0 right-0 h-1 bg-gray-700 rounded-full transform -translate-y-1/2" />

        {/* Days */}
        <div className="relative flex justify-between px-4">
          {Array.from({ length: totalDays }, (_, i) => i + 1).map(day => {
            const isActive = day === currentDay;
            const significantEvents = getSignificantEvents(day);

            return (
              <div key={day} className="flex flex-col items-center">
                {/* Event indicators */}
                <div className="flex gap-0.5 mb-1 h-4">
                  {significantEvents.slice(0, 3).map((event, i) => {
                    const info = getEventInfo(event.type);
                    return (
                      <span
                        key={i}
                        className="text-xs"
                        title={`${info.label}${event.target ? `: ${event.target}` : ''}`}
                      >
                        {info.icon}
                      </span>
                    );
                  })}
                </div>

                {/* Day marker */}
                <motion.button
                  onClick={() => handleDayClick(day)}
                  className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-500 text-white ring-2 ring-blue-400 ring-offset-2 ring-offset-gray-800'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {day}
                </motion.button>

                {/* Day label */}
                <span className="text-xs text-gray-500 mt-1">
                  Day {day}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current position indicator */}
      <div className="text-center text-sm text-gray-400">
        Day {currentDay} - {PHASES.find(p => p.id === currentPhase)?.label}
        <span className="text-gray-600 ml-2">(Use arrow keys to navigate)</span>
      </div>
    </div>
  );
}

export default TimelineScrubber;
