/**
 * Voice WebSocket Hook - Bidirectional audio streaming
 *
 * Connects to the HITL WebSocket server for:
 * - Binary audio frame streaming (capture → server)
 * - Binary audio frame receiving (server → playback)
 * - JSON control messages (game state, speaker turns, transcripts)
 *
 * Message protocol matches hitl_server.py MessageType enum.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// Types (mirrors hitl_server.py MessageType)
// ============================================================================

export enum MessageType {
  // Client → Server
  AUDIO_CHUNK = 'audio_chunk',
  HUMAN_READY = 'human_ready',
  INTENT_OVERRIDE = 'intent_override',
  SKIP_SPEAKER = 'skip_speaker',

  // Server → Client
  AUDIO_STREAM = 'audio_stream',
  SPEAKER_TURN = 'speaker_turn',
  TRANSCRIPT = 'transcript',
  GAME_STATE = 'game_state',
  PHASE_CHANGE = 'phase_change',
  ERROR = 'error',

  // Bidirectional
  PING = 'ping',
  PONG = 'pong',
}

export interface SpeakerTurnMessage {
  type: MessageType.SPEAKER_TURN;
  speaker_id: string;
  speaker_name: string;
  priority: string;
  can_interrupt: boolean;
  estimated_duration_ms?: number;
}

export interface TranscriptMessage {
  type: MessageType.TRANSCRIPT;
  speaker_id: string;
  speaker_name: string;
  text: string;
  is_final: boolean;
  confidence?: number;
}

export interface GameStateMessage {
  type: MessageType.GAME_STATE;
  day: number;
  phase: string;
  substate?: string;
  alive_players: string[];
  current_speaker?: string;
  time_remaining_ms?: number;
}

export interface PhaseChangeMessage {
  type: MessageType.PHASE_CHANGE;
  previous_phase: string;
  new_phase: string;
  day: number;
}

export interface ErrorMessage {
  type: MessageType.ERROR;
  code: string;
  message: string;
}

export interface PongMessage {
  type: MessageType.PONG;
}

export type ServerMessage =
  | PongMessage
  | SpeakerTurnMessage
  | TranscriptMessage
  | GameStateMessage
  | PhaseChangeMessage
  | ErrorMessage;

// ============================================================================
// Connection State
// ============================================================================

export interface VoiceWebSocketState {
  /** WebSocket connection status */
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  /** Current game state from server */
  gameState: GameStateMessage | null;
  /** Current speaker info */
  currentSpeaker: SpeakerTurnMessage | null;
  /** Last transcript received */
  lastTranscript: TranscriptMessage | null;
  /** Connection error if any */
  error: string | null;
  /** Round-trip latency in ms */
  latencyMs: number | null;
}

export interface VoiceWebSocketActions {
  /** Connect to WebSocket server */
  connect: (url: string, sessionId?: string) => void;
  /** Disconnect from server */
  disconnect: () => void;
  /** Send binary audio chunk */
  sendAudio: (data: ArrayBuffer) => void;
  /** Signal human is ready to speak */
  sendHumanReady: () => void;
  /** Override detected intent */
  sendIntentOverride: (intent: string, target?: string) => void;
  /** Skip current speaker */
  sendSkipSpeaker: () => void;
  /** Set callback for audio data received */
  onAudioReceived: (callback: (data: ArrayBuffer, speaker: string) => void) => void;
  /** Set callback for transcript received */
  onTranscriptReceived: (callback: (transcript: TranscriptMessage) => void) => void;
  /** Set callback for game state changes */
  onGameStateChanged: (callback: (state: GameStateMessage) => void) => void;
  /** Set callback for speaker turn changes */
  onSpeakerTurn: (callback: (speaker: SpeakerTurnMessage) => void) => void;
}

export type UseVoiceWebSocketReturn = [VoiceWebSocketState, VoiceWebSocketActions];

// ============================================================================
// Hook Implementation
// ============================================================================

