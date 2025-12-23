/**
 * PlaybackControls - Media player-style controls for timeline navigation
 *
 * Features:
 * - Play/Pause button with animated icon
 * - Speed selector (0.5x, 1x, 2x, 4x)
 * - Skip to start/end buttons
 * - Step forward/backward buttons
 * - Current position display (Day X, Phase Y of Z)
 * - Auto-stops at end of timeline
 * - Keyboard shortcuts (Space=play/pause, arrows already handled by TimelineScrubber)
 */

import { useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore, PHASES } from '../../stores/gameStore';
import { usePlaybackTimer, useReducedMotion } from '../../hooks';

// ============================================================================
// Types
// ============================================================================

interface PlaybackControlsProps {
  totalDays: number;
}

type PlaybackSpeed = 0.5 | 1 | 2 | 4;

const SPEED_OPTIONS: { value: PlaybackSpeed; label: string }[] = [
  { value: 0.5, label: '0.5×' },
  { value: 1, label: '1×' },
  { value: 2, label: '2×' },
  { value: 4, label: '4×' },
];

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Animated play/pause button with morphing icon
 */
function PlayPauseButton({
  isPlaying,
  onClick,
  disabled,
}: {
  isPlaying: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
        disabled
          ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
          : isPlaying
          ? 'bg-orange-500 hover:bg-orange-400 text-white'
          : 'bg-blue-500 hover:bg-blue-400 text-white'
      }`}
      whileHover={disabled ? {} : { scale: 1.05 }}
      whileTap={disabled ? {} : { scale: 0.95 }}
      aria-label={isPlaying ? 'Pause' : 'Play'}
      title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
    >
      <AnimatePresence mode="wait">
        {isPlaying ? (
          <motion.div
            key="pause"
            initial={reducedMotion ? false : { scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex gap-1"
          >
            <span className="w-1.5 h-5 bg-current rounded-sm" />
            <span className="w-1.5 h-5 bg-current rounded-sm" />
          </motion.div>
        ) : (
          <motion.div
            key="play"
            initial={reducedMotion ? false : { scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="ml-1"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <polygon points="4,2 18,10 4,18" />
            </svg>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.button>
  );
}

/**
 * Small icon button for step/skip controls
 */
function IconButton({
  onClick,
  disabled,
  title,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
        disabled
          ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
          : 'bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white'
      }`}
      whileHover={disabled ? {} : { scale: 1.1 }}
      whileTap={disabled ? {} : { scale: 0.9 }}
      title={title}
      aria-label={title}
    >
      {children}
    </motion.button>
  );
}

/**
 * Speed selector dropdown
 */
