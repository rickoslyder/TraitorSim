/**
 * Sidebar - Game list and selection
 *
 * Uses TanStack Query for loading games list and Zustand for selection state.
 * Collapsible on mobile with overlay backdrop.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../../stores/gameStore';
import { useGames, usePrefetchGame } from '../../api/hooks';
import { LoadingFallback, QueryErrorFallback } from '../ErrorBoundary';

export function Sidebar() {
  // UI state from Zustand
  const { selectedGameId, selectGame, sidebarOpen, setSidebarOpen } = useGameStore();

  // Server state from TanStack Query
  const { data, isLoading, error, refetch } = useGames();
  const prefetchGame = usePrefetchGame();

  const games = data?.games || [];

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
        ) : (
          <div className="space-y-1">
            {games.map(game => (
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
                  <span className={game.winner === 'FAITHFUL' ? 'text-blue-300' : 'text-red-300'}>
                    {game.winner}
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
            {games.length} game{games.length !== 1 ? 's' : ''} loaded
            {data?.total && data.total > games.length && (
              <span className="ml-1">({data.total} total)</span>
            )}
          </div>
        )}
      </aside>
    </>
  );
}

export default Sidebar;