export function useVoiceWebSocket(): UseVoiceWebSocketReturn {
  // State
  const [status, setStatus] = useState<VoiceWebSocketState['status']>('disconnected');
  const [gameState, setGameState] = useState<GameStateMessage | null>(null);
  const [currentSpeaker, setCurrentSpeaker] = useState<SpeakerTurnMessage | null>(null);
  const [lastTranscript, setLastTranscript] = useState<TranscriptMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pingTimestampRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Callbacks
  const onAudioReceivedRef = useRef<((data: ArrayBuffer, speaker: string) => void) | null>(null);
  const onTranscriptReceivedRef = useRef<((transcript: TranscriptMessage) => void) | null>(null);
  const onGameStateChangedRef = useRef<((state: GameStateMessage) => void) | null>(null);
  const onSpeakerTurnRef = useRef<((speaker: SpeakerTurnMessage) => void) | null>(null);

  // Current speaker for audio association
  const currentSpeakerNameRef = useRef<string>('Unknown');

  // Cleanup function
  const cleanup = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    // Binary data = audio
    if (event.data instanceof ArrayBuffer) {
      if (onAudioReceivedRef.current) {
        onAudioReceivedRef.current(event.data, currentSpeakerNameRef.current);
      }
      return;
    }

    // Blob = audio (some WebSocket implementations)
    if (event.data instanceof Blob) {
      event.data.arrayBuffer().then((buffer) => {
        if (onAudioReceivedRef.current) {
          onAudioReceivedRef.current(buffer, currentSpeakerNameRef.current);
        }
      });
      return;
    }

    // Text = JSON control message
    try {
      const message = JSON.parse(event.data) as ServerMessage;

      switch (message.type) {
        case MessageType.PONG:
          // Calculate latency
          if (pingTimestampRef.current > 0) {
            setLatencyMs(Date.now() - pingTimestampRef.current);
          }
          break;

        case MessageType.SPEAKER_TURN:
          setCurrentSpeaker(message);
          currentSpeakerNameRef.current = message.speaker_name;
          if (onSpeakerTurnRef.current) {
            onSpeakerTurnRef.current(message);
          }
          break;

        case MessageType.TRANSCRIPT:
          setLastTranscript(message);
          if (onTranscriptReceivedRef.current) {
            onTranscriptReceivedRef.current(message);
          }
          break;

        case MessageType.GAME_STATE:
          setGameState(message);
          if (onGameStateChangedRef.current) {
            onGameStateChangedRef.current(message);
          }
          break;

        case MessageType.PHASE_CHANGE:
          // Update game state with new phase
          setGameState((prev) => prev ? {
            ...prev,
            phase: message.new_phase,
            day: message.day,
          } : null);
          break;

        case MessageType.ERROR:
          setError(message.message);
          break;
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, []);

  // Connect to WebSocket server
  const connect = useCallback((url: string, sessionId?: string) => {
    cleanup();
    setStatus('connecting');
    setError(null);

    // Build URL with session ID if provided
    let wsUrl = url;
    if (sessionId) {
      const separator = url.includes('?') ? '&' : '?';
      wsUrl = `${url}${separator}session_id=${sessionId}`;
    }

    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setStatus('connected');
        setError(null);

        // Start ping interval for latency tracking
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            pingTimestampRef.current = Date.now();
            ws.send(JSON.stringify({ type: MessageType.PING }));
          }
        }, 5000);
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        setError('WebSocket connection error');
        setStatus('error');
      };

      ws.onclose = (event) => {
        setStatus('disconnected');
        cleanup();

        // Log close reason
        if (event.code !== 1000) {
          console.warn(`WebSocket closed: ${event.code} ${event.reason}`);
        }
      };

      wsRef.current = ws;

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect';
      setError(message);
      setStatus('error');
    }
  }, [cleanup, handleMessage]);

  // Disconnect
  const disconnect = useCallback(() => {
    cleanup();
    setStatus('disconnected');
  }, [cleanup]);

  // Send binary audio chunk
  const sendAudio = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  // Send human ready signal
  const sendHumanReady = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: MessageType.HUMAN_READY }));
    }
  }, []);

  // Send intent override
  const sendIntentOverride = useCallback((intent: string, target?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: MessageType.INTENT_OVERRIDE,
        intent,
        target,
      }));
    }
  }, []);

  // Send skip speaker
  const sendSkipSpeaker = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: MessageType.SKIP_SPEAKER }));
    }
  }, []);

  // Set callbacks
  const onAudioReceived = useCallback((callback: (data: ArrayBuffer, speaker: string) => void) => {
    onAudioReceivedRef.current = callback;
  }, []);

  const onTranscriptReceived = useCallback((callback: (transcript: TranscriptMessage) => void) => {
    onTranscriptReceivedRef.current = callback;
  }, []);

  const onGameStateChanged = useCallback((callback: (state: GameStateMessage) => void) => {
    onGameStateChangedRef.current = callback;
  }, []);

  const onSpeakerTurn = useCallback((callback: (speaker: SpeakerTurnMessage) => void) => {
    onSpeakerTurnRef.current = callback;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return [
    {
      status,
      gameState,
      currentSpeaker,
      lastTranscript,
      error,
      latencyMs,
    },
    {
      connect,
      disconnect,
      sendAudio,
      sendHumanReady,
      sendIntentOverride,
      sendSkipSpeaker,
      onAudioReceived,
      onTranscriptReceived,
      onGameStateChanged,
      onSpeakerTurn,
    },
  ];
}

export default useVoiceWebSocket;
