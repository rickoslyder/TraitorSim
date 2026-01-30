import { useLiveGameWebSocket } from '../../hooks/useLiveGameWebSocket';
import { DecisionModal } from './DecisionModal';
import './LiveGame.css';

interface LiveGameProps {
  gameId: string;
  token: string;
  playerId: string;
}

export function LiveGame({ gameId, token, playerId }: LiveGameProps) {
  const { connected, gameState, pendingDecision, events, submitDecision, error } =
    useLiveGameWebSocket(gameId, token);

  if (error) {
    return (
      <div className="live-game error">
        <h2>Connection Error</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Reconnect</button>
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="live-game connecting">
        <div className="spinner"></div>
        <p>Connecting to game...</p>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="live-game loading">
        <div className="spinner"></div>
        <p>Loading game state...</p>
      </div>
    );
  }

  return (
    <div className="live-game">
      {/* Header */}
      <header className="game-header">
        <div className="game-info">
          <h2>Day {gameState.day}</h2>
          <span className="phase">{gameState.phase || 'Waiting'}</span>
        </div>
        <div className="prize-pot">£{gameState.prize_pot.toLocaleString()}</div>
        <div className={`connection-status ${connected ? 'connected' : ''}`}>
          {connected ? '● Live' : '○ Disconnected'}
        </div>
      </header>

      {/* Player info */}
      <div className="my-player">
        <h3>You: {gameState.my_player.name}</h3>
        <div className="my-status">
          <span className={`role ${gameState.my_player.role || ''}`}>
            {gameState.my_player.role || 'Unknown'}
          </span>
          {gameState.my_player.alive ? (
            <span className="alive">● Alive</span>
          ) : (
            <span className="dead">✗ Eliminated</span>
          )}
          {gameState.my_player.has_shield && (
            <span className="shield">🛡️ Shield</span>
          )}
        </div>
      </div>

      {/* Players list */}
      <div className="players-grid">
        <h3>Players</h3>
        <div className="players-list">
          {gameState.players.map((player) => (
            <div
              key={player.id}
              className={`player-card ${player.alive ? 'alive' : 'dead'} ${
                player.id === playerId ? 'me' : ''
              }`}
            >
              <span className="player-name">{player.name}</span>
              {player.role && <span className="player-role">{player.role}</span>}
              {!player.alive && <span className="eliminated">✗</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Events log */}
      <div className="events-log">
        <h3>Game Log</h3>
        <div className="events-list">
          {events.slice(-10).map((event, i) => (
            <div key={i} className={`event ${event.event || ''}`}>
              {event.type === 'game_event' && event.event === 'banishment' && (
                <span>
                  ☠️ {event.data?.player_name} was banished (Role: {event.data?.role})
                </span>
              )}
              {event.type === 'game_event' && event.event === 'murder' && (
                <span>
                  🗡️ {event.data?.victim_name} was murdered
                </span>
              )}
              {event.type === 'game_event' && event.event === 'phase_started' && (
                <span>
                  📅 Day {gameState.day} - {event.data?.phase} phase started
                </span>
              )}
              {event.type === 'game_event' && event.event === 'player_deciding' && (
                <span>⏳ {event.data?.player_id} is deciding...</span>
              )}
            </div>
          ))}
          {events.length === 0 && <p className="no-events">Waiting for events...</p>}
        </div>
      </div>

      {/* Pending decision modal */}
      {pendingDecision && (
        <DecisionModal
          decisionId={pendingDecision.decision_id}
          decisionType={pendingDecision.decision_type}
          context={pendingDecision.context}
          timeoutSeconds={pendingDecision.timeout_seconds}
          deadline={pendingDecision.deadline}
          onSubmit={submitDecision}
        />
      )}
    </div>
  );
}
