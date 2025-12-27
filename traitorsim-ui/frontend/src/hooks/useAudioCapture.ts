/**
 * Audio Capture Hook - WebRTC getUserMedia integration
 *
 * Provides browser microphone capture with:
 * - Permission request handling
 * - Audio level metering for VU visualization
 * - Configurable sample rate and buffer size
 * - Automatic cleanup on unmount
 *
 * Works with the HITL WebSocket server for real-time voice input.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface AudioCaptureConfig {
  /** Sample rate in Hz (default: 16000 for speech recognition) */
  sampleRate?: number;
  /** Buffer size in samples (default: 4096) */
  bufferSize?: number;
  /** Enable echo cancellation (default: true) */
  echoCancellation?: boolean;
  /** Enable noise suppression (default: true) */
  noiseSuppression?: boolean;
  /** Enable automatic gain control (default: true) */
  autoGainControl?: boolean;
}

export interface AudioCaptureState {
  /** Whether we have microphone permission */
  hasPermission: boolean;
  /** Whether microphone is actively capturing */
  isCapturing: boolean;
  /** Whether permission request is pending */
  isPending: boolean;
  /** Current audio level (0-1 for VU meter) */
  audioLevel: number;
  /** Any error that occurred */
  error: string | null;
  /** Device label if available */
  deviceLabel: string | null;
}

export interface AudioCaptureActions {
  /** Request microphone permission */
  requestPermission: () => Promise<boolean>;
  /** Start capturing audio */
  startCapture: () => Promise<void>;
  /** Stop capturing audio */
  stopCapture: () => void;
  /** Set callback for audio data chunks */
  onAudioData: (callback: (data: Float32Array) => void) => void;
}

export type UseAudioCaptureReturn = [AudioCaptureState, AudioCaptureActions];

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_CONFIG: Required<AudioCaptureConfig> = {
  sampleRate: 16000,     // Optimal for speech recognition
  bufferSize: 4096,      // ~256ms at 16kHz
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useAudioCapture(config: AudioCaptureConfig = {}): UseAudioCaptureReturn {
  const settings = { ...DEFAULT_CONFIG, ...config };

  // State
  const [hasPermission, setHasPermission] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [deviceLabel, setDeviceLabel] = useState<string | null>(null);

  // Refs for cleanup
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const callbackRef = useRef<((data: Float32Array) => void) | null>(null);

  // Clean up resources
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current?.state !== 'closed') {
      audioContextRef.current?.close();
      audioContextRef.current = null;
    }

    setIsCapturing(false);
    setAudioLevel(0);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // Request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    setIsPending(true);
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: settings.echoCancellation,
          noiseSuppression: settings.noiseSuppression,
          autoGainControl: settings.autoGainControl,
          sampleRate: settings.sampleRate,
        },
        video: false,
      });

      // Get device info
      const audioTrack = stream.getAudioTracks()[0];
      setDeviceLabel(audioTrack.label || 'Default microphone');

      // Stop the stream (we just wanted permission)
      stream.getTracks().forEach(track => track.stop());

      setHasPermission(true);
      setIsPending(false);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Microphone permission denied';
      setError(message);
      setHasPermission(false);
      setIsPending(false);
      return false;
    }
  }, [settings]);

  // Update audio level from analyser (called via requestAnimationFrame)
  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate RMS for a more natural VU meter
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const value = dataArray[i] / 255;
      sum += value * value;
    }
    const rms = Math.sqrt(sum / dataArray.length);

    setAudioLevel(rms);

    if (isCapturing) {
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [isCapturing]);

  // Start capturing audio
  const startCapture = useCallback(async (): Promise<void> => {
    if (isCapturing) return;

    setError(null);

    try {
      // Get new stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: settings.echoCancellation,
          noiseSuppression: settings.noiseSuppression,
          autoGainControl: settings.autoGainControl,
          sampleRate: settings.sampleRate,
        },
        video: false,
      });
      streamRef.current = stream;

      // Create audio context
      const audioContext = new AudioContext({
        sampleRate: settings.sampleRate,
      });
      audioContextRef.current = audioContext;

      // Create source from stream
      const source = audioContext.createMediaStreamSource(stream);

      // Create analyser for level metering
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;
      source.connect(analyser);

      // Create script processor for audio data (AudioWorklet preferred but more complex)
      // Using ScriptProcessorNode for simplicity - deprecated but widely supported
      const processor = audioContext.createScriptProcessor(settings.bufferSize, 1, 1);

      processor.onaudioprocess = (event) => {
        if (callbackRef.current) {
          const inputData = event.inputBuffer.getChannelData(0);
          // Copy the data since the buffer gets reused
          const copy = new Float32Array(inputData.length);
          copy.set(inputData);
          callbackRef.current(copy);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsCapturing(true);
      setHasPermission(true);

      // Start level monitoring
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start audio capture';
      setError(message);
      cleanup();
      throw new Error(message);
    }
  }, [isCapturing, settings, cleanup, updateAudioLevel]);

  // Stop capturing audio
  const stopCapture = useCallback(() => {
    cleanup();
  }, [cleanup]);

  // Set callback for audio data
  const onAudioData = useCallback((callback: (data: Float32Array) => void) => {
    callbackRef.current = callback;
  }, []);

  return [
    {
      hasPermission,
      isCapturing,
      isPending,
      audioLevel,
      error,
      deviceLabel,
    },
    {
      requestPermission,
      startCapture,
      stopCapture,
      onAudioData,
    },
  ];
}

// ============================================================================
// Utility: Convert Float32Array to Int16Array (for WebSocket transmission)
// ============================================================================

export function float32ToInt16(float32Array: Float32Array): Int16Array {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    // Clamp to [-1, 1] range and scale to int16
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16Array;
}

// ============================================================================
// Utility: Convert Int16Array to ArrayBuffer for WebSocket
// ============================================================================

export function int16ToArrayBuffer(int16Array: Int16Array): ArrayBuffer {
  // Create a new ArrayBuffer and copy data to ensure it's not SharedArrayBuffer
  const buffer = new ArrayBuffer(int16Array.byteLength);
  const view = new Int16Array(buffer);
  view.set(int16Array);
  return buffer;
}

export default useAudioCapture;
