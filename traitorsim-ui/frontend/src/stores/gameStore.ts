/**
 * Zustand store for UI state management
 *
 * This store manages ONLY UI state:
 * - Selection state (which game, player is selected)
 * - Timeline position (current day/phase being viewed)
 * - View options (show roles, show eliminated, etc.)
 *
 * Server state (game data, trust matrices, events) is managed by
 * TanStack Query hooks in api/hooks.ts
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Phase, TrustMatrix, TrustSnapshot } from '../types';

// ============================================================================
// Types
// ============================================================================

type Theme = 'dark' | 'light' | 'system';

/**
 * Viewing mode determines what information is visible to the viewer.
 *
 * - omniscient: Full spoilers - see all roles, all trust, murder discussions
 * - faithful: Spoiler-free - experience like a Faithful contestant (optional: from specific player's POV)
 * - traitor: Traitor knowledge - see Traitors, murder decisions, recruitment plots
 */
type ViewingMode = 'omniscient' | 'faithful' | 'traitor';

interface GameStore {
  // Selection state
  selectedGameId: string | null;
  selectedPlayerId: string | null;
  highlightedPlayers: string[];
  hoveredPlayerId: string | null;

  // Timeline state
  currentDay: number;
  currentPhase: Phase;

  // View options
  showRoles: boolean;
  showEliminatedPlayers: boolean;
  trustThreshold: number;
  viewingMode: ViewingMode;
  povPlayerId: string | null; // For faithful mode - whose perspective to show

  // UI state
  sidebarOpen: boolean;
  theme: Theme;

  // Computed trust matrix (derived from snapshots + timeline position)
  currentTrustMatrix: TrustMatrix;

  // Animation state for trust matrix transitions
  previousTrustMatrix: TrustMatrix;
  animationProgress: number; // 0.0 to 1.0
  isAnimating: boolean;

  // Playback state
  isPlaying: boolean;
  playbackSpeed: number; // 0.5, 1, 2, 4

  // Actions - Selection
  selectGame: (id: string | null) => void;
  selectPlayer: (id: string | null) => void;
  highlightPlayer: (id: string) => void;
  unhighlightPlayer: (id: string) => void;
  clearHighlights: () => void;
  setHoveredPlayer: (id: string | null) => void;

  // Actions - Timeline
  setTimelinePosition: (day: number, phase: Phase) => void;
  nextPhase: (totalDays: number) => void;
  prevPhase: () => void;

  // Actions - View Options
  toggleRoleReveal: () => void;
  toggleShowEliminated: () => void;
  setTrustThreshold: (threshold: number) => void;
  setViewingMode: (mode: ViewingMode) => void;
  setPovPlayer: (playerId: string | null) => void;

  // Actions - UI
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;

  // Actions - Trust Matrix
  updateTrustMatrix: (snapshots: TrustSnapshot[]) => void;

  // Actions - Animation
  startAnimation: () => void;
  setAnimationProgress: (progress: number) => void;
  stopAnimation: () => void;

  // Actions - Playback
  togglePlayback: () => void;
  setPlaybackSpeed: (speed: number) => void;
  stopPlayback: () => void;

  // Actions - Reset
  reset: () => void;
  resetTimeline: () => void;
}

// ============================================================================
// Constants
// ============================================================================

const PHASES: Phase[] = ['breakfast', 'mission', 'social', 'roundtable', 'turret'];

// Backend may use 'round_table', so we normalize when comparing
const normalizePhaseForMatch = (phase: Phase | string): Phase => {
  if (phase === 'round_table') return 'roundtable';
  return phase as Phase;
};

// ============================================================================
// Helpers
// ============================================================================

/**
 * Find the trust matrix for a specific day/phase from snapshots.
 * Falls back to the closest previous snapshot if exact match not found.
 */
