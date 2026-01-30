import { useState } from 'react';
import './LobbyJoiner.css';

interface LobbyJoinerProps {
  onJoined: (gameId: string, token: string, playerId: string) => void;
}

export function LobbyJoiner({ onJoined }: LobbyJoinerProps) {
  const [gameId, setGameId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/lobby/${gameId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: displayName || 'Player',
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to join lobby');
      }

      const data = await response.json();
      onJoined(data.game_id, data.token, data.player_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lobby-joiner">
      <h2>Join Game</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Game ID</label>
          <input
            type="text"
            value={gameId}
            onChange={(e) => setGameId(e.target.value)}
            placeholder="Enter game ID"
            required
          />
        </div>

        <div className="form-group">
          <label>Your Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Enter your name"
            required
          />
        </div>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={loading}>
          {loading ? 'Joining...' : 'Join Game'}
        </button>
      </form>
    </div>
  );
}
