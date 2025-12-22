/**
 * PlayerGrid - Grid layout for all player cards with search and filter
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Player, TrustMatrix, GameEvent } from '../../types';
import { PlayerCard } from './PlayerCard';
import { PlayerDetailModal } from './PlayerDetailModal';
import { useGameStore } from '../../stores/gameStore';

interface PlayerGridProps {
  players: Record<string, Player>;
  trustMatrix: TrustMatrix;
  events?: GameEvent[];
}

export function PlayerGrid({ players, trustMatrix, events = [] }: PlayerGridProps) {
  const {
    selectedPlayerId,
    selectPlayer,
    showRoles,
    showEliminatedPlayers,
    currentDay,
  } = useGameStore();

  // Search and filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [archetypeFilter, setArchetypeFilter] = useState<string | null>(null);
  const [detailPlayer, setDetailPlayer] = useState<Player | null>(null);

  // Get unique archetypes for filter dropdown
  const uniqueArchetypes = useMemo(() => {
    const archetypes = new Set<string>();
    Object.values(players).forEach(p => {
      if (p.archetype_name) archetypes.add(p.archetype_name);
    });
    return Array.from(archetypes).sort();
  }, [players]);

  // Filter and sort players
  const filteredPlayers = useMemo(() => {
    return Object.values(players)
      .filter(player => {
        // Search filter
        if (searchTerm) {
          const term = searchTerm.toLowerCase();
          const matchesName = player.name.toLowerCase().includes(term);
          const matchesArchetype = player.archetype_name?.toLowerCase().includes(term);
          if (!matchesName && !matchesArchetype) return false;
        }

        // Archetype filter
        if (archetypeFilter && player.archetype_name !== archetypeFilter) {
          return false;
        }

        // Filter out eliminated players if setting is off
        if (!showEliminatedPlayers && !player.alive) return false;

        // Filter out players eliminated before current day
        if (player.eliminated_day && player.eliminated_day < currentDay) {
          return showEliminatedPlayers;
        }

        return true;
      })
      .sort((a, b) => {
        // Sort: alive first, then by elimination day (latest first), then by name
        if (a.alive !== b.alive) return a.alive ? -1 : 1;
        if (a.eliminated_day && b.eliminated_day) {
          return b.eliminated_day - a.eliminated_day;
        }
        return a.name.localeCompare(b.name);
      });
  }, [players, searchTerm, archetypeFilter, showEliminatedPlayers, currentDay]);

  const handlePlayerClick = (player: Player) => {
    selectPlayer(player.id === selectedPlayerId ? null : player.id);
    setDetailPlayer(player);
  };

  const handleCloseModal = () => {
    setDetailPlayer(null);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setArchetypeFilter(null);
  };

  const hasFilters = searchTerm || archetypeFilter;

  return (
    <>
      {/* Search and Filter Bar */}
      <div className="sticky top-0 z-10 bg-gray-900 p-4 border-b border-gray-700">
        <div className="flex flex-wrap gap-3">
          {/* Search input */}
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search players..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 pl-10 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
              🔍
            </span>
          </div>

          {/* Archetype filter */}
          <select
            value={archetypeFilter || ''}
            onChange={e => setArchetypeFilter(e.target.value || null)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Archetypes</option>
            {uniqueArchetypes.map(arch => (
              <option key={arch} value={arch}>{arch}</option>
            ))}
          </select>

          {/* Clear filters button */}
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
            >
              Clear
            </button>
          )}

          {/* Results count */}
          <div className="flex items-center text-sm text-gray-500 ml-auto">
            {filteredPlayers.length} of {Object.keys(players).length} players
          </div>
        </div>
      </div>

      {/* Player Grid */}
      {filteredPlayers.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <span className="text-4xl mb-2">🔍</span>
          <p>No players match your search</p>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="mt-2 text-blue-400 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
          <AnimatePresence mode="popLayout">
            {filteredPlayers.map(player => (
              <motion.div
                key={player.id}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
              >
                <PlayerCard
                  player={player}
                  trustMatrix={trustMatrix}
                  isSelected={player.id === selectedPlayerId}
                  showRole={showRoles}
                  onClick={() => handlePlayerClick(player)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Player Detail Modal */}
      <AnimatePresence>
        {detailPlayer && (
          <PlayerDetailModal
            player={detailPlayer}
            players={players}
            events={events}
            trustMatrix={trustMatrix}
            onClose={handleCloseModal}
          />
        )}
      </AnimatePresence>
    </>
  );
}

export default PlayerGrid;
