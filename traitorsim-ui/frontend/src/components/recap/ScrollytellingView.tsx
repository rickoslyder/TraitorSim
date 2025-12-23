/**
 * ScrollytellingView - Full scrollytelling narrative experience
 *
 * A scroll-triggered journey through the entire game, presenting
 * each day as a dramatic narrative chapter with:
 * - Progress indicator showing position in the game
 * - Day-by-day breakdowns with key moments highlighted
 * - Smooth scroll animations and reveals
 * - Integration with POV toggle for spoiler control
 */

import { useMemo, useState, useRef, useEffect } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Player, GameEvent, getArchetypeColor } from '../../types';
import { DayRecap } from './DayRecap';
import { usePOVVisibility } from '../../hooks';

interface ScrollytellingViewProps {
  players: Record<string, Player>;
  events: GameEvent[];
  totalDays: number;
  prizePot?: number;
  winner?: 'FAITHFUL' | 'TRAITORS';
}

/**
 * Progress sidebar showing day navigation
 */
function ProgressSidebar({
  totalDays,
  currentDay,
  onDayClick,
}: {
  totalDays: number;
  currentDay: number;
  onDayClick: (day: number) => void;
}) {
  return (
    <nav className="fixed left-4 top-1/2 -translate-y-1/2 z-20 hidden lg:block">
      <div className="flex flex-col items-center gap-2">
        {Array.from({ length: totalDays }, (_, i) => i + 1).map(day => (
          <button
            key={day}
            onClick={() => onDayClick(day)}
            className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
              day === currentDay
                ? 'bg-blue-600 text-white scale-110 shadow-lg'
                : day < currentDay
                  ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
            }`}
            title={`Day ${day}`}
          >
            {day}
          </button>
        ))}
      </div>
    </nav>
  );
}

/**
 * Final results chapter
 */
function GameConclusion({
  winner,
  players,
  prizePot,
}: {
  winner: 'FAITHFUL' | 'TRAITORS';
  players: Record<string, Player>;
  prizePot: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { shouldRevealTraitor } = usePOVVisibility(players);

  // Get survivors
  const survivors = useMemo(() => {
    return Object.values(players).filter(p => p.alive);
  }, [players]);

  // Get traitors
  const traitors = useMemo(() => {
    return Object.values(players).filter(p => p.role === 'TRAITOR');
  }, [players]);

  // Get faithful
  const faithful = useMemo(() => {
    return Object.values(players).filter(p => p.role === 'FAITHFUL');
  }, [players]);

  return (
    <motion.article
      ref={ref}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
      className="game-conclusion text-center py-16"
    >
      {/* Victory banner */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        whileInView={{ scale: 1, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className={`inline-block px-8 py-4 rounded-lg mb-8 ${
          winner === 'TRAITORS'
            ? 'bg-red-900/50 border border-red-500'
            : 'bg-blue-900/50 border border-blue-500'
        }`}
      >
        <span className="text-5xl mb-4 block">
          {winner === 'TRAITORS' ? '🗡️' : '🏆'}
        </span>
        <h2 className={`text-3xl font-bold ${
          winner === 'TRAITORS' ? 'text-red-400' : 'text-blue-400'
        }`}>
          {winner === 'TRAITORS' ? 'The Traitors Win!' : 'The Faithful Triumph!'}
        </h2>
      </motion.div>

      {/* Prize pot */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        whileInView={{ y: 0, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mb-12"
      >
        <p className="text-gray-400 mb-2">Prize Pot</p>
        <p className="text-4xl font-bold text-yellow-400">
          £{prizePot.toLocaleString()}
        </p>
      </motion.div>

      {/* Survivors */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        whileInView={{ y: 0, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="mb-12"
      >
        <h3 className="text-xl font-semibold text-white mb-6">Survivors</h3>
        <div className="flex justify-center flex-wrap gap-4">
          {survivors.map(player => (
            <div
              key={player.id}
              className={`flex flex-col items-center p-4 bg-gray-800 rounded-lg ${
                shouldRevealTraitor(player) ? 'ring-2 ring-red-500' : ''
              }`}
            >
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold text-white mb-2"
                style={{ backgroundColor: getArchetypeColor(player.archetype_id || '') }}
              >
                {player.name.charAt(0)}
              </div>
              <p className="text-white font-medium">{player.name}</p>
              <p className={`text-sm ${
                player.role === 'TRAITOR' ? 'text-red-400' : 'text-blue-400'
              }`}>
                {player.role}
              </p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Role reveal */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        whileInView={{ y: 0, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.8 }}
        className="max-w-2xl mx-auto"
      >
        <h3 className="text-xl font-semibold text-white mb-6">Final Role Reveal</h3>

        <div className="grid grid-cols-2 gap-8">
          {/* Traitors */}
          <div>
            <h4 className="text-red-400 font-medium mb-3 flex items-center justify-center gap-2">
              <span>🗡️</span> Traitors ({traitors.length})
            </h4>
            <div className="space-y-2">
              {traitors.map(player => (
                <div
                  key={player.id}
                  className={`px-3 py-2 bg-red-900/30 rounded text-white text-sm ${
                    !player.alive ? 'opacity-60' : ''
                  }`}
                >
                  {player.name}
                  {!player.alive && (
                    <span className="text-gray-400 ml-2">
                      ({player.elimination_type === 'MURDERED' ? 'Murdered' : 'Banished'} Day {player.eliminated_day})
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Faithful */}
          <div>
            <h4 className="text-blue-400 font-medium mb-3 flex items-center justify-center gap-2">
              <span>🛡️</span> Faithful ({faithful.length})
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {faithful.map(player => (
                <div
                  key={player.id}
                  className={`px-3 py-2 bg-blue-900/30 rounded text-white text-sm ${
                    !player.alive ? 'opacity-60' : ''
                  }`}
                >
                  {player.name}
                  {!player.alive && (
                    <span className="text-gray-400 ml-2">
                      ({player.elimination_type === 'MURDERED' ? 'Murdered' : 'Banished'} Day {player.eliminated_day})
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.article>
  );
}

/**
 * Main ScrollytellingView component
 */
export function ScrollytellingView({
  players,
  events,
  totalDays,
  prizePot = 0,
  winner = 'FAITHFUL',
}: ScrollytellingViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleDay, setVisibleDay] = useState(1);
  const { isSpoilerFree } = usePOVVisibility(players);

  // Track scroll progress
  const { scrollYProgress } = useScroll({ container: containerRef });
  const progressWidth = useTransform(scrollYProgress, [0, 1], ['0%', '100%']);

  // Day section refs for scroll tracking
  const dayRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Track which day is visible
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const day = parseInt(entry.target.getAttribute('data-day') || '1', 10);
            setVisibleDay(day);
          }
        });
      },
      { threshold: 0.3 }
    );

    dayRefs.current.forEach(ref => {
      if (ref) observer.observe(ref);
    });

    return () => observer.disconnect();
  }, [totalDays]);

  // Scroll to specific day
  const scrollToDay = (day: number) => {
    const ref = dayRefs.current[day - 1];
    if (ref) {
      ref.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="scrollytelling-view relative">
      {/* Progress bar at top */}
      <div className="fixed top-0 left-0 right-0 z-30 h-1 bg-gray-800">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
          style={{ width: progressWidth }}
        />
      </div>

      {/* Spoiler warning for non-faithful modes */}
      {!isSpoilerFree && (
        <div className="sticky top-1 z-20 flex justify-center">
          <div className="bg-yellow-900/90 text-yellow-400 px-4 py-1 rounded-full text-xs backdrop-blur-sm">
            ⚠️ Spoilers visible - switch to Faithful POV for spoiler-free experience
          </div>
        </div>
      )}

      {/* Day navigation sidebar */}
      <ProgressSidebar
        totalDays={totalDays}
        currentDay={visibleDay}
        onDayClick={scrollToDay}
      />

      {/* Main content */}
      <div
        ref={containerRef}
        className="scrollytelling-content max-w-4xl mx-auto px-4 py-8"
      >
        {/* Prologue */}
        <motion.header
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center py-16 mb-16"
        >
          <h1 className="text-5xl font-bold text-white mb-4">
            The Traitors
          </h1>
          <p className="text-xl text-gray-400 mb-2">
            Ardross Castle, Scottish Highlands
          </p>
          <p className="text-lg text-gray-500">
            {Object.keys(players).length} players • {totalDays} days • £{prizePot.toLocaleString()} prize
          </p>

          <div className="mt-8 flex justify-center gap-6 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-red-500" />
              Traitors: {Object.values(players).filter(p => p.role === 'TRAITOR').length}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-blue-500" />
              Faithful: {Object.values(players).filter(p => p.role === 'FAITHFUL').length}
            </span>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-12 text-gray-600"
          >
            Scroll to begin the journey ↓
          </motion.div>
        </motion.header>

        {/* Day recaps */}
        {Array.from({ length: totalDays }, (_, i) => i + 1).map(day => (
          <div
            key={day}
            ref={el => { dayRefs.current[day - 1] = el; }}
            data-day={day}
          >
            <DayRecap
              day={day}
              events={events}
              players={players}
            />
          </div>
        ))}

        {/* Conclusion */}
        <GameConclusion
          winner={winner}
          players={players}
          prizePot={prizePot}
        />

        {/* End card */}
        <motion.footer
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center py-16 border-t border-gray-700"
        >
          <p className="text-gray-500 text-sm">
            End of simulation
          </p>
          <p className="text-gray-600 text-xs mt-2">
            Powered by TraitorSim AI
          </p>
        </motion.footer>
      </div>
    </div>
  );
}

export default ScrollytellingView;
