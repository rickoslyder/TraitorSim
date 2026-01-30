import { useEffect, useState } from 'react';
import './LobbyView.css';

interface Player {
  player_id: string;
  display_name: string;
  is_host: boolean;
  ready: boolean;
}

interface LobbyData {
  game_id: string;
  name: string;
  host_id: string;
  max_players: number;
  num_traitors: number;
  rule_set: string;
  players: Player[];
  status: string;
}

interface LobbyViewProps {
  gameId: string;
  token: string;
  playerId: string;
  onGameStarted: () => void;
}

export function LobbyView({ gameId, token, playerId, onGameStarted }: LobbyViewProps) {
  const [lobby, setLobby] = useState<LobbyData | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(true);

  const isHost = lobby?.host_id === playerId;

  // Poll for lobby updates
  useEffect(() => {
    if (!polling) return;

    const fetchLobby = async () => {
      try {
        const response = await fetch(`/api/lobby/${gameId}`);
        if (!response.ok) throw new Error('Failed to fetch lobby');
        const data = await response.json();
        setLobby(data);

        // Check if game started
        if (data.status === 'in_progress') {
          setPolling(false);
          onGameStarted();
        }

        // Update ready status
        const me = data.players.find((p: Player) => p.player_id === playerId);
        if (me) {
          setIsReady(me.ready);
        }
      } catch (err) {
        console.error('Failed to fetch lobby:', err);
      }
    };

    fetchLobby();
    const interval = setInterval(fetchLobby, 2000);
    return () => clearInterval(interval);
  }, [gameId, playerId, polling, onGameStarted]);

  const toggleReady = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/lobby/${gameId}/ready?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ready: !isReady }),
      });

      if (!response.ok) throw new Error('Failed to update ready status');
      setIsReady(!isReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const startGame = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/lobby/${gameId}/start?token=${token}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to start game');
      }

      setPolling(false);
      onGameStarted();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (!lobby) {
    return <div className="lobby-view loading">Loading lobby...</div>;
  }

  const allReady = lobby.players.every((p) => p.ready);
  const canStart = isHost && allReady && lobby.players.length >= 4;

  return (
    <div className="lobby-view">
      <h2>{lobby.name}</h2>
      <p className="game-id">Game ID: {lobby.game_id}</p>

      <div className="lobby-config">
        <span>Players: {lobby.players.length}/{lobby.max_players}</span>
        <span>Traitors: {lobby.num_traitors}</span>
        <span>Rules: {lobby.rule_set.toUpperCase()}</span>
      </div>

      <div className="players-list">
        <h3>Players</h3>
        {lobby.players.map((player) => (
          <div
            key={player.player_id}
            className={`player-row ${player.player_id === playerId ? 'me' : ''}`}
          >
            <span className="player-name">
              {player.display_name}
              {player.is_host && <span className="host-badge">HOST</span>}
              {player.player_id === playerId && <span className="me-badge">YOU</span>}
            </span>
            <span className={`ready-status ${player.ready ? 'ready' : ''}`}>
              {player.ready ? '✓ Ready' : '⏳ Not Ready'}
            </span>
          </div>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      <div className="lobby-actions">
        <button onClick={toggleReady} disabled={loading} className={isReady ? 'ready' : ''}>
          {isReady ? 'Not Ready' : 'Ready Up'}
        </button>

        {isHost && (
          <button
            onClick={startGame}
            disabled={loading || !canStart}
            className="start-btn"
          >
            {loading ? 'Starting...' : 'Start Game'}
          </button>
        )}
      </div>

      {isHost && !allReady && (
        <p className="hint">All players must be ready to start</p>
      )}
    </div>
  );
}
