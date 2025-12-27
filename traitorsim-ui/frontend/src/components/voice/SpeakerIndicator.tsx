/**
 * SpeakerIndicator - Visual indicator showing who is speaking
 *
 * Displays:
 * - Current speaker name with avatar/initial
 * - Audio waveform visualization
 * - Listening/speaking state
 */

import { useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ============================================================================
// Types
// ============================================================================

export interface SpeakerIndicatorProps {
  /** Name of the current speaker (null if no one speaking) */
  speakerName: string | null;
  /** Whether audio is currently playing */
  isPlaying: boolean;
  /** Audio level for waveform (0-1) - for human mic input */
  audioLevel?: number;
  /** Remaining audio queue duration in seconds */
  queueDuration?: number;
  /** Custom class name */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function SpeakerIndicator({
  speakerName,
  isPlaying,
  audioLevel,
  queueDuration = 0,
  className = '',
}: SpeakerIndicatorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const barsRef = useRef<number[]>(Array(32).fill(0.1));

  // Generate avatar color from name
  const avatarColor = useMemo(() => {
    if (!speakerName) return 'bg-gray-600';

    // Simple hash function for consistent colors
    let hash = 0;
    for (let i = 0; i < speakerName.length; i++) {
      hash = speakerName.charCodeAt(i) + ((hash << 5) - hash);
    }

    const colors = [
      'bg-blue-600',
      'bg-purple-600',
      'bg-pink-600',
      'bg-red-600',
      'bg-orange-600',
      'bg-yellow-600',
      'bg-green-600',
      'bg-teal-600',
      'bg-cyan-600',
      'bg-indigo-600',
    ];

    return colors[Math.abs(hash) % colors.length];
  }, [speakerName]);

  // Get initials from name
  const initials = useMemo(() => {
    if (!speakerName) return '?';

    return speakerName
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }, [speakerName]);

  // Animate waveform bars
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bars = barsRef.current;
    const numBars = bars.length;

    const animate = () => {
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Update bars
      for (let i = 0; i < numBars; i++) {
        if (isPlaying) {
          // Simulate audio waveform with random movement
          const target = 0.2 + Math.random() * 0.6;
          bars[i] = bars[i] + (target - bars[i]) * 0.3;
        } else if (audioLevel !== undefined && audioLevel > 0) {
          // Use actual audio level for human input
          const variation = Math.sin(Date.now() / 50 + i * 0.5) * 0.2;
          bars[i] = Math.max(0.1, Math.min(1, audioLevel + variation));
        } else {
          // Decay to baseline
          bars[i] = bars[i] * 0.9 + 0.1 * 0.1;
        }
      }

      // Draw bars
      const barWidth = canvas.width / numBars;
      const barGap = 2;
      const maxHeight = canvas.height * 0.9;

      ctx.fillStyle = isPlaying ? '#60A5FA' : (audioLevel ? '#F87171' : '#6B7280');

      for (let i = 0; i < numBars; i++) {
        const height = bars[i] * maxHeight;
        const x = i * barWidth + barGap / 2;
        const y = (canvas.height - height) / 2;

        ctx.beginPath();
        ctx.roundRect(x, y, barWidth - barGap, height, 2);
        ctx.fill();
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, audioLevel]);

  // Determine status text
  const statusText = useMemo(() => {
    if (audioLevel !== undefined && audioLevel > 0.1) {
      return 'You are speaking';
    }
    if (speakerName && isPlaying) {
      return `${speakerName} is speaking`;
    }
    if (speakerName && queueDuration > 0) {
      return `${speakerName} (${queueDuration.toFixed(1)}s queued)`;
    }
    return 'Listening...';
  }, [speakerName, isPlaying, audioLevel, queueDuration]);

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      {/* Avatar */}
      <motion.div
        className={`relative w-12 h-12 rounded-full ${avatarColor} flex items-center justify-center`}
        animate={{
          scale: isPlaying || (audioLevel && audioLevel > 0.1) ? [1, 1.1, 1] : 1,
        }}
        transition={{
          repeat: isPlaying || (audioLevel && audioLevel > 0.1) ? Infinity : 0,
          duration: 0.8,
        }}
      >
        <span className="text-white font-bold text-lg">{initials}</span>

        {/* Active indicator ring */}
        <AnimatePresence>
          {(isPlaying || (audioLevel && audioLevel > 0.1)) && (
            <motion.div
              initial={{ scale: 1, opacity: 0 }}
              animate={{ scale: 1.5, opacity: 0 }}
              exit={{ scale: 1, opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="absolute inset-0 rounded-full border-2 border-blue-400"
            />
          )}
        </AnimatePresence>
      </motion.div>

      {/* Waveform and status */}
      <div className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          <motion.p
            key={statusText}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="text-sm font-medium text-gray-300 truncate mb-1"
          >
            {statusText}
          </motion.p>
        </AnimatePresence>

        {/* Waveform canvas */}
        <canvas
          ref={canvasRef}
          width={200}
          height={32}
          className="w-full h-8 rounded bg-gray-800"
        />
      </div>
    </div>
  );
}

export default SpeakerIndicator;
