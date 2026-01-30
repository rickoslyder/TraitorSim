import { useEffect, useRef, useState, useCallback } from 'react';

export interface GameState {
  game_id: string;
  day: number;
  phase: string | null;
  prize_pot: number;
  players: Array<{
    id: string;
    name: string;
    alive: boolean;
    role?: string;
  }>;
  my_player: {
    id: string;
    name: string;
    role: string | null;
    alive: boolean;
    has_shield: boolean;
  };
}

export interface DecisionRequest {
  decision_id: string;
  decision_type: string;
  context: Record<string, unknown>;
  timeout_seconds: number;
  deadline: string;
}

export interface GameEvent {
  type: string;
  event?: string;
  data?: Record<string, unknown>;
}

export interface UseLiveGameWebSocketReturn {
  connected: boolean;
  gameState: GameState | null;
  pendingDecision: DecisionRequest | null;
  events: GameEvent[];
  submitDecision: (decisionId: string, result: unknown) => void;
  error: string | null;
}

export function useLiveGameWebSocket(
  gameId: string | null,
  token: string | null
): UseLiveGameWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [pendingDecision, setPendingDecision] = useState<DecisionRequest | null>(null);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gameId || !token) {
      return;
    }

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/game/${gameId}?token=${token}`;

    console.log('[WebSocket] Connecting to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('[WebSocket] Received:', message);

        switch (message.type) {
          case 'game_state':
            setGameState(message.data);
            break;

          case 'decision_request':
            setPendingDecision({
              decision_id: message.decision_id,
              decision_type: message.decision_type,
              context: message.context,
              timeout_seconds: message.timeout_seconds,
              deadline: message.deadline,
            });
            break;

          case 'decision_made':
            // Clear pending decision if it matches
            setPendingDecision((current) => {
              if (current?.decision_id === message.decision_id) {
                return null;
              }
              return current;
            });
            break;

          case 'action_ack':
            // Decision was acknowledged, clear it
            setPendingDecision((current) => {
              if (current?.decision_id === message.decision_id) {
                return null;
              }
              return current;
            });
            break;

          case 'game_event':
            setEvents((prev) => [...prev, message]);
            // Also update game state if event contains state changes
            if (message.event === 'phase_started' || message.event === 'phase_ended') {
              // Request fresh state
              ws.send(JSON.stringify({ type: 'get_state' }));
            }
            break;

          case 'waiting':
            console.log('[WebSocket] Waiting:', message.message);
            break;

          case 'pong':
            // Heartbeat response
            break;

          case 'error':
            console.error('[WebSocket] Error:', message.error);
            setError(message.error);
            break;

          default:
            console.log('[WebSocket] Unknown message type:', message.type);
        }
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err);
      }
    };

    ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected:', event.code, event.reason);
      setConnected(false);
      if (event.code !== 1000 && event.code !== 1001) {
        setError(`Connection closed: ${event.reason || 'Unknown error'}`);
      }
    };

    ws.onerror = (err) => {
      console.error('[WebSocket] Error:', err);
      setError('WebSocket error occurred');
    };

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'Component unmounted');
      }
    };
  }, [gameId, token]);

  const submitDecision = useCallback((decisionId: string, result: unknown) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error('[WebSocket] Cannot submit: not connected');
      return;
    }

    ws.send(
      JSON.stringify({
        type: 'action',
        data: {
          decision_id: decisionId,
          result,
        },
      })
    );
  }, []);

  return {
    connected,
    gameState,
    pendingDecision,
    events,
    submitDecision,
    error,
  };
}
