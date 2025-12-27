/**
 * VoicePanel - Main voice control component for HITL mode
 *
 * Provides:
 * - Microphone control (push-to-talk or toggle)
 * - Connection status indicator
 * - Audio level visualization
 * - Integration with SpeakerIndicator and TranscriptDisplay
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  useAudioCapture,
  useAudioPlayback,
  useVoiceWebSocket,
  float32ToInt16,
  int16ToArrayBuffer,
} from '../../hooks';
import SpeakerIndicator from './SpeakerIndicator';
import TranscriptDisplay from './TranscriptDisplay';
import type { TranscriptMessage } from '../../hooks/useVoiceWebSocket';

// ============================================================================
// Types
// ============================================================================

export interface VoicePanelProps {
  /** WebSocket server URL */
  serverUrl?: string;
  /** Session ID for the HITL session */
  sessionId?: string;
  /** Whether to show transcript panel */
  showTranscript?: boolean;
  /** Push-to-talk mode (hold to speak) vs toggle mode */
  pushToTalk?: boolean;
  /** Callback when connection status changes */
  onConnectionChange?: (connected: boolean) => void;
  /** Callback when game state updates */
  onGameStateUpdate?: (state: {
    day: number;
    phase: string;
    alivePlayers: string[];
  }) => void;
  /** Custom class name */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function VoicePanel({
  serverUrl = 'ws://localhost:8765',
  sessionId,
  showTranscript = true,
  pushToTalk = false,
  onConnectionChange,
  onGameStateUpdate,
  className = '',
}: VoicePanelProps) {
  // Hooks
  const [captureState, captureActions] = useAudioCapture({
    sampleRate: 16000,
    bufferSize: 4096,
  });
  const [playbackState, playbackActions] = useAudioPlayback({
    sampleRate: 16000,
  });
  const [wsState, wsActions] = useVoiceWebSocket();

  // Local state
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [showSettings, setShowSettings] = useState(false);

  // Refs
  const micButtonRef = useRef<HTMLButtonElement>(null);

  // Connect audio capture to WebSocket
  useEffect(() => {
    captureActions.onAudioData((data) => {
      if (!isMuted && wsState.status === 'connected') {
        const int16Data = float32ToInt16(data);
        const buffer = int16ToArrayBuffer(int16Data);
        wsActions.sendAudio(buffer);
      }
    });
  }, [captureActions, wsActions, isMuted, wsState.status]);

  // Connect WebSocket audio to playback
  useEffect(() => {
    wsActions.onAudioReceived((data, speaker) => {
      playbackActions.queueAudio(data, speaker);
    });
  }, [wsActions, playbackActions]);

  // Handle transcript messages
  useEffect(() => {
    wsActions.onTranscriptReceived((transcript) => {
      setTranscripts((prev) => {
        // Replace if same speaker and not final, append if final
        const existing = prev.findIndex(
          (t) => t.speaker_id === transcript.speaker_id && !t.is_final
        );

        if (existing >= 0 && !transcript.is_final) {
          const updated = [...prev];
          updated[existing] = transcript;
          return updated;
        }

        // Keep last 50 transcripts
        return [...prev, transcript].slice(-50);
      });
    });
  }, [wsActions]);

  // Handle game state updates
  useEffect(() => {
    wsActions.onGameStateChanged((state) => {
      onGameStateUpdate?.({
        day: state.day,
        phase: state.phase,
        alivePlayers: state.alive_players,
      });
    });
  }, [wsActions, onGameStateUpdate]);

  // Track connection status
  useEffect(() => {
    const connected = wsState.status === 'connected';
    setIsConnected(connected);
    onConnectionChange?.(connected);
  }, [wsState.status, onConnectionChange]);

  // Handle connect/disconnect
  const handleConnect = useCallback(async () => {
    if (isConnected) {
      wsActions.disconnect();
      captureActions.stopCapture();
      playbackActions.stopPlayback();
    } else {
      // Request mic permission first
      const hasPermission = await captureActions.requestPermission();
      if (hasPermission) {
        wsActions.connect(serverUrl, sessionId);
      }
    }
  }, [
    isConnected,
    serverUrl,
    sessionId,
    wsActions,
    captureActions,
    playbackActions,
  ]);

  // Handle mic toggle
  const handleMicToggle = useCallback(async () => {
    if (isMuted) {
      await captureActions.startCapture();
      setIsMuted(false);
      wsActions.sendHumanReady();
    } else {
      captureActions.stopCapture();
      setIsMuted(true);
    }
  }, [isMuted, captureActions, wsActions]);

  // Push-to-talk handlers
  const handleMicDown = useCallback(async () => {
    if (pushToTalk && isMuted) {
      await captureActions.startCapture();
      setIsMuted(false);
      wsActions.sendHumanReady();
    }
  }, [pushToTalk, isMuted, captureActions, wsActions]);

  const handleMicUp = useCallback(() => {
    if (pushToTalk && !isMuted) {
      captureActions.stopCapture();
      setIsMuted(true);
    }
  }, [pushToTalk, isMuted, captureActions]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Space for push-to-talk when focused on mic button
      if (e.code === 'Space' && document.activeElement === micButtonRef.current) {
        e.preventDefault();
        handleMicDown();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && pushToTalk) {
        handleMicUp();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleMicDown, handleMicUp, pushToTalk]);

  // Status text
  const statusText = {
    disconnected: 'Disconnected',
    connecting: 'Connecting...',
    connected: 'Connected',
    error: wsState.error || 'Connection error',
  }[wsState.status];

  const statusColor = {
    disconnected: 'text-gray-400',
    connecting: 'text-yellow-400',
    connected: 'text-green-400',
    error: 'text-red-400',
  }[wsState.status];

  return (
    <div className={`bg-gray-900 rounded-lg border border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-3">
          {/* Connection indicator */}
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
              }`}
            />
            <span className={`text-sm ${statusColor}`}>{statusText}</span>
          </div>

          {/* Latency */}
          {wsState.latencyMs !== null && isConnected && (
            <span className="text-xs text-gray-500">
              {wsState.latencyMs}ms
            </span>
          )}
        </div>

        {/* Settings button */}
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          aria-label="Voice settings"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>

      {/* Main controls */}
      <div className="p-4 space-y-4">
        {/* Speaker indicator */}
        <SpeakerIndicator
          speakerName={wsState.currentSpeaker?.speaker_name || null}
          isPlaying={playbackState.isPlaying}
          audioLevel={captureState.isCapturing ? captureState.audioLevel : undefined}
          queueDuration={playbackState.queueDuration}
        />

        {/* Control buttons */}
        <div className="flex items-center justify-center gap-4">
          {/* Connect button */}
          <motion.button
            onClick={handleConnect}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              isConnected
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </motion.button>

          {/* Mic button */}
          <motion.button
            ref={micButtonRef}
            onClick={pushToTalk ? undefined : handleMicToggle}
            onMouseDown={handleMicDown}
            onMouseUp={handleMicUp}
            onMouseLeave={handleMicUp}
            onTouchStart={handleMicDown}
            onTouchEnd={handleMicUp}
            disabled={!isConnected}
            whileHover={{ scale: isConnected ? 1.1 : 1 }}
            whileTap={{ scale: isConnected ? 0.9 : 1 }}
            className={`relative w-16 h-16 rounded-full flex items-center justify-center transition-all ${
              !isConnected
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : isMuted
                ? 'bg-gray-600 hover:bg-gray-500 text-white'
                : 'bg-red-500 hover:bg-red-400 text-white'
            }`}
            aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {/* Audio level ring */}
            {captureState.isCapturing && (
              <motion.div
                className="absolute inset-0 rounded-full border-4 border-red-400"
                animate={{
                  scale: 1 + captureState.audioLevel * 0.3,
                  opacity: 0.5 + captureState.audioLevel * 0.5,
                }}
                transition={{ duration: 0.1 }}
              />
            )}

            {/* Mic icon */}
            {isMuted ? (
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 3l18 18"
                />
              </svg>
            ) : (
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                />
              </svg>
            )}
          </motion.button>

          {/* Skip speaker button */}
          <motion.button
            onClick={() => wsActions.sendSkipSpeaker()}
            disabled={!isConnected || !playbackState.isPlaying}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              isConnected && playbackState.isPlaying
                ? 'bg-gray-600 hover:bg-gray-500 text-white'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            Skip
          </motion.button>
        </div>

        {/* Push-to-talk hint */}
        {pushToTalk && isConnected && (
          <p className="text-center text-sm text-gray-500">
            Hold the mic button or press Space to talk
          </p>
        )}

        {/* Error display */}
        <AnimatePresence>
          {(wsState.error || captureState.error || playbackState.error) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-red-900/50 border border-red-700 rounded-lg px-4 py-2"
            >
              <p className="text-sm text-red-300">
                {wsState.error || captureState.error || playbackState.error}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Transcript panel */}
      {showTranscript && (
        <div className="border-t border-gray-700">
          <TranscriptDisplay
            transcripts={transcripts}
            maxHeight={200}
          />
        </div>
      )}

      {/* Settings panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-gray-700 p-4 space-y-3"
          >
            <h4 className="text-sm font-medium text-gray-300">Voice Settings</h4>

            {/* Device info */}
            {captureState.deviceLabel && (
              <div className="text-xs text-gray-500">
                Microphone: {captureState.deviceLabel}
              </div>
            )}

            {/* Push-to-talk toggle would go here */}
            <div className="text-xs text-gray-500">
              Mode: {pushToTalk ? 'Push-to-talk' : 'Toggle'}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default VoicePanel;
