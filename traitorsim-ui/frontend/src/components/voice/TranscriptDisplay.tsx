/**
 * TranscriptDisplay - Accessibility-first transcript display
 *
 * Shows:
 * - Real-time transcripts with speaker attribution
 * - Auto-scroll to latest
 * - Visual indicators for interim vs final transcripts
 * - ARIA live region for screen readers
 */

import { useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { TranscriptMessage } from '../../hooks/useVoiceWebSocket';

// ============================================================================
// Types
// ============================================================================

export interface TranscriptDisplayProps {
  /** List of transcripts to display */
  transcripts: TranscriptMessage[];
  /** Maximum height in pixels */
  maxHeight?: number;
  /** Whether to auto-scroll to latest */
  autoScroll?: boolean;
  /** Custom class name */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function TranscriptDisplay({
  transcripts,
  maxHeight = 200,
  autoScroll = true,
  className = '',
}: TranscriptDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new transcripts arrive
  useEffect(() => {
    if (autoScroll && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcripts, autoScroll]);

  // Group consecutive transcripts from same speaker
  const groupedTranscripts = useMemo(() => {
    const groups: {
      speakerId: string;
      speakerName: string;
      messages: TranscriptMessage[];
    }[] = [];

    for (const transcript of transcripts) {
      const lastGroup = groups[groups.length - 1];

      if (lastGroup && lastGroup.speakerId === transcript.speaker_id) {
        lastGroup.messages.push(transcript);
      } else {
        groups.push({
          speakerId: transcript.speaker_id,
          speakerName: transcript.speaker_name,
          messages: [transcript],
        });
      }
    }

    return groups;
  }, [transcripts]);

  // Get speaker color
  const getSpeakerColor = (speakerName: string): string => {
    // Simple hash for consistent colors
    let hash = 0;
    for (let i = 0; i < speakerName.length; i++) {
      hash = speakerName.charCodeAt(i) + ((hash << 5) - hash);
    }

    const colors = [
      'text-blue-400',
      'text-purple-400',
      'text-pink-400',
      'text-red-400',
      'text-orange-400',
      'text-yellow-400',
      'text-green-400',
      'text-teal-400',
      'text-cyan-400',
      'text-indigo-400',
    ];

    return colors[Math.abs(hash) % colors.length];
  };

  // Empty state
  if (transcripts.length === 0) {
    return (
      <div
        className={`p-4 text-center text-gray-500 text-sm ${className}`}
        style={{ maxHeight }}
      >
        <p>Transcripts will appear here...</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`overflow-y-auto p-4 space-y-3 ${className}`}
      style={{ maxHeight }}
      role="log"
      aria-live="polite"
      aria-label="Voice transcripts"
    >
      <AnimatePresence initial={false}>
        {groupedTranscripts.map((group, groupIndex) => (
          <motion.div
            key={`${group.speakerId}-${groupIndex}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-1"
          >
            {/* Speaker name */}
            <p className={`text-xs font-semibold ${getSpeakerColor(group.speakerName)}`}>
              {group.speakerName}
            </p>

            {/* Messages */}
            {group.messages.map((message, messageIndex) => (
              <motion.p
                key={`${message.speaker_id}-${groupIndex}-${messageIndex}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-sm leading-relaxed ${
                  message.is_final
                    ? 'text-gray-200'
                    : 'text-gray-400 italic'
                }`}
              >
                {message.text}
                {!message.is_final && (
                  <span className="inline-block ml-1 w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                )}
              </motion.p>
            ))}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Scroll anchor */}
      <div ref={endRef} />
    </div>
  );
}

export default TranscriptDisplay;
