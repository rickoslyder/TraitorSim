/**
 * Audio Playback Hook - Web Audio API integration
 *
 * Provides real-time audio playback with:
 * - Streaming audio buffer queue management
 * - Smooth transitions between chunks
 * - Current speaker tracking
 * - Playback state management
 *
 * Works with the HITL WebSocket server for AI agent voice responses.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface AudioPlaybackConfig {
  /** Sample rate in Hz (must match server) */
  sampleRate?: number;
  /** Maximum queued audio duration in seconds */
  maxQueueDuration?: number;
  /** Crossfade duration between chunks in ms */
  crossfadeDuration?: number;
}

export interface AudioPlaybackState {
  /** Whether audio is currently playing */
  isPlaying: boolean;
  /** Number of chunks in the queue */
  queueLength: number;
  /** Estimated queue duration in seconds */
  queueDuration: number;
  /** Current speaker name (if tracked) */
  currentSpeaker: string | null;
  /** Any error that occurred */
  error: string | null;
}

export interface AudioPlaybackActions {
  /** Queue audio data for playback */
  queueAudio: (data: ArrayBuffer | Int16Array, speaker?: string) => void;
  /** Start playback (resumes AudioContext if suspended) */
  startPlayback: () => Promise<void>;
  /** Stop playback and clear queue */
  stopPlayback: () => void;
  /** Pause playback (keeps queue) */
  pausePlayback: () => void;
  /** Resume playback */
  resumePlayback: () => Promise<void>;
  /** Clear the audio queue */
  clearQueue: () => void;
  /** Set callback for playback complete */
  onPlaybackComplete: (callback: () => void) => void;
  /** Set callback for speaker change */
  onSpeakerChange: (callback: (speaker: string | null) => void) => void;
}

export type UseAudioPlaybackReturn = [AudioPlaybackState, AudioPlaybackActions];

// ============================================================================
// Audio Chunk with metadata
// ============================================================================

interface AudioChunk {
  data: AudioBuffer;
  speaker?: string;
  duration: number;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_CONFIG: Required<AudioPlaybackConfig> = {
  sampleRate: 16000,
  maxQueueDuration: 30,    // 30 seconds max queue
  crossfadeDuration: 10,   // 10ms crossfade
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useAudioPlayback(config: AudioPlaybackConfig = {}): UseAudioPlaybackReturn {
  const settings = { ...DEFAULT_CONFIG, ...config };

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [queueLength, setQueueLength] = useState(0);
  const [queueDuration, setQueueDuration] = useState(0);
  const [currentSpeaker, setCurrentSpeaker] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioChunk[]>([]);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const isProcessingRef = useRef<boolean>(false);
  const playbackCompleteCallbackRef = useRef<(() => void) | null>(null);
  const speakerChangeCallbackRef = useRef<((speaker: string | null) => void) | null>(null);

  // Update queue stats
  const updateQueueStats = useCallback(() => {
    const queue = audioQueueRef.current;
    setQueueLength(queue.length);

    let totalDuration = 0;
    for (const chunk of queue) {
      totalDuration += chunk.duration;
    }
    setQueueDuration(totalDuration);
  }, []);

  // Get or create audio context
  const getAudioContext = useCallback((): AudioContext => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new AudioContext({
        sampleRate: settings.sampleRate,
      });
    }
    return audioContextRef.current;
  }, [settings.sampleRate]);

  // Process the queue - schedule next chunk
  const processQueue = useCallback(async () => {
    if (isProcessingRef.current) return;

    const queue = audioQueueRef.current;
    if (queue.length === 0) {
      setIsPlaying(false);
      if (playbackCompleteCallbackRef.current) {
        playbackCompleteCallbackRef.current();
      }
      return;
    }

    isProcessingRef.current = true;

    try {
      const audioContext = getAudioContext();

      // Resume if suspended (browser autoplay policy)
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      const chunk = queue.shift()!;
      updateQueueStats();

      // Update current speaker if changed
      if (chunk.speaker !== currentSpeaker) {
        setCurrentSpeaker(chunk.speaker || null);
        if (speakerChangeCallbackRef.current) {
          speakerChangeCallbackRef.current(chunk.speaker || null);
        }
      }

      // Create source node
      const source = audioContext.createBufferSource();
      source.buffer = chunk.data;
      source.connect(audioContext.destination);
      currentSourceRef.current = source;

      // Calculate start time (schedule slightly ahead for gapless playback)
      const now = audioContext.currentTime;
      const startTime = Math.max(now, nextPlayTimeRef.current);

      // Update next play time
      nextPlayTimeRef.current = startTime + chunk.duration;

      // Handle completion
      source.onended = () => {
        currentSourceRef.current = null;
        isProcessingRef.current = false;
        processQueue(); // Process next chunk
      };

      // Start playback
      source.start(startTime);
      setIsPlaying(true);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Playback error';
      setError(message);
      isProcessingRef.current = false;
    }
  }, [getAudioContext, updateQueueStats, currentSpeaker]);

