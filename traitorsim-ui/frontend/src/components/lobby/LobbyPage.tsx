import { useState } from 'react';
import { LobbyCreator } from './LobbyCreator';
import { LobbyJoiner } from './LobbyJoiner';
import { LobbyView } from './LobbyView';
import { LiveGameView } from '../game/LiveGameView';
import './LobbyPage.css';

type ViewState = 'menu' | 'create' | 'join' | 'lobby' | 'game';

export function LobbyPage() {
  const [view, setView] = useState<ViewState>('menu');
  const [gameId, setGameId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [playerId, setPlayerId] = useState<string | null>(null);

  const handleLobbyCreated = (gId: string, tok: string, pId: string) => {
    setGameId(gId);
    setToken(tok);
    setPlayerId(pId);
    setView('lobby');
  };

  const handleJoined = (gId: string, tok: string, pId: string) => {
    setGameId(gId);
    setToken(tok);
    setPlayerId(pId);
    setView('lobby');
  };

  const handleGameStarted = () => {
    setView('game');
  };

  return (
    <div className="lobby-page">
      {view === 'menu' && (
        <div className="lobby-menu">
          <h1>TraitorSim</h1>
          <p className="tagline">The Traitors - Play with Friends</p>
          <div className="menu-buttons">
            <button onClick={() => setView('create')} className="primary">
              Create Game
            </button>
            <button onClick={() => setView('join')}>
              Join Game
            </button>
          </div>
        </div>
      )}

      {view === 'create' && (
        <>
          <button className="back-btn" onClick={() => setView('menu')}>
            ← Back
          </button>
          <LobbyCreator onLobbyCreated={handleLobbyCreated} />
        </>
      )}

      {view === 'join' && (
        <>
          <button className="back-btn" onClick={() => setView('menu')}>
            ← Back
          </button>
          <LobbyJoiner onJoined={handleJoined} />
        </>
      )}

      {view === 'lobby' && gameId && token && playerId && (
        <LobbyView
          gameId={gameId}
          token={token}
          playerId={playerId}
          onGameStarted={handleGameStarted}
        />
      )}

      {view === 'game' && gameId && (
        <LiveGameView
          gameId={gameId}
        />
      )}
    </div>
  );
}
