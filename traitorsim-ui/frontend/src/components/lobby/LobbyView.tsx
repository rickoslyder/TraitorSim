/**
 * Main lobby view component.
 * Displays the waiting room before a game starts.
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSessionStore } from '../../stores/sessionStore';
import { useLobbyWebSocket } from '../../hooks/useLobbyWebSocket';
import { lobbyApi } from '../../api/lobby';
import { PlayerSlot } from './PlayerSlot';
import { GameConfigPanel } from './GameConfigPanel';
import { InviteLink } from './InviteLink';
import { ReadyButton } from './ReadyButton';
import type { LobbyConfig, LobbyState } from '../../types/lobby';

interface LobbyViewProps {
  gameId: string;
  initialState?: LobbyState;
}

export function LobbyView({ gameId, initialState }: LobbyViewProps) {
  const navigate = useNavigate();
  const { session, clearSession } = useSessionStore();

  const [isStarting, setIsStarting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Initialize lobby state with API data, then switch to WebSocket updates
  const [lobbyStateFromApi, setLobbyStateFromApi] = useState<LobbyState | null>(
    initialState ?? null
  );

  // Fetch initial state if not provided
  useEffect(() => {
    if (!initialState && gameId) {
      lobbyApi.get(gameId).then(setLobbyStateFromApi).catch(console.error);
    }
  }, [gameId, initialState]);

  // WebSocket connection for real-time updates
  const {
    isConnected,
    lobbyState: wsLobbyState,
    connectionError,
    gameStarting,
    sendReady,
    reconnect,
  } = useLobbyWebSocket(gameId, {
    onGameStart: (msg) => {
      // Navigate to game when it starts
      navigate(`/game/${msg.game_id}`);
    },
    onKicked: (reason) => {
      clearSession();
      navigate('/', { state: { kicked: true, reason } });
    },
  });

  // Use WebSocket state if available, otherwise API state
  const lobbyState = wsLobbyState ?? lobbyStateFromApi;

  const isHost = session?.is_host ?? false;
  const currentSlot = lobbyState?.slots.find(
    (slot) => slot.player_id === session?.player_id
  );
  const isReady = currentSlot?.is_ready ?? false;

  // Calculate if game can start
  const canStart =
    lobbyState &&
    isHost &&
    lobbyState.player_count >= 2 &&
    (lobbyState.ready_count === lobbyState.player_count ||
      lobbyState.config.ai_fill_empty_slots);

  // Handle ready toggle
  const handleReadyToggle = useCallback(
    (ready: boolean) => {
      if (session) {
        sendReady(ready);
        // Also update via API for immediate feedback
        lobbyApi.setReady(gameId, session.token, ready).catch(console.error);
      }
    },
    [session, gameId, sendReady]
  );

  // Handle config update
  const handleConfigUpdate = useCallback(
    async (config: LobbyConfig) => {
      if (!session || !isHost) return;

      setActionError(null);
      try {
        await lobbyApi.updateConfig(gameId, session.token, config);
      } catch (error) {
        setActionError(
          error instanceof Error ? error.message : 'Failed to update config'
        );
      }
    },
    [session, gameId, isHost]
  );

  // Handle kick player
  const handleKickPlayer = useCallback(
    async (playerId: string) => {
      if (!session || !isHost) return;

      setActionError(null);
      try {
        await lobbyApi.kickPlayer(gameId, session.token, playerId);
      } catch (error) {
        setActionError(
          error instanceof Error ? error.message : 'Failed to kick player'
        );
      }
    },
    [session, gameId, isHost]
  );

  // Handle leave lobby
  const handleLeave = useCallback(async () => {
    if (!session) return;

    try {
      await lobbyApi.leave(gameId, session.token);
    } catch (error) {
      console.warn('Error leaving lobby:', error);
    } finally {
      clearSession();
      navigate('/');
    }
  }, [session, gameId, clearSession, navigate]);

  // Handle start game
  const handleStartGame = useCallback(async () => {
    if (!session || !isHost || !canStart) return;

    setIsStarting(true);
    setActionError(null);

    try {
      await lobbyApi.startGame(gameId, session.token);
      // WebSocket will handle navigation when GAME_STARTING is received
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : 'Failed to start game'
      );
      setIsStarting(false);
    }
  }, [session, gameId, isHost, canStart]);

  // Show loading state
  if (!lobbyState) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading lobby...</p>
        </div>
      </div>
    );
  }

  // Show countdown if game is starting
  if (gameStarting) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Game Starting!</h2>
          <div className="text-6xl font-bold text-blue-400 mb-4">
            {gameStarting.countdown_seconds}
          </div>
          <p className="text-gray-400">Get ready...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{lobbyState.name}</h1>
          <p className="text-gray-400">
            {lobbyState.player_count} / {lobbyState.config.total_players} players
          </p>
        </div>
        <InviteLink gameId={gameId} inviteCode={lobbyState.invite_code} />
      </header>

      {/* Connection status */}
      {connectionError && (
        <div className="flex items-center justify-between p-3 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
          <span className="text-yellow-400 text-sm">{connectionError}</span>
          <button
            onClick={reconnect}
            className="px-3 py-1 text-sm font-medium text-yellow-400 hover:text-yellow-300"
          >
            Reconnect
          </button>
        </div>
      )}

      {/* Action error */}
      {actionError && (
        <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {actionError}
        </div>
      )}

      {/* Player slots */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-200">Players</h2>
        <div className="grid gap-2">
          {lobbyState.slots.map((slot) => (
            <PlayerSlot
              key={slot.slot_index}
              slot={slot}
              isCurrentPlayer={slot.player_id === session?.player_id}
              canKick={isHost && slot.player_id !== session?.player_id}
              onKick={() => slot.player_id && handleKickPlayer(slot.player_id)}
            />
          ))}
        </div>
      </section>

      {/* Game configuration */}
      <section>
        <GameConfigPanel
          config={lobbyState.config}
          canEdit={isHost}
          onUpdate={handleConfigUpdate}
        />
      </section>

      {/* Action buttons */}
      <footer className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 border-t border-gray-700">
        <button
          onClick={handleLeave}
          className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
        >
          Leave Lobby
        </button>

        <div className="flex items-center gap-4">
          <ReadyButton
            isReady={isReady}
            isConnected={isConnected}
            onToggle={handleReadyToggle}
          />

          {isHost && (
            <button
              onClick={handleStartGame}
              disabled={!canStart || isStarting}
              className={`
                flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-lg
                transition-transform transform
                ${
                  canStart && !isStarting
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-lg shadow-purple-600/25 hover:scale-105 active:scale-95'
                    : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                }
              `}
            >
              {isStarting ? (
                <>
                  <svg
                    className="w-5 h-5 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Starting…
                </>
              ) : (
                <>Start Game</>
              )}
            </button>
          )}
        </div>
      </footer>

      {/* Host instructions */}
      {isHost && !canStart && (
        <p className="text-center text-sm text-gray-500">
          {lobbyState.player_count < 2
            ? 'Need at least 2 players to start'
            : lobbyState.ready_count < lobbyState.player_count &&
              !lobbyState.config.ai_fill_empty_slots
            ? 'Waiting for all players to be ready'
            : ''}
        </p>
      )}
    </div>
  );
}
