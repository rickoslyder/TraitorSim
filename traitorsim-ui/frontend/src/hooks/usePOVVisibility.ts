/**
 * usePOVVisibility - Hook for POV-aware content visibility
 *
 * Provides utilities to determine what content should be visible
 * based on the current viewing mode (omniscient, faithful, traitor).
 *
 * Usage:
 *   const { shouldShowRole, isVisibleEvent, getVisibleTrust } = usePOVVisibility(players);
 *   if (shouldShowRole(player)) { ... }
 */

import { useCallback } from 'react';
import { useGameStore, ViewingMode } from '../stores/gameStore';
import { Player, GameEvent, TrustMatrix, EventType } from '../types';

// Event types that contain spoiler information (Traitor knowledge)
const TRAITOR_ONLY_EVENTS: EventType[] = [
  'MURDER',
  'MURDER_ATTEMPT',
  'RECRUITMENT',
  'RECRUITMENT_OFFER',
];

// Events that should never be hidden (public knowledge)
const PUBLIC_EVENTS: EventType[] = [
  'MURDER_SUCCESS',
  'BANISHMENT',
  'VOTE',
  'VOTE_TALLY',
  'MISSION_COMPLETE',
  'MISSION_SUCCESS',
  'MISSION_FAIL',
  'SHIELD_AWARDED',
  'SEER_AWARDED',
  'DAGGER_AWARDED',
  'BREAKFAST_ORDER',
  'GAME_START',
  'GAME_END',
  'DAY_START',
  'PHASE_CHANGE',
];

export interface POVVisibility {
  /** Current viewing mode */
  viewingMode: ViewingMode;

  /** The specific player's POV (for faithful mode) */
  povPlayerId: string | null;

  /** Whether to show a player's role */
  shouldShowRole: (player: Player) => boolean;

  /** Whether to show a player as a Traitor (for highlighting/styling) */
  shouldRevealTraitor: (player: Player) => boolean;

  /** Whether an event should be visible in the current POV */
  isVisibleEvent: (event: GameEvent) => boolean;

  /** Filter events to only those visible in current POV */
  filterVisibleEvents: (events: GameEvent[]) => GameEvent[];

  /** Get the trust matrix visible to current POV (may be filtered) */
  getVisibleTrust: (fullMatrix: TrustMatrix) => TrustMatrix;

  /** Whether to show "spoiler" warning banner */
  hasSpoilers: boolean;

  /** Whether we're in spoiler-free mode */
  isSpoilerFree: boolean;
}

export function usePOVVisibility(
  _players: Record<string, Player> = {}
): POVVisibility {
  const { viewingMode, povPlayerId } = useGameStore();

  // Note: _players is available for future enhancements like
  // showing only traitor trust when in traitor mode

  /**
   * Determine if a player's role should be displayed.
   *
   * - Omniscient: Always show roles
   * - Traitor POV: Show Traitor roles, hide Faithful roles
   * - Faithful POV: Never show roles (everyone is a suspect)
   */
  const shouldShowRole = useCallback((player: Player): boolean => {
    switch (viewingMode) {
      case 'omniscient':
        return true;
      case 'traitor':
        return player.role === 'TRAITOR';
      case 'faithful':
        return false;
    }
  }, [viewingMode]);

  /**
   * Determine if a player should be revealed/highlighted as a Traitor.
   * Used for styling (red borders, etc.)
   */
  const shouldRevealTraitor = useCallback((player: Player): boolean => {
    if (player.role !== 'TRAITOR') return false;

    switch (viewingMode) {
      case 'omniscient':
        return true;
      case 'traitor':
        return true;
      case 'faithful':
        // In faithful mode, only reveal if player was eliminated and role was revealed
        return !player.alive && player.elimination_type === 'BANISHED';
    }
  }, [viewingMode]);

  /**
   * Check if an event should be visible in the current POV.
   */
  const isVisibleEvent = useCallback((event: GameEvent): boolean => {
    // Public events are always visible
    if (PUBLIC_EVENTS.includes(event.type)) {
      return true;
    }

    switch (viewingMode) {
      case 'omniscient':
        // God mode sees everything
        return true;

      case 'traitor':
        // Traitor mode sees Traitor-only events
        return true;

      case 'faithful': {
        // Faithful mode hides Traitor-only events
        if (TRAITOR_ONLY_EVENTS.includes(event.type)) {
          return false;
        }

        // If we have a specific POV player, only show events they could know about
        if (povPlayerId) {
          // Events where POV player is actor or target
          if (event.actor === povPlayerId || event.target === povPlayerId) {
            return true;
          }

          // Events with participants that include POV player
          const participants = event.data?.participants as string[] | undefined;
          if (participants?.includes(povPlayerId)) {
            return true;
          }

          // Votes where POV player voted
          const votes = event.data?.votes as Record<string, string> | undefined;
          if (votes?.[povPlayerId]) {
            return true;
          }

          // General public events
          return PUBLIC_EVENTS.includes(event.type);
        }

        return true;
      }
    }
  }, [viewingMode, povPlayerId]);

  /**
   * Filter events to only those visible in the current POV.
   */
  const filterVisibleEvents = useCallback((events: GameEvent[]): GameEvent[] => {
    return events.filter(isVisibleEvent);
  }, [isVisibleEvent]);

  /**
   * Get the trust matrix visible to the current POV.
   *
   * - Omniscient: Full matrix
   * - Traitor: Full matrix (Traitors know everything)
   * - Faithful: Only the POV player's trust, or empty if no POV player
   */
  const getVisibleTrust = useCallback((fullMatrix: TrustMatrix): TrustMatrix => {
    switch (viewingMode) {
      case 'omniscient':
      case 'traitor':
        return fullMatrix;

      case 'faithful':
        if (povPlayerId && fullMatrix[povPlayerId]) {
          // Only show the POV player's trust assessments
          return {
            [povPlayerId]: fullMatrix[povPlayerId],
          };
        }
        // No specific POV player - show aggregate "public" trust
        return fullMatrix;
    }
  }, [viewingMode, povPlayerId]);

  const hasSpoilers = viewingMode !== 'faithful';
  const isSpoilerFree = viewingMode === 'faithful';

  return {
    viewingMode,
    povPlayerId,
    shouldShowRole,
    shouldRevealTraitor,
    isVisibleEvent,
    filterVisibleEvents,
    getVisibleTrust,
    hasSpoilers,
    isSpoilerFree,
  };
}

export default usePOVVisibility;