function SpeedSelector({
  currentSpeed,
  onSpeedChange,
}: {
  currentSpeed: number;
  onSpeedChange: (speed: PlaybackSpeed) => void;
}) {
  return (
    <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
      {SPEED_OPTIONS.map(option => (
        <button
          key={option.value}
          onClick={() => onSpeedChange(option.value)}
          className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${
            currentSpeed === option.value
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
          title={`Set speed to ${option.label}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Progress indicator showing current position in timeline
 */
function ProgressIndicator({
  currentDay,
  currentPhase,
  totalDays,
}: {
  currentDay: number;
  currentPhase: string;
  totalDays: number;
}) {
  const phaseIndex = PHASES.indexOf(currentPhase as typeof PHASES[number]) + 1;
  const totalPhases = totalDays * PHASES.length;
  const currentPosition = (currentDay - 1) * PHASES.length + phaseIndex;
  const progressPercent = Math.round((currentPosition / totalPhases) * 100);

  const phaseName = PHASES.find(p => p === currentPhase)
    ? currentPhase.charAt(0).toUpperCase() + currentPhase.slice(1)
    : currentPhase;

  return (
    <div className="flex flex-col items-center min-w-[120px]">
      <div className="text-sm font-medium text-white">
        Day {currentDay} - {phaseName}
      </div>
      <div className="text-xs text-gray-500">
        Phase {currentPosition} of {totalPhases} ({progressPercent}%)
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function PlaybackControls({ totalDays }: PlaybackControlsProps) {
  const {
    currentDay,
    currentPhase,
    isPlaying,
    playbackSpeed,
    togglePlayback,
    setPlaybackSpeed,
    stopPlayback,
    nextPhase,
    prevPhase,
    setTimelinePosition,
  } = useGameStore();

  // Check if we're at the boundaries
  const isAtStart = currentDay === 1 && currentPhase === PHASES[0];
  const isAtEnd = currentDay === totalDays && currentPhase === PHASES[PHASES.length - 1];

  // Auto-advance handler
  const handleAdvance = useCallback(() => {
    // Check if we're at the end before advancing
    const phaseIndex = PHASES.indexOf(currentPhase as typeof PHASES[number]);
    const isLastPhase = phaseIndex === PHASES.length - 1;
    const isLastDay = currentDay === totalDays;

    if (isLastPhase && isLastDay) {
      // Stop playback at the end
      stopPlayback();
    } else {
      nextPhase(totalDays);
    }
  }, [currentDay, currentPhase, totalDays, nextPhase, stopPlayback]);

  // Use the playback timer hook
  usePlaybackTimer(isPlaying, playbackSpeed, handleAdvance, 2000);

  // Step handlers
  const handleStepBack = useCallback(() => {
    if (!isAtStart) {
      prevPhase();
    }
  }, [isAtStart, prevPhase]);

  const handleStepForward = useCallback(() => {
    if (!isAtEnd) {
      nextPhase(totalDays);
    }
  }, [isAtEnd, totalDays, nextPhase]);

  // Skip to start/end handlers
  const handleSkipToStart = useCallback(() => {
    stopPlayback();
    setTimelinePosition(1, PHASES[0]);
  }, [stopPlayback, setTimelinePosition]);

  const handleSkipToEnd = useCallback(() => {
    stopPlayback();
    setTimelinePosition(totalDays, PHASES[PHASES.length - 1]);
  }, [stopPlayback, setTimelinePosition, totalDays]);

  // Keyboard shortcuts (Space for play/pause)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (!isAtEnd || isPlaying) {
            togglePlayback();
          }
          break;
        // Note: Arrow keys handled by TimelineScrubber
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAtEnd, isPlaying, togglePlayback]);

  // Auto-stop when reaching end
  useEffect(() => {
    if (isPlaying && isAtEnd) {
      stopPlayback();
    }
  }, [isPlaying, isAtEnd, stopPlayback]);

  return (
    <div className="playback-controls flex items-center justify-center gap-6 py-3 px-4 bg-gray-800/50 rounded-xl backdrop-blur">
      {/* Skip to start */}
      <IconButton
        onClick={handleSkipToStart}
        disabled={isAtStart}
        title="Skip to start"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <rect x="1" y="2" width="2" height="10" />
          <polygon points="13,2 5,7 13,12" />
        </svg>
      </IconButton>

      {/* Step back */}
      <IconButton
        onClick={handleStepBack}
        disabled={isAtStart}
        title="Previous phase"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <polygon points="12,2 4,7 12,12" />
        </svg>
      </IconButton>

      {/* Play/Pause */}
      <PlayPauseButton
        isPlaying={isPlaying}
        onClick={togglePlayback}
        disabled={isAtEnd && !isPlaying}
      />

      {/* Step forward */}
      <IconButton
        onClick={handleStepForward}
        disabled={isAtEnd}
        title="Next phase"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <polygon points="2,2 10,7 2,12" />
        </svg>
      </IconButton>

      {/* Skip to end */}
      <IconButton
        onClick={handleSkipToEnd}
        disabled={isAtEnd}
        title="Skip to end"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <polygon points="1,2 9,7 1,12" />
          <rect x="11" y="2" width="2" height="10" />
        </svg>
      </IconButton>

      {/* Divider */}
      <div className="w-px h-8 bg-gray-700" />

      {/* Speed selector */}
      <SpeedSelector
        currentSpeed={playbackSpeed}
        onSpeedChange={setPlaybackSpeed}
      />

      {/* Divider */}
      <div className="w-px h-8 bg-gray-700" />

      {/* Progress indicator */}
      <ProgressIndicator
        currentDay={currentDay}
        currentPhase={currentPhase}
        totalDays={totalDays}
      />

      {/* Playing indicator */}
      <AnimatePresence>
        {isPlaying && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center gap-2 text-green-400 text-sm"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span>Playing</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default PlaybackControls;
