/**
 * Tests for the game store
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useGameStore } from './gameStore';
import type { TrustSnapshot } from '../types';

describe('gameStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useGameStore.getState().reset();
    // Reset persisted state
    localStorage.clear();
  });

  describe('selectGame', () => {
    it('should select a game and reset related state', () => {
      const store = useGameStore.getState();

      // Set some state first
      store.selectPlayer('player-1');
      store.highlightPlayer('player-2');
      store.setTimelinePosition(5, 'roundtable');

      // Select a new game
      store.selectGame('game-123');

      const state = useGameStore.getState();
      expect(state.selectedGameId).toBe('game-123');
      expect(state.selectedPlayerId).toBeNull();
      expect(state.highlightedPlayers).toHaveLength(0);
      expect(state.currentDay).toBe(1);
      expect(state.currentPhase).toBe('breakfast');
    });

    it('should allow deselecting a game', () => {
      const store = useGameStore.getState();
      store.selectGame('game-123');
      store.selectGame(null);

      expect(useGameStore.getState().selectedGameId).toBeNull();
    });
  });

  describe('selectPlayer', () => {
    it('should select a player', () => {
      const store = useGameStore.getState();
      store.selectPlayer('player-1');

      expect(useGameStore.getState().selectedPlayerId).toBe('player-1');
    });

    it('should allow deselecting a player', () => {
      const store = useGameStore.getState();
      store.selectPlayer('player-1');
      store.selectPlayer(null);

      expect(useGameStore.getState().selectedPlayerId).toBeNull();
    });
  });

  describe('highlightPlayer', () => {
    it('should add player to highlights', () => {
      const store = useGameStore.getState();
      store.highlightPlayer('player-1');
      store.highlightPlayer('player-2');

      expect(useGameStore.getState().highlightedPlayers).toEqual([
        'player-1',
        'player-2',
      ]);
    });

    it('should not duplicate highlights', () => {
      const store = useGameStore.getState();
      store.highlightPlayer('player-1');
      store.highlightPlayer('player-1');

      expect(useGameStore.getState().highlightedPlayers).toEqual(['player-1']);
    });
  });

  describe('unhighlightPlayer', () => {
    it('should remove player from highlights', () => {
      const store = useGameStore.getState();
      store.highlightPlayer('player-1');
      store.highlightPlayer('player-2');
      store.unhighlightPlayer('player-1');

      expect(useGameStore.getState().highlightedPlayers).toEqual(['player-2']);
    });
  });

  describe('timeline navigation', () => {
    it('should set timeline position', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(3, 'mission');

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(3);
      expect(state.currentPhase).toBe('mission');
    });

    it('should navigate to next phase within same day', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(1, 'breakfast');
      store.nextPhase(10);

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(1);
      expect(state.currentPhase).toBe('mission');
    });

    it('should navigate to first phase of next day at end of day', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(1, 'turret');
      store.nextPhase(10);

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(2);
      expect(state.currentPhase).toBe('breakfast');
    });

    it('should not go past the last day', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(10, 'turret');
      store.nextPhase(10);

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(10);
      expect(state.currentPhase).toBe('turret');
    });

    it('should navigate to previous phase within same day', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(1, 'mission');
      store.prevPhase();

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(1);
      expect(state.currentPhase).toBe('breakfast');
    });

    it('should navigate to last phase of previous day at start of day', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(2, 'breakfast');
      store.prevPhase();

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(1);
      expect(state.currentPhase).toBe('turret');
    });

    it('should not go before day 1', () => {
      const store = useGameStore.getState();
      store.setTimelinePosition(1, 'breakfast');
      store.prevPhase();

      const state = useGameStore.getState();
      expect(state.currentDay).toBe(1);
      expect(state.currentPhase).toBe('breakfast');
    });
  });

  describe('view options', () => {
    it('should toggle role reveal', () => {
      const store = useGameStore.getState();
      expect(useGameStore.getState().showRoles).toBe(false);

      store.toggleRoleReveal();
      expect(useGameStore.getState().showRoles).toBe(true);

      store.toggleRoleReveal();
      expect(useGameStore.getState().showRoles).toBe(false);
    });

    it('should toggle show eliminated', () => {
      const store = useGameStore.getState();
      expect(useGameStore.getState().showEliminatedPlayers).toBe(true);

      store.toggleShowEliminated();
      expect(useGameStore.getState().showEliminatedPlayers).toBe(false);
    });

    it('should set trust threshold', () => {
      const store = useGameStore.getState();
      store.setTrustThreshold(0.5);

      expect(useGameStore.getState().trustThreshold).toBe(0.5);
    });
  });

  describe('sidebar and theme', () => {
    it('should toggle sidebar', () => {
      const store = useGameStore.getState();
      expect(useGameStore.getState().sidebarOpen).toBe(false);

      store.toggleSidebar();
      expect(useGameStore.getState().sidebarOpen).toBe(true);

      store.toggleSidebar();
      expect(useGameStore.getState().sidebarOpen).toBe(false);
    });

    it('should set sidebar open state', () => {
      const store = useGameStore.getState();
      store.setSidebarOpen(true);
      expect(useGameStore.getState().sidebarOpen).toBe(true);

      store.setSidebarOpen(false);
      expect(useGameStore.getState().sidebarOpen).toBe(false);
    });

    it('should set theme and apply to document', () => {
      const store = useGameStore.getState();
      const root = document.documentElement;

      store.setTheme('light');
      expect(useGameStore.getState().theme).toBe('light');
      expect(root.classList.contains('light')).toBe(true);
      expect(root.classList.contains('dark')).toBe(false);

      store.setTheme('dark');
      expect(useGameStore.getState().theme).toBe('dark');
      expect(root.classList.contains('dark')).toBe(true);
      expect(root.classList.contains('light')).toBe(false);
    });
  });

  describe('updateTrustMatrix', () => {
    it('should find exact matching snapshot', () => {
      const store = useGameStore.getState();
      const snapshots: TrustSnapshot[] = [
        { day: 1, phase: 'breakfast', matrix: { p1: { p2: 0.5 } } },
        { day: 1, phase: 'roundtable', matrix: { p1: { p2: 0.7 } } },
        { day: 2, phase: 'breakfast', matrix: { p1: { p2: 0.9 } } },
      ];

      store.setTimelinePosition(1, 'roundtable');
      store.updateTrustMatrix(snapshots);

      expect(useGameStore.getState().currentTrustMatrix).toEqual({ p1: { p2: 0.7 } });
    });

    it('should find closest previous snapshot if no exact match', () => {
      const store = useGameStore.getState();
      const snapshots: TrustSnapshot[] = [
        { day: 1, phase: 'breakfast', matrix: { p1: { p2: 0.5 } } },
        { day: 2, phase: 'roundtable', matrix: { p1: { p2: 0.9 } } },
      ];

      // Set to mission phase day 1, should find breakfast snapshot
      store.setTimelinePosition(1, 'mission');
      store.updateTrustMatrix(snapshots);

      expect(useGameStore.getState().currentTrustMatrix).toEqual({ p1: { p2: 0.5 } });
    });

    it('should return empty matrix if no snapshots', () => {
      const store = useGameStore.getState();
      store.updateTrustMatrix([]);

      expect(useGameStore.getState().currentTrustMatrix).toEqual({});
    });
  });
});
