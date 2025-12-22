/**
 * Header - Top navigation bar
 *
 * Uses Zustand for view options and TanStack Query for game data display.
 * Includes hamburger menu for mobile sidebar toggle and theme selector.
 */

import { useGameStore, type Theme } from '../../stores/gameStore';
import { useGame } from '../../api/hooks';

interface HeaderProps {
  onRefreshClick: () => void;
  isRefreshing?: boolean;
}

export function Header({ onRefreshClick, isRefreshing = false }: HeaderProps) {
  // UI state from Zustand
  const {
    selectedGameId,
    showRoles,
    toggleRoleReveal,
    showEliminatedPlayers,
    toggleShowEliminated,
    toggleSidebar,
    theme,
    setTheme,
  } = useGameStore();

  // Server state from TanStack Query
  const { data: currentGame } = useGame(selectedGameId);

  const handleThemeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTheme(e.target.value as Theme);
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left section: Menu button + Logo */}
        <div className="flex items-center gap-3">
          {/* Mobile menu button */}
          <button
            onClick={toggleSidebar}
            className="md:hidden p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Toggle sidebar menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          {/* Logo */}
          <h1 className="text-xl font-bold text-white">
            <span className="text-red-500">Traitor</span>Sim
          </h1>
          {currentGame && (
            <span className="hidden sm:inline text-gray-400 text-sm">
              | {currentGame.name}
            </span>
          )}
        </div>

        {/* Game stats */}
        {currentGame && (
          <div className="hidden md:flex items-center gap-6 text-sm">
            <div className="text-gray-400">
              Days: <span className="text-white font-medium">{currentGame.total_days}</span>
            </div>
            <div className="text-gray-400">
              Prize Pot: <span className="text-green-400 font-medium">
                £{currentGame.prize_pot.toLocaleString()}
              </span>
            </div>
            <div className="text-gray-400">
              Winner: <span className={`font-medium ${
                currentGame.winner === 'FAITHFUL' ? 'text-blue-400' : 'text-red-400'
              }`}>
                {currentGame.winner}
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          {currentGame && (
            <>
              {/* Role reveal toggle */}
              <button
                onClick={toggleRoleReveal}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  showRoles
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                title={showRoles ? 'Hide roles' : 'Reveal roles'}
                aria-label={showRoles ? 'Hide player roles' : 'Show player roles'}
              >
                {showRoles ? '🎭 Hide Roles' : '👁️ Show Roles'}
              </button>

              {/* Show eliminated toggle */}
              <button
                onClick={toggleShowEliminated}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  showEliminatedPlayers
                    ? 'bg-gray-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                aria-label={showEliminatedPlayers ? 'Show all players' : 'Show alive players only'}
              >
                {showEliminatedPlayers ? '💀 Showing All' : '💚 Alive Only'}
              </button>
            </>
          )}

          {/* Theme selector */}
          <select
            value={theme}
            onChange={handleThemeChange}
            className="px-2 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Select theme"
          >
            <option value="dark">🌙 Dark</option>
            <option value="light">☀️ Light</option>
            <option value="system">💻 System</option>
          </select>

          {/* Refresh button */}
          <button
            onClick={onRefreshClick}
            disabled={isRefreshing}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm transition-colors ${
              isRefreshing
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-gray-700 text-white hover:bg-gray-600'
            }`}
            aria-label="Refresh game list"
          >
            <span className={isRefreshing ? 'animate-spin' : ''}>🔄</span>
            <span className="hidden sm:inline">{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