  // Convert raw audio data to AudioBuffer
  const createAudioBuffer = useCallback((data: ArrayBuffer | Int16Array): AudioBuffer => {
    const audioContext = getAudioContext();

    // Convert to Int16Array if needed
    let int16Data: Int16Array;
    if (data instanceof Int16Array) {
      int16Data = data;
    } else {
      int16Data = new Int16Array(data);
    }

    // Create audio buffer
    const numSamples = int16Data.length;
    const audioBuffer = audioContext.createBuffer(1, numSamples, settings.sampleRate);
    const channelData = audioBuffer.getChannelData(0);

    // Convert Int16 to Float32 (-1 to 1)
    for (let i = 0; i < numSamples; i++) {
      channelData[i] = int16Data[i] / 0x8000;
    }

    return audioBuffer;
  }, [getAudioContext, settings.sampleRate]);

  // Queue audio data for playback
  const queueAudio = useCallback((data: ArrayBuffer | Int16Array, speaker?: string) => {
    try {
      const audioBuffer = createAudioBuffer(data);

      // Check queue limit
      let currentQueueDuration = 0;
      for (const chunk of audioQueueRef.current) {
        currentQueueDuration += chunk.duration;
      }

      // Drop oldest chunks if queue is too long
      while (currentQueueDuration > settings.maxQueueDuration && audioQueueRef.current.length > 0) {
        const dropped = audioQueueRef.current.shift()!;
        currentQueueDuration -= dropped.duration;
      }

      // Add new chunk
      audioQueueRef.current.push({
        data: audioBuffer,
        speaker,
        duration: audioBuffer.duration,
      });

      updateQueueStats();

      // Start processing if not already
      if (!isProcessingRef.current && !isPlaying) {
        processQueue();
      }

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to queue audio';
      setError(message);
    }
  }, [createAudioBuffer, settings.maxQueueDuration, updateQueueStats, isPlaying, processQueue]);

  // Start playback
  const startPlayback = useCallback(async () => {
    setError(null);

    try {
      const audioContext = getAudioContext();
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      nextPlayTimeRef.current = audioContext.currentTime;
      processQueue();

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start playback';
      setError(message);
    }
  }, [getAudioContext, processQueue]);

  // Stop playback and clear queue
  const stopPlayback = useCallback(() => {
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch {
        // Ignore if already stopped
      }
      currentSourceRef.current = null;
    }

    audioQueueRef.current = [];
    isProcessingRef.current = false;
    setIsPlaying(false);
    setCurrentSpeaker(null);
    updateQueueStats();
  }, [updateQueueStats]);

  // Pause playback
  const pausePlayback = useCallback(() => {
    const audioContext = audioContextRef.current;
    if (audioContext && audioContext.state === 'running') {
      audioContext.suspend();
      setIsPlaying(false);
    }
  }, []);

  // Resume playback
  const resumePlayback = useCallback(async () => {
    const audioContext = audioContextRef.current;
    if (audioContext && audioContext.state === 'suspended') {
      await audioContext.resume();
      if (audioQueueRef.current.length > 0 || currentSourceRef.current) {
        setIsPlaying(true);
      }
    }
  }, []);

  // Clear the queue (keep current playing)
  const clearQueue = useCallback(() => {
    audioQueueRef.current = [];
    updateQueueStats();
  }, [updateQueueStats]);

  // Set playback complete callback
  const onPlaybackComplete = useCallback((callback: () => void) => {
    playbackCompleteCallbackRef.current = callback;
  }, []);

  // Set speaker change callback
  const onSpeakerChange = useCallback((callback: (speaker: string | null) => void) => {
    speakerChangeCallbackRef.current = callback;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPlayback();
      if (audioContextRef.current?.state !== 'closed') {
        audioContextRef.current?.close();
      }
    };
  }, [stopPlayback]);

  return [
    {
      isPlaying,
      queueLength,
      queueDuration,
      currentSpeaker,
      error,
    },
    {
      queueAudio,
      startPlayback,
      stopPlayback,
      pausePlayback,
      resumePlayback,
      clearQueue,
      onPlaybackComplete,
      onSpeakerChange,
    },
  ];
}

export default useAudioPlayback;
