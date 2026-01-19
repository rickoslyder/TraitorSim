/**
 * Custom hooks
 */

export {
  useContainerSize,
  useWindowSize,
  useReducedMotion,
  useTrustAnimation,
  usePlaybackTimer,
} from './useContainerSize';

export { usePOVVisibility } from './usePOVVisibility';
export type { POVVisibility } from './usePOVVisibility';

// Voice / HITL hooks
export {
  useAudioCapture,
  float32ToInt16,
  int16ToArrayBuffer,
} from './useAudioCapture';
export type {
  AudioCaptureConfig,
  AudioCaptureState,
  AudioCaptureActions,
  UseAudioCaptureReturn,
} from './useAudioCapture';

export { useAudioPlayback } from './useAudioPlayback';
export type {
  AudioPlaybackConfig,
  AudioPlaybackState,
  AudioPlaybackActions,
  UseAudioPlaybackReturn,
} from './useAudioPlayback';

export {
  useVoiceWebSocket,
  MessageType,
} from './useVoiceWebSocket';
export type {
  SpeakerTurnMessage,
  TranscriptMessage,
  GameStateMessage,
  PhaseChangeMessage,
  ErrorMessage,
  ServerMessage,
  VoiceWebSocketState,
  VoiceWebSocketActions,
  UseVoiceWebSocketReturn,
} from './useVoiceWebSocket';

// Playable game hooks
export { usePlayerSession } from './usePlayerSession';
export type { UsePlayerSessionReturn } from './usePlayerSession';

export { useLobbyWebSocket } from './useLobbyWebSocket';
export type {
  UseLobbyWebSocketReturn,
  UseLobbyWebSocketOptions,
} from './useLobbyWebSocket';

export { useLiveGameWebSocket } from './useLiveGameWebSocket';
export type {
  UseLiveGameWebSocketReturn,
  UseLiveGameWebSocketOptions,
} from './useLiveGameWebSocket';

export { useCountdown } from './useCountdown';
export type { UseCountdownReturn, UseCountdownOptions } from './useCountdown';
