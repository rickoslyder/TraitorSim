/**
 * EventFeed - Scrolling list of game events
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameEvent, EventType, getEventInfo, normalizePhase } from '../../types';
import { useGameStore } from '../../stores/gameStore';
import { usePOVVisibility } from '../../hooks';

interface EventFeedProps {
  events: GameEvent[];
  maxDay?: number;
}

const EVENT_TYPE_FILTERS: { label: string; types: EventType[] }[] = [
  { label: 'All', types: [] },
  { label: 'Eliminations', types: ['BANISHMENT', 'MURDER_SUCCESS', 'MURDER_BLOCKED'] },
  { label: 'Votes', types: ['VOTE', 'TIE_VOTE', 'REVOTE'] },
  { label: 'Powers', types: ['SHIELD_AWARDED', 'SEER_AWARDED', 'SEER_USED', 'DAGGER_AWARDED'] },
  { label: 'Missions', types: ['MISSION_SUCCESS', 'MISSION_FAIL'] },
  { label: 'Recruitment', types: ['RECRUITMENT_OFFER', 'RECRUITMENT_ACCEPTED', 'RECRUITMENT_REFUSED'] },
];

export function EventFeed({ events, maxDay }: EventFeedProps) {
  const { setTimelinePosition, currentDay, currentPhase } = useGameStore();
  const effectiveMaxDay = maxDay ?? currentDay;

  // POV-aware event filtering (hides Traitor-only events in Faithful mode)
  const { filterVisibleEvents, isSpoilerFree } = usePOVVisibility();

  const [filterIndex, setFilterIndex] = useState(0);
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);

  // Filter events with POV awareness
  const filteredEvents = useMemo(() => {
    // First apply POV filter (hides murder planning, recruitment offers in Faithful mode)
    let filtered = filterVisibleEvents(events);

    // Then filter by day
    filtered = filtered.filter(e => e.day <= effectiveMaxDay);

    // Apply type filter
    const filter = EVENT_TYPE_FILTERS[filterIndex];
    if (filter.types.length > 0) {
      filtered = filtered.filter(e => filter.types.includes(e.type));
    }

    // Sort by day (descending), then by type priority
    return filtered.sort((a, b) => {
      if (a.day !== b.day) return b.day - a.day;
      return 0;
    });
  }, [events, effectiveMaxDay, filterIndex, filterVisibleEvents]);

  const handleEventClick = (event: GameEvent) => {
    // Navigate to event's day/phase (normalize phase for consistency)
    setTimelinePosition(event.day, normalizePhase(event.phase));
    setExpandedEvent(expandedEvent === event.id ? null : event.id ?? null);
  };

  // Group events by day
  const eventsByDay = useMemo(() => {
    const grouped: Record<number, GameEvent[]> = {};
    for (const event of filteredEvents) {
      if (!grouped[event.day]) grouped[event.day] = [];
      grouped[event.day].push(event);
    }
    return grouped;
  }, [filteredEvents]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {EVENT_TYPE_FILTERS.map((filter, i) => (
          <button
            key={filter.label}
            onClick={() => setFilterIndex(i)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              filterIndex === i
                ? 'bg-blue-500 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Event list by day */}
      <div className="space-y-6 max-h-[600px] overflow-y-auto pr-2">
        {Object.entries(eventsByDay)
          .sort(([a], [b]) => Number(b) - Number(a))
          .map(([day, dayEvents]) => (
            <div key={day}>
              <h3 className="text-sm font-medium text-gray-400 mb-2 sticky top-0 bg-gray-900 py-1">
                Day {day}
              </h3>

              <AnimatePresence mode="popLayout">
                <div className="space-y-2">
                  {dayEvents.map((event, index) => {
                    const info = getEventInfo(event.type);
                    const isExpanded = expandedEvent === event.id;
                    const isCurrent = event.day === currentDay && normalizePhase(event.phase) === currentPhase;

                    return (
                      <motion.div
                        key={event.id ?? `${event.type}-${index}`}
                        layout
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ delay: index * 0.02 }}
                        className={`bg-gray-800 rounded-lg p-3 cursor-pointer transition-colors ${
                          isCurrent ? 'ring-1 ring-blue-400' : 'hover:bg-gray-750'
                        }`}
                        onClick={() => handleEventClick(event)}
                      >
                        <div className="flex items-start gap-3">
                          {/* Event icon */}
                          <div className={`event-icon ${info.color} flex-shrink-0`}>
                            {info.icon}
                          </div>

                          {/* Event content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white">
                                {info.label}
                              </span>
                              <span className="text-xs text-gray-500 capitalize">
                                {event.phase}
                              </span>
                            </div>

                            {/* Actor/target info */}
                            {(event.actor || event.target) && (
                              <p className="text-sm text-gray-400 mt-0.5">
                                {event.actor && <span>{event.actor}</span>}
                                {event.actor && event.target && <span> → </span>}
                                {event.target && <span>{event.target}</span>}
                              </p>
                            )}

                            {/* Narrative (expanded) */}
                            <AnimatePresence>
                              {isExpanded && event.narrative && (
                                <motion.p
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="text-sm text-gray-300 mt-2 italic"
                                >
                                  "{event.narrative}"
                                </motion.p>
                              )}
                            </AnimatePresence>
                          </div>

                          {/* Expand indicator */}
                          {event.narrative && (
                            <motion.div
                              animate={{ rotate: isExpanded ? 180 : 0 }}
                              className="text-gray-500"
                            >
                              ▼
                            </motion.div>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </AnimatePresence>
            </div>
          ))}

        {filteredEvents.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            No events match the current filter
          </div>
        )}
      </div>

      {/* Stats and POV indicator */}
      <div className="text-xs text-gray-500 text-center space-y-1">
        <div>Showing {filteredEvents.length} events</div>
        {isSpoilerFree && (
          <div className="text-yellow-500">
            👁️ Faithful POV - some events hidden
          </div>
        )}
      </div>
    </div>
  );
}

export default EventFeed;
