/**
 * Sidebar session list — automation-friendly native buttons (Playwright / a11y refs).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../../test/utils';
import { Sidebar } from './Sidebar';
import { useGameStore } from '../../stores/gameStore';

const mockGames = {
  games: [
    {
      id: 'game_20260104_012251',
      name: 'Game 2026-01-04 01:22',
      total_days: 11,
      winner: 'FAITHFUL',
    },
  ],
  total: 1,
  reports_dir: '/data',
};

vi.mock('../runner/GameRunner', () => ({
  GameRunner: () => null,
}));

vi.mock('../../api/hooks', () => ({
  useGames: () => ({
    data: mockGames,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  usePrefetchGame: () => vi.fn(),
  useRunStatus: () => ({ data: { running: false } }),
}));

describe('Sidebar game sessions', () => {
  beforeEach(() => {
    useGameStore.setState({
      selectedGameId: null,
      sidebarOpen: true,
    });
  });

  it('exposes data-testid per session and selects on click', () => {
    render(<Sidebar />);

    const btn = screen.getByTestId('game-session-game_20260104_012251');
    expect(btn).toHaveAttribute('type', 'button');
    expect(btn).toHaveAttribute('aria-label', 'Select game: Game 2026-01-04 01:22');

    fireEvent.click(btn);

    expect(useGameStore.getState().selectedGameId).toBe('game_20260104_012251');
    expect(btn).toHaveAttribute('aria-pressed', 'true');
  });
});