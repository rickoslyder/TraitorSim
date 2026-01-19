/**
 * Main live game view component.
 * Container for all gameplay UI elements.
 */

import { useState } from 'react';
import { useLiveGameWebSocket } from '../../hooks/useLiveGameWebSocket';
import { PhaseIndicator } from './PhaseIndicator';
import { ActionPanel } from './ActionPanel';
import { PlayerList } from './PlayerList';
import { EventNotification } from './EventNotification';
import { ChatPanel } from './ChatPanel';

interface LiveGameViewProps {
  gameId: string;
}

export function LiveGameView({ gameId }: LiveGameViewProps) {
  const [showChat, setShowChat] = useState(true);

  const {
    isConnected,
    gameState,
    pendingDecision,
    events,
    chatMessages,
    connectionError,
    submitAction,
    sendChat,
    reconnect,
  } = useLiveGameWebSocket(gameId);

  // Loading state
  if (!gameState) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-400">Connecting to game…</p>
          {connectionError && (
            <div className="text-red-400 text-sm">{connectionError}</div>
          )}
        </div>
      </div>
    );
  }

  // Game completed
  if (gameState.status === 'completed') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-6">
        <div className="max-w-md text-center space-y-6">
          <div className="text-6xl">🏆</div>
          <h1 className="text-3xl font-bold text-white">Game Over!</h1>
          <p className="text-gray-400">
            The game has ended. Check the analysis dashboard for full results.
          </p>
          <a
            href="/analysis"
            className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
          >
            View Analysis
          </a>
        </div>
      </div>
    );
  }

  const isTraitor = gameState.my_role === 'TRAITOR';
  const isAlive = gameState.my_alive;

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Connection status bar */}
      {!isConnected && (
        <div className="bg-yellow-500/20 border-b border-yellow-500/50 px-4 py-2 flex items-center justify-between">
          <span className="text-yellow-400 text-sm">
            {connectionError || 'Reconnecting…'}
          </span>
          <button
            onClick={reconnect}
            className="text-yellow-400 hover:text-yellow-300 text-sm font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Header - Phase and game info */}
      <header className="p-4 border-b border-gray-700">
        <PhaseIndicator
          day={gameState.day}
          phase={gameState.phase}
          prizePot={gameState.prize_pot}
          aliveCount={gameState.alive_count}
          totalPlayers={gameState.players.length}
        />
      </header>

      {/* Role badge */}
      <div className="flex items-center justify-center gap-4 py-3 bg-gray-800/50 border-b border-gray-700">
        <div
          className={`
            flex items-center gap-2 px-4 py-2 rounded-full font-medium
            ${isTraitor ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}
          `}
        >
          {isTraitor ? (
            <>
              <span>🗡️</span>
              <span>You are a TRAITOR</span>
            </>
          ) : (
            <>
              <span>💙</span>
              <span>You are FAITHFUL</span>
            </>
          )}
        </div>
        {!isAlive && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-gray-600/50 text-gray-400 font-medium">
            <span>💀</span>
            <span>Eliminated</span>
          </div>
        )}
      </div>

      {/* Main content */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left side - Action panel and players */}
        <div className="flex-1 flex flex-col overflow-auto p-4 space-y-4">
          {/* Action panel - only if alive */}
          {isAlive && (
            <ActionPanel
              pendingDecision={pendingDecision}
              gameState={gameState}
              onSubmit={submitAction}
            />
          )}

          {/* Spectator message if dead */}
          {!isAlive && (
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <div className="text-4xl mb-3">👻</div>
              <h3 className="text-lg font-semibold text-white mb-2">
                You are now a spectator
              </h3>
              <p className="text-gray-400">
                Watch as the game unfolds. Your role has been revealed to all players.
              </p>
            </div>
          )}

          {/* Player list */}
          <PlayerList
            players={gameState.players}
            myPlayerId={gameState.my_player_id}
            myRole={gameState.my_role}
            fellowTraitors={gameState.fellow_traitors}
          />

          {/* Recent events */}
          {events.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Recent Events
              </h3>
              <div className="space-y-2">
                {events.slice(0, 5).map((event, i) => (
                  <EventNotification key={i} event={event} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right side - Chat */}
        <div
          className={`
            lg:w-80 border-t lg:border-t-0 lg:border-l border-gray-700
            ${showChat ? '' : 'hidden lg:block'}
          `}
        >
          <ChatPanel
            messages={chatMessages}
            onSend={sendChat}
            isTraitor={isTraitor}
            disabled={!isConnected}
          />
        </div>
      </main>

      {/* Mobile chat toggle */}
      <button
        onClick={() => setShowChat(!showChat)}
        className="lg:hidden fixed bottom-4 right-4 w-14 h-14 bg-blue-600 hover:bg-blue-500 text-white rounded-full shadow-lg flex items-center justify-center"
      >
        <span className="text-xl">{showChat ? '✕' : '💬'}</span>
      </button>
    </div>
  );
}
