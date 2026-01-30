import { useEffect, useRef, useState, useCallback } from 'react';
import type { LiveGameState, PendingDecision, GameEvent, ChatMessage, PlayerAction } from '../types/live';

export interface UseLiveGameWebSocketReturn {
  isConnected: boolean;
  gameState: LiveGameState | null;
  pendingDecision: PendingDecision | null;
  events: GameEvent[];
  chatMessages: ChatMessage[];
  connectionError: string | null;
  submitAction: (action: PlayerAction) => void;
  sendChat: (message: string, channel?: string) => void;
  reconnect: () => void;
}

export function useLiveGameWebSocket(gameId: string): UseLiveGameWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [gameState, setGameState] = useState<LiveGameState | null>(null);
  const [pendingDecision, setPendingDecision] = useState<PendingDecision | null>(null);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const connect = useCallback(() => {
    if (!gameId) return;

    // Get token from URL or session storage
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token') || sessionStorage.getItem(`game_${gameId}_token`);

    if (!token) {
      setConnectionError('No session token found');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/game/${gameId}?token=${token}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setConnectionError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'game_state':
            setGameState(message.data);
            break;

          case 'decision_request':
            setPendingDecision({
              id: message.decision_id,
              decision_type: message.decision_type,
              playerId: '', // Will be filled from context
              timeout: message.timeout_seconds,
              timeout_seconds: message.timeout_seconds,
              deadline: message.deadline,
              context: message.context,
            });
            break;

          case 'decision_made':
            setPendingDecision(null);
            break;

          case 'game_event':
            if (message.event) {
              setEvents((prev) => [...prev, message.data]);
            }
            break;

          case 'chat':
            if (message.message) {
              setChatMessages((prev) => [...prev, message.message]);
            }
            break;

          case 'error':
            setConnectionError(message.error);
            break;
        }
      } catch (err) {
        console.error('Failed to parse message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setConnectionError('WebSocket error');
    };
  }, [gameId]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const submitAction = useCallback((action: PlayerAction) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(
      JSON.stringify({
        type: 'action',
        data: action,
      })
    );
  }, []);

  const sendChat = useCallback((message: string, channel = 'public') => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(
      JSON.stringify({
        type: 'chat',
        data: { message, channel },
      })
    );
  }, []);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    connect();
  }, [connect]);

  return {
    isConnected,
    gameState,
    pendingDecision,
    events,
    chatMessages,
    connectionError,
    submitAction,
    sendChat,
    reconnect,
  };
}
