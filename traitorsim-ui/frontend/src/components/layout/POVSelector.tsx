/**
 * POVSelector - Toggle between viewing perspectives
 *
 * Allows viewers to experience the game from different perspectives:
 * - Omniscient: Full spoilers (see all roles, trust, murder discussions)
 * - Faithful: Spoiler-free (experience like a Faithful contestant)
 * - Traitor: Traitor knowledge (see fellow Traitors, murder decisions)
 *
 * This implements the "Spoiler Shield" UX pattern from the research doc,
 * enabling viewers to control their experience.
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useGameStore, ViewingMode } from '../../stores/gameStore';
import type { Player } from '../../types/player';

interface POVSelectorProps {
  players?: Record<string, Player>;
  compact?: boolean;
}

const MODE_CONFIG: Record<ViewingMode, {
  label: string;
  shortLabel: string;
  icon: string;
  color: string;
  bgColor: string;
  description: string;
}> = {
  omniscient: {
    label: 'Omniscient',
    shortLabel: 'God',
    icon: '👁️',
    color: 'text-purple-400',
    bgColor: 'bg-purple-600',
    description: 'See everything: all roles, trust, and secrets',
  },
  faithful: {
    label: 'Faithful POV',
    shortLabel: 'Faithful',
    icon: '🙈',
    color: 'text-blue-400',
    bgColor: 'bg-blue-600',
    description: 'Spoiler-free: experience like a contestant',
  },
  traitor: {
    label: 'Traitor POV',
    shortLabel: 'Traitor',
    icon: '🗡️',
    color: 'text-red-400',
    bgColor: 'bg-red-600',
    description: 'See Traitor knowledge: murders, recruitment',
  },
};

export function POVSelector({ players = {}, compact = false }: POVSelectorProps) {
  const {
    viewingMode,
    setViewingMode,
    povPlayerId,
    setPovPlayer,
  } = useGameStore();

  // Get alive Faithful players for POV selection
  const faithfulPlayers = useMemo(() => {
    return Object.values(players)
      .filter(p => p.role === 'FAITHFUL' && p.alive)
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [players]);

  // Get Traitor count for info display
  const traitorCount = useMemo(() => {
    return Object.values(players).filter(p => p.role === 'TRAITOR').length;
  }, [players]);

  const currentConfig = MODE_CONFIG[viewingMode];

  if (compact) {
    // Compact mode: just show current mode with dropdown
    return (
      <div className="pov-selector-compact flex items-center gap-2">
        <span className="text-gray-400 text-sm">POV:</span>
        <select
          value={viewingMode}
          onChange={(e) => setViewingMode(e.target.value as ViewingMode)}
          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Select viewing perspective"
        >
          {Object.entries(MODE_CONFIG).map(([mode, config]) => (
            <option key={mode} value={mode}>
              {config.icon} {config.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="pov-selector space-y-3">
      {/* Mode selector buttons */}
      <div className="flex rounded-lg bg-gray-800 p-1 gap-1">
        {Object.entries(MODE_CONFIG).map(([mode, config]) => (
          <button
            key={mode}
            onClick={() => setViewingMode(mode as ViewingMode)}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md transition-colors ${
              viewingMode === mode
                ? `${config.bgColor} text-white shadow-lg`
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
            title={config.description}
          >
            <span>{config.icon}</span>
            <span className="text-sm font-medium hidden sm:inline">{config.label}</span>
            <span className="text-sm font-medium sm:hidden">{config.shortLabel}</span>
          </button>
        ))}
      </div>

      {/* Mode description */}
      <motion.div
        key={viewingMode}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-xs text-gray-500 text-center"
      >
        {currentConfig.description}
      </motion.div>

      {/* Faithful POV player selector */}
      {viewingMode === 'faithful' && faithfulPlayers.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="pt-2 border-t border-gray-700"
        >
          <label htmlFor="pov-player-select" className="text-xs text-gray-400 block mb-2">
            View from perspective of:
          </label>
          <select
            id="pov-player-select"
            value={povPlayerId || ''}
            onChange={(e) => setPovPlayer(e.target.value || null)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Select Faithful player perspective"
          >
            <option value="">Random Faithful</option>
            {faithfulPlayers.map((player) => (
              <option key={player.id} value={player.id}>
                {player.name} ({player.archetype_name || 'Unknown'})
              </option>
            ))}
          </select>
        </motion.div>
      )}

      {/* Traitor mode info */}
      {viewingMode === 'traitor' && traitorCount > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="pt-2 border-t border-gray-700"
        >
          <div className="flex items-center gap-2 text-sm text-red-400">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>Viewing as Traitor ({traitorCount} Traitor{traitorCount !== 1 ? 's' : ''} in game)</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Murder targets, recruitment discussions, and Traitor strategies are revealed.
          </p>
        </motion.div>
      )}

      {/* Spoiler warning for non-faithful modes */}
      {viewingMode !== 'faithful' && (
        <div className="flex items-center gap-2 px-3 py-2 bg-yellow-900/30 border border-yellow-700/50 rounded-lg">
          <span className="text-yellow-500">⚠️</span>
          <span className="text-xs text-yellow-400">
            {viewingMode === 'omniscient'
              ? 'Spoilers enabled - all roles and secrets visible'
              : 'Traitor knowledge visible - partial spoilers'}
          </span>
        </div>
      )}
    </div>
  );
}

export default POVSelector;
