/**
 * DayRecap - Scrollytelling narrative view for a single day
 *
 * Presents events in dramatic, newspaper-headline style with:
 * - Phase-by-phase breakdown
 * - Highlighted key moments (murders, banishments, shields)
 * - Player portraits and quotes
 * - Suspenseful reveal animations
 */

import { useMemo, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Player, GameEvent, getArchetypeColor, normalizePhase } from '../../types';
import { usePOVVisibility } from '../../hooks';
import { useGameStore } from '../../stores/gameStore';

interface DayRecapProps {
  day: number;
  events: GameEvent[];
  players: Record<string, Player>;
}

// Phase display configuration
const PHASE_CONFIG: Record<string, { icon: string; title: string; color: string }> = {
  breakfast: { icon: '🍳', title: 'Morning Reveal', color: 'text-yellow-400' },
  mission: { icon: '🎯', title: 'The Mission', color: 'text-green-400' },
  social: { icon: '💬', title: 'Whispers & Alliances', color: 'text-blue-400' },
  roundtable: { icon: '🗳️', title: 'The Round Table', color: 'text-purple-400' },
  turret: { icon: '🗡️', title: 'The Turret', color: 'text-red-400' },
};

/**
 * Single event card within a phase
 */
function EventCard({
  event,
  players,
  isKeyEvent,
}: {
  event: GameEvent;
  players: Record<string, Player>;
  isKeyEvent: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const { setTimelinePosition } = useGameStore();
  const { shouldRevealTraitor } = usePOVVisibility(players);

  const actor = event.actor ? players[event.actor] : null;
  const target = event.target ? players[event.target] : null;

  const handleClick = () => {
    setTimelinePosition(event.day, normalizePhase(event.phase));
  };

  // Determine event styling based on type
  const getEventStyling = () => {
    switch (event.type) {
      case 'MURDER_SUCCESS':
      case 'MURDER':
        return {
          border: 'border-red-500',
          bg: 'bg-red-900/30',
          icon: '💀',
          headline: target ? `${target.name} was Murdered` : 'A Murder in the Night',
        };
      case 'BANISHMENT':
        return {
          border: 'border-orange-500',
          bg: 'bg-orange-900/30',
          icon: '⚖️',
          headline: target ? `${target.name} was Banished` : 'Banishment!',
        };
      case 'SHIELD_AWARDED':
        return {
          border: 'border-yellow-500',
          bg: 'bg-yellow-900/30',
          icon: '🛡️',
          headline: target ? `${target.name} Wins the Shield` : 'Shield Awarded',
        };
      case 'SEER_AWARDED':
        return {
          border: 'border-cyan-500',
          bg: 'bg-cyan-900/30',
          icon: '👁️',
          headline: target ? `${target.name} Receives the Seer Power` : 'Seer Power Granted',
        };
      case 'DAGGER_AWARDED':
        return {
          border: 'border-red-600',
          bg: 'bg-red-900/30',
          icon: '🗡️',
          headline: target ? `${target.name} Holds the Dagger` : 'The Dagger Changes Hands',
        };
      case 'RECRUITMENT_ACCEPTED':
        return {
          border: 'border-purple-500',
          bg: 'bg-purple-900/30',
          icon: '🎭',
          headline: target ? `${target.name} Joins the Traitors` : 'A New Traitor Rises',
        };
      case 'RECRUITMENT_REFUSED':
        return {
          border: 'border-blue-500',
          bg: 'bg-blue-900/30',
          icon: '✋',
          headline: target ? `${target.name} Refuses the Darkness` : 'Recruitment Refused',
        };
      case 'TIE_VOTE':
        return {
          border: 'border-orange-400',
          bg: 'bg-orange-900/30',
          icon: '⚔️',
          headline: 'Deadlock at the Round Table',
        };
      case 'MISSION_SUCCESS':
        return {
          border: 'border-green-500',
          bg: 'bg-green-900/30',
          icon: '✓',
          headline: 'Mission Success!',
        };
      case 'MISSION_FAIL':
        return {
          border: 'border-red-400',
          bg: 'bg-red-900/30',
          icon: '✗',
          headline: 'Mission Failed',
        };
      default:
        return {
          border: 'border-gray-600',
          bg: 'bg-gray-800/50',
          icon: '📋',
          headline: event.type.replace(/_/g, ' '),
        };
    }
  };

  const styling = getEventStyling();

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
      transition={{ duration: 0.5 }}
      onClick={handleClick}
      className={`cursor-pointer transition-transform hover:scale-[1.02] ${
        isKeyEvent ? 'my-6' : 'my-3'
      }`}
    >
      <div className={`rounded-lg border-l-4 ${styling.border} ${styling.bg} overflow-hidden`}>
        {/* Headline for key events */}
        {isKeyEvent && (
          <div className="px-4 py-3 border-b border-gray-700/50">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{styling.icon}</span>
              <h4 className="text-lg font-bold text-white">{styling.headline}</h4>
            </div>
          </div>
        )}

        <div className="p-4">
          {/* Player portraits for events with actors/targets */}
          {(actor || target) && (
            <div className="flex items-center gap-4 mb-3">
              {actor && (
                <div className="flex items-center gap-2">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold text-white ${
                      shouldRevealTraitor(actor) ? 'ring-2 ring-red-500' : ''
                    }`}
                    style={{ backgroundColor: getArchetypeColor(actor.archetype_id || '') }}
                  >
                    {actor.name.charAt(0)}
                  </div>
                  <span className="text-sm text-gray-300">{actor.name}</span>
                </div>
              )}

              {actor && target && (
                <span className="text-gray-500">→</span>
              )}

              {target && (
                <div className="flex items-center gap-2">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold text-white ${
                      shouldRevealTraitor(target) ? 'ring-2 ring-red-500' : ''
                    } ${!target.alive ? 'opacity-50' : ''}`}
                    style={{ backgroundColor: getArchetypeColor(target.archetype_id || '') }}
                  >
                    {target.name.charAt(0)}
                  </div>
                  <span className="text-sm text-gray-300">{target.name}</span>
                </div>
              )}
            </div>
          )}

          {/* Narrative text */}
          {event.narrative && (
            <p className="text-gray-300 text-sm leading-relaxed italic">
              "{event.narrative}"
            </p>
          )}

          {/* Click hint */}
          <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
            <span className="capitalize">{event.phase}</span>
            <span className="text-blue-400">Click to jump →</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Phase section within a day
 */
function PhaseSection({
  phase,
  events,
  players,
}: {
  phase: string;
  events: GameEvent[];
  players: Record<string, Player>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });

  const config = PHASE_CONFIG[phase] || {
    icon: '📋',
    title: phase.charAt(0).toUpperCase() + phase.slice(1),
    color: 'text-gray-400',
  };

  // Determine which events are "key" (headline-worthy)
  const keyEventTypes = [
    'MURDER_SUCCESS', 'MURDER', 'BANISHMENT', 'SHIELD_AWARDED',
    'SEER_AWARDED', 'DAGGER_AWARDED', 'RECRUITMENT_ACCEPTED',
    'RECRUITMENT_REFUSED', 'TIE_VOTE',
  ];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : { opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-8"
    >
      {/* Phase header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{config.icon}</span>
        <h3 className={`text-xl font-semibold ${config.color}`}>
          {config.title}
        </h3>
        <div className="flex-1 h-px bg-gray-700" />
      </div>

      {/* Events */}
      {events.length > 0 ? (
        <div className="space-y-2">
          {events.map((event, idx) => (
            <EventCard
              key={event.id ?? idx}
              event={event}
              players={players}
              isKeyEvent={keyEventTypes.includes(event.type)}
            />
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-sm italic pl-4">
          No significant events during this phase.
        </p>
      )}
    </motion.div>
  );
}

/**
 * Main DayRecap component
 */
export function DayRecap({ day, events, players }: DayRecapProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const { filterVisibleEvents } = usePOVVisibility(players);

  // Filter events for this day and by POV visibility
  const dayEvents = useMemo(() => {
    return filterVisibleEvents(
      events.filter(e => e.day === day)
    );
  }, [events, day, filterVisibleEvents]);

  // Group events by phase
  const eventsByPhase = useMemo(() => {
    const phases = ['breakfast', 'mission', 'social', 'roundtable', 'turret'];
    const grouped: Record<string, GameEvent[]> = {};

    for (const phase of phases) {
      grouped[phase] = dayEvents.filter(
        e => normalizePhase(e.phase) === phase
      );
    }

    return grouped;
  }, [dayEvents]);

  // Get summary stats for the day
  const daySummary = useMemo(() => {
    const murders = dayEvents.filter(e => e.type === 'MURDER_SUCCESS' || e.type === 'MURDER').length;
    const banishments = dayEvents.filter(e => e.type === 'BANISHMENT').length;
    const shieldsAwarded = dayEvents.filter(e => e.type === 'SHIELD_AWARDED').length;

    return { murders, banishments, shieldsAwarded };
  }, [dayEvents]);

  // Count alive players at end of day
  const aliveCount = useMemo(() => {
    return Object.values(players).filter(
      p => p.alive || (p.eliminated_day && p.eliminated_day > day)
    ).length;
  }, [players, day]);

  return (
    <motion.article
      ref={ref}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : { opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="day-recap mb-16"
    >
      {/* Day header - newspaper style */}
      <header className="text-center mb-8 pb-6 border-b border-gray-700">
        <motion.div
          initial={{ scale: 0.9 }}
          animate={isInView ? { scale: 1 } : { scale: 0.9 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <span className="text-sm text-gray-500 uppercase tracking-widest">
            Ardross Castle Chronicle
          </span>
          <h2 className="text-4xl font-bold text-white mt-2 mb-3">
            Day {day}
          </h2>

          {/* Summary badges */}
          <div className="flex justify-center gap-4 text-sm">
            {daySummary.murders > 0 && (
              <span className="px-3 py-1 bg-red-900/50 text-red-400 rounded-full">
                💀 {daySummary.murders} Murder{daySummary.murders > 1 ? 's' : ''}
              </span>
            )}
            {daySummary.banishments > 0 && (
              <span className="px-3 py-1 bg-orange-900/50 text-orange-400 rounded-full">
                ⚖️ {daySummary.banishments} Banishment{daySummary.banishments > 1 ? 's' : ''}
              </span>
            )}
            {daySummary.shieldsAwarded > 0 && (
              <span className="px-3 py-1 bg-yellow-900/50 text-yellow-400 rounded-full">
                🛡️ Shield Awarded
              </span>
            )}
            <span className="px-3 py-1 bg-gray-800 text-gray-400 rounded-full">
              👥 {aliveCount} Remaining
            </span>
          </div>
        </motion.div>
      </header>

      {/* Phases */}
      <div className="max-w-2xl mx-auto">
        {Object.entries(eventsByPhase).map(([phase, phaseEvents]) => (
          <PhaseSection
            key={phase}
            phase={phase}
            events={phaseEvents}
            players={players}
          />
        ))}
      </div>
    </motion.article>
  );
}

export default DayRecap;
