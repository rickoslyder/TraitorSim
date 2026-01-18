/**
 * Sidebar - Game list and selection
 *
 * Uses TanStack Query for loading games list and Zustand for selection state.
 * Collapsible on mobile with overlay backdrop.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../../stores/gameStore';
import { useGames, usePrefetchGame, useRunStatus } from '../../api/hooks';
import { LoadingFallback, QueryErrorFallback } from '../ErrorBoundary';
import { GameRunner } from '../runner';

export function Sidebar() {
  const [runnerOpen, setRunnerOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOption, setSortOption] = useState<'recent' | 'alphabetical' | 'in-progress'>(
    'recent'
  );
  const { data: runStatus } = useRunStatus();
  // UI state from Zustand
  const { selectedGameId, selectGame, sidebarOpen, setSidebarOpen } = useGameStore();

  // Server state from TanStack Query
  const { data, isLoading, error, refetch } = useGames();
  const prefetchGame = usePrefetchGame();

  const games = data?.games || [];
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredGames = games.filter(game =>
    game.name.toLowerCase().includes(normalizedSearch)
  );
  const sortedGames = [...filteredGames].sort((a, b) => {
    if (sortOption === 'alphabetical') {
      return a.name.localeCompare(b.name);
    }
    const aInProgress = a.winner === '' || a.winner === 'UNKNOWN';
    const bInProgress = b.winner === '' || b.winner === 'UNKNOWN';
    if (sortOption === 'in-progress' && aInProgress !== bInProgress) {
      return aInProgress ? -1 : 1;
    }
    const aDate = Date.parse(a.created_at) || 0;
    const bDate = Date.parse(b.created_at) || 0;
    return bDate - aDate;
  });
  const hasSearch = normalizedSearch.length > 0;

  const handleGameSelect = (gameId: string) => {
    selectGame(gameId);
    // Close sidebar on mobile after selection
    setSidebarOpen(false);
  };

  const handleGameHover = (gameId: string) => {
    // Prefetch game data on hover for faster loading
    prefetchGame(gameId);
  };

  const handleBackdropClick = () => {
    setSidebarOpen(false);
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-30 md:hidden"
            onClick={handleBackdropClick}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-64 bg-gray-800 border-r border-gray-700 flex flex-col
          transform transition-transform duration-300 ease-in-out
          md:relative md:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Game Sessions
        </h2>
      </div>

      {/* Run New Game button */}
      <div className="p-2 border-b border-gray-700">
        <motion.button
          onClick={() => setRunnerOpen(true)}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
            runStatus?.running
              ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
              : 'bg-green-600 hover:bg-green-500 text-white'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {runStatus?.running ? (
            <>
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-300 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-yellow-200" />
              </span>
              Game Running...
            </>
          ) : (
            <>
              <span>▶</span>
              Run New Game
            </>
          )}
        </motion.button>
      </div>

      <div className="p-2 border-b border-gray-700 space-y-2">
        <label className="block text-xs text-gray-400">
          <span className="sr-only">Search games</span>
          <input
            type="search"
            value={searchTerm}
            onChange={event => setSearchTerm(event.target.value)}
            placeholder="Search games"
            className="w-full rounded-md bg-gray-750 border border-gray-700 px-2.5 py-1.5 text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>
        <label className="block text-xs text-gray-400">
          <span className="sr-only">Sort games</span>
          <select
            value={sortOption}
            onChange={event =>
              setSortOption(event.target.value as 'recent' | 'alphabetical' | 'in-progress')
            }
            className="w-full rounded-md bg-gray-750 border border-gray-700 px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="recent">Most recent</option>
            <option value="alphabetical">Alphabetical</option>
            <option value="in-progress">In progress first</option>
          </select>
        </label>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <LoadingFallback message="Loading games..." />
        ) : error ? (
          <QueryErrorFallback
            error={error}
            title="Failed to load games"
            onRetry={() => refetch()}
          />
        ) : games.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">No games found</p>
            <p className="text-xs mt-1">Run a simulation to generate reports</p>
          </div>
        ) : sortedGames.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">No matching games</p>
            <p className="text-xs mt-1">Try a different search term</p>
          </div>
        ) : (
          <div className="space-y-1">
            {sortedGames.map(game => (
              <motion.button
                key={game.id}
                onClick={() => handleGameSelect(game.id)}
                onMouseEnter={() => handleGameHover(game.id)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedGameId === game.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-750 text-gray-300 hover:bg-gray-700'
                }`}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                <div className="font-medium text-sm truncate">{game.name}</div>
                <div className="flex items-center gap-2 mt-1 text-xs opacity-75">
                  <span>{game.total_days} days</span>
                  <span>•</span>
                  <span className={
                    game.winner === 'FAITHFUL' ? 'text-blue-300' :
                    game.winner === 'TRAITORS' ? 'text-red-300' :
                    'text-gray-400'
                  }>
                    {game.winner === '' || game.winner === 'UNKNOWN' ? 'In Progress' : game.winner}
                  </span>
                </div>
              </motion.button>
            ))}
          </div>
        )}
      </div>

        {/* Stats */}
        {games.length > 0 && (
          <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
            {hasSearch
              ? `${sortedGames.length} of ${games.length} game${
                  games.length !== 1 ? 's' : ''
                } shown`
              : `${games.length} game${games.length !== 1 ? 's' : ''} loaded`}
            {data?.total && data.total > games.length && (
              <span className="ml-1">({data.total} total)</span>
            )}
          </div>
        )}
      </aside>

      {/* Game Runner Modal */}
      <GameRunner isOpen={runnerOpen} onClose={() => setRunnerOpen(false)} />
    </>
  );
}

export default Sidebar;
