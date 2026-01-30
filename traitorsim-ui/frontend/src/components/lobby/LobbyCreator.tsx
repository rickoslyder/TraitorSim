import { useState } from 'react';
import './LobbyCreator.css';

interface LobbyCreatorProps {
  onLobbyCreated: (gameId: string, token: string, playerId: string) => void;
}

export function LobbyCreator({ onLobbyCreated }: LobbyCreatorProps) {
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [maxPlayers, setMaxPlayers] = useState(6);
  const [numTraitors, setNumTraitors] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/lobby/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name || 'My Game',
          host_display_name: displayName || 'Host',
          max_players: maxPlayers,
          num_traitors: numTraitors,
          rule_set: 'uk',
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to create lobby');
      }

      const data = await response.json();
      onLobbyCreated(data.game_id, data.token, data.player_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lobby-creator">
      <h2>Create New Game</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Game Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My TraitorSim Game"
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

        <div className="form-row">
          <div className="form-group">
            <label>Players</label>
            <input
              type="number"
              min={4}
              max={12}
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(Number(e.target.value))}
            />
          </div>

          <div className="form-group">
            <label>Traitors</label>
            <input
              type="number"
              min={1}
              max={Math.floor(maxPlayers / 3)}
              value={numTraitors}
              onChange={(e) => setNumTraitors(Number(e.target.value))}
            />
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create Game'}
        </button>
      </form>
    </div>
  );
}