function findTrustSnapshot(
  snapshots: TrustSnapshot[],
  day: number,
  phase: Phase
): TrustMatrix {
  if (!snapshots || snapshots.length === 0) {
    return {};
  }

  const normalizedPhase = normalizePhaseForMatch(phase);

  // Find exact match first (normalize both for comparison)
  const exact = snapshots.find(
    s => s.day === day && normalizePhaseForMatch(s.phase) === normalizedPhase
  );
  if (exact) return exact.matrix;

  // Find closest previous snapshot
  const phaseIndex = PHASES.indexOf(normalizedPhase);
  for (let d = day; d >= 1; d--) {
    const startPhase = d === day ? phaseIndex : PHASES.length - 1;
    for (let p = startPhase; p >= 0; p--) {
      const snapshot = snapshots.find(
        s => s.day === d && normalizePhaseForMatch(s.phase) === PHASES[p]
      );
      if (snapshot) return snapshot.matrix;
    }
  }

  // Return first available snapshot if none found before
  return snapshots[0]?.matrix || {};
}

// ============================================================================
// Store Definition
// ============================================================================

export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      // Initial state
      selectedGameId: null,
      selectedPlayerId: null,
      highlightedPlayers: [],
      hoveredPlayerId: null,
      currentDay: 1,
      currentPhase: 'breakfast',
      showRoles: false,
      showEliminatedPlayers: true,
      trustThreshold: 0.1,
      viewingMode: 'omniscient',
      povPlayerId: null,
      sidebarOpen: false,
      theme: 'dark',
      currentTrustMatrix: {},
      previousTrustMatrix: {},
      animationProgress: 1, // Start at 1 (no animation in progress)
      isAnimating: false,
      isPlaying: false,
      playbackSpeed: 1,

      // Selection actions
      selectGame: (id) => {
        set({
          selectedGameId: id,
          selectedPlayerId: null,
          highlightedPlayers: [],
          currentDay: 1,
          currentPhase: 'breakfast',
          currentTrustMatrix: {},
          previousTrustMatrix: {},
          animationProgress: 1,
          isAnimating: false,
          isPlaying: false,
        });
      },

      selectPlayer: (id) => {
        set({ selectedPlayerId: id });
      },

      highlightPlayer: (id) => {
        set((state) => ({
          highlightedPlayers: state.highlightedPlayers.includes(id)
            ? state.highlightedPlayers
            : [...state.highlightedPlayers, id],
        }));
      },

      unhighlightPlayer: (id) => {
        set((state) => ({
          highlightedPlayers: state.highlightedPlayers.filter((p) => p !== id),
        }));
      },

      clearHighlights: () => {
        set({ highlightedPlayers: [] });
      },

      setHoveredPlayer: (id) => {
        set({ hoveredPlayerId: id });
      },

      // Timeline actions
      setTimelinePosition: (day, phase) => {
        set({ currentDay: day, currentPhase: phase });
      },

      nextPhase: (totalDays) => {
        const { currentDay, currentPhase } = get();
        const phaseIndex = PHASES.indexOf(currentPhase);

        if (phaseIndex < PHASES.length - 1) {
          // Next phase in same day
          set({ currentPhase: PHASES[phaseIndex + 1] });
        } else if (currentDay < totalDays) {
          // First phase of next day
          set({ currentDay: currentDay + 1, currentPhase: PHASES[0] });
        }
        // Else: at the end, do nothing
      },

      prevPhase: () => {
        const { currentDay, currentPhase } = get();
        const phaseIndex = PHASES.indexOf(currentPhase);

        if (phaseIndex > 0) {
          // Previous phase in same day
          set({ currentPhase: PHASES[phaseIndex - 1] });
        } else if (currentDay > 1) {
          // Last phase of previous day
          set({ currentDay: currentDay - 1, currentPhase: PHASES[PHASES.length - 1] });
        }
        // Else: at the beginning, do nothing
      },

      // View options actions
      toggleRoleReveal: () => {
        set((state) => ({ showRoles: !state.showRoles }));
      },

      toggleShowEliminated: () => {
        set((state) => ({ showEliminatedPlayers: !state.showEliminatedPlayers }));
      },

      setTrustThreshold: (threshold) => {
        set({ trustThreshold: threshold });
      },

      setViewingMode: (mode) => {
        // viewingMode controls what's visible. Components should use usePOVVisibility hook.
        // showRoles is a legacy toggle - we keep it in sync as a fallback
        // omniscient: show all roles (showRoles = true)
        // traitor: show traitor roles only (showRoles = false, use usePOVVisibility for nuanced control)
        // faithful: hide all roles (showRoles = false)
        const showRoles = mode === 'omniscient';
        set({
          viewingMode: mode,
          showRoles,
          // Clear POV player if switching away from faithful mode
          povPlayerId: mode === 'faithful' ? get().povPlayerId : null,
        });
      },

      setPovPlayer: (playerId) => {
        set({ povPlayerId: playerId });
      },

      // UI actions
      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarOpen: (open) => {
        set({ sidebarOpen: open });
      },

      setTheme: (theme) => {
        set({ theme });
        // Apply theme class to document
        const root = document.documentElement;
        root.classList.remove('dark', 'light');
        if (theme === 'system') {
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
          root.classList.add(prefersDark ? 'dark' : 'light');
        } else {
          root.classList.add(theme);
        }
      },

      // Trust matrix actions
      updateTrustMatrix: (snapshots) => {
        const { currentDay, currentPhase, currentTrustMatrix } = get();
        const newMatrix = findTrustSnapshot(snapshots, currentDay, currentPhase);

        // Only animate if we have a previous matrix and it's different
        const hasData = Object.keys(currentTrustMatrix).length > 0;
        const isNewData = JSON.stringify(newMatrix) !== JSON.stringify(currentTrustMatrix);

        if (hasData && isNewData) {
          // Start animation from current to new
          set({
            previousTrustMatrix: currentTrustMatrix,
            currentTrustMatrix: newMatrix,
            animationProgress: 0,
            isAnimating: true,
          });
        } else {
          // No animation needed
          set({
            currentTrustMatrix: newMatrix,
            previousTrustMatrix: newMatrix,
            animationProgress: 1,
            isAnimating: false,
          });
        }
      },

      // Animation actions
      startAnimation: () => {
        set({ isAnimating: true, animationProgress: 0 });
      },

      setAnimationProgress: (progress) => {
        set({ animationProgress: Math.min(1, Math.max(0, progress)) });
        if (progress >= 1) {
          set({ isAnimating: false });
        }
      },

      stopAnimation: () => {
        set({ isAnimating: false, animationProgress: 1 });
      },

      // Playback actions
      togglePlayback: () => {
        set((state) => ({ isPlaying: !state.isPlaying }));
      },

      setPlaybackSpeed: (speed) => {
        set({ playbackSpeed: speed });
      },

      stopPlayback: () => {
        set({ isPlaying: false });
      },

      // Reset actions
      reset: () => {
        set({
          selectedGameId: null,
          selectedPlayerId: null,
          highlightedPlayers: [],
          hoveredPlayerId: null,
          currentDay: 1,
          currentPhase: 'breakfast',
          currentTrustMatrix: {},
          previousTrustMatrix: {},
          animationProgress: 1,
          isAnimating: false,
          isPlaying: false,
        });
      },

      resetTimeline: () => {
        set({
          currentDay: 1,
          currentPhase: 'breakfast',
          isPlaying: false,
        });
      },
    }),
    {
      name: 'traitorsim-ui-store',
      // Only persist view options and theme, not selections
      partialize: (state) => ({
        showRoles: state.showRoles,
        showEliminatedPlayers: state.showEliminatedPlayers,
        trustThreshold: state.trustThreshold,
        viewingMode: state.viewingMode,
        theme: state.theme,
      }),
    }
  )
);

// ============================================================================
// Selector Hooks
// ============================================================================

/**
 * Get current timeline position
 */
export const useTimelinePosition = () =>
  useGameStore((state) => ({
    day: state.currentDay,
    phase: state.currentPhase,
  }));

/**
 * Get view options
 */
export const useViewOptions = () =>
  useGameStore((state) => ({
    showRoles: state.showRoles,
    showEliminatedPlayers: state.showEliminatedPlayers,
    trustThreshold: state.trustThreshold,
    viewingMode: state.viewingMode,
    povPlayerId: state.povPlayerId,
  }));

/**
 * Get selection state
 */
export const useSelection = () =>
  useGameStore((state) => ({
    gameId: state.selectedGameId,
    playerId: state.selectedPlayerId,
    highlightedPlayers: state.highlightedPlayers,
    hoveredPlayerId: state.hoveredPlayerId,
  }));

/**
 * Get UI state
 */
export const useUIState = () =>
  useGameStore((state) => ({
    sidebarOpen: state.sidebarOpen,
    theme: state.theme,
  }));

// Export the phase list for components
export { PHASES };

// Export types
export type { Theme, ViewingMode };
