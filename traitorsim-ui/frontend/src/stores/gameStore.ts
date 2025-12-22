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

  // UI state
  sidebarOpen: boolean;
  theme: Theme;

  // Computed trust matrix (derived from snapshots + timeline position)
  currentTrustMatrix: TrustMatrix;

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

  // Actions - UI
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;

  // Actions - Trust Matrix
  updateTrustMatrix: (snapshots: TrustSnapshot[]) => void;

  // Actions - Reset
  reset: () => void;
  resetTimeline: () => void;
}

// ============================================================================
// Constants
// ============================================================================

const PHASES: Phase[] = ['breakfast', 'mission', 'social', 'roundtable', 'turret'];

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

  // Find exact match first
  const exact = snapshots.find(s => s.day === day && s.phase === phase);
  if (exact) return exact.matrix;

  // Find closest previous snapshot
  const phaseIndex = PHASES.indexOf(phase);
  for (let d = day; d >= 1; d--) {
    const startPhase = d === day ? phaseIndex : PHASES.length - 1;
    for (let p = startPhase; p >= 0; p--) {
      const snapshot = snapshots.find(s => s.day === d && s.phase === PHASES[p]);
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
      sidebarOpen: false,
      theme: 'dark',
      currentTrustMatrix: {},

      // Selection actions
      selectGame: (id) => {
        set({
          selectedGameId: id,
          selectedPlayerId: null,
          highlightedPlayers: [],
          currentDay: 1,
          currentPhase: 'breakfast',
          currentTrustMatrix: {},
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
        const { currentDay, currentPhase } = get();
        const matrix = findTrustSnapshot(snapshots, currentDay, currentPhase);
        set({ currentTrustMatrix: matrix });
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
        });
      },

      resetTimeline: () => {
        set({
          currentDay: 1,
          currentPhase: 'breakfast',
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

// Export the Theme type
export type { Theme };
