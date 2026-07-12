/**
 * Castle broadcast panel — UE projection operator affordance.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../test/utils';
import { CastleBroadcastPanel } from './CastleBroadcastPanel';
import { useWorldProjection } from '../../api/hooks';

vi.mock('../../api/hooks', () => ({
  useWorldProjection: vi.fn(),
}));

const mockUseWorldProjection = vi.mocked(useWorldProjection);

function projectionQuery(value: unknown) {
  return value as ReturnType<typeof useWorldProjection>;
}

describe('CastleBroadcastPanel', () => {
  beforeEach(() => {
    mockUseWorldProjection.mockReset();
    mockUseWorldProjection.mockReturnValue(
      projectionQuery({ data: null, isLoading: false, isError: false })
    );
  });

  it('renders an operator prompt before a session exists', () => {
    render(<CastleBroadcastPanel />);

    expect(screen.getByTestId('castle-broadcast-empty')).toBeInTheDocument();
    expect(screen.getByText(/Start a run/i)).toBeInTheDocument();
    expect(mockUseWorldProjection).toHaveBeenCalledWith(undefined, false);
  });

  it('shows the session id and UE polling URL when a session exists', () => {
    render(<CastleBroadcastPanel sessionId="game_20260712_010203" isRunning />);

    expect(screen.getByTestId('castle-broadcast-panel')).toBeInTheDocument();
    expect(screen.getByText('game_20260712_010203')).toBeInTheDocument();
    expect(
      screen.getByText(
        'https://traitorsim.rbnk.uk/api/sessions/game_20260712_010203/projection/world'
      )
    ).toBeInTheDocument();
    expect(mockUseWorldProjection).toHaveBeenCalledWith('game_20260712_010203', true);
  });

  it('distinguishes a missing snapshot from a request failure', () => {
    mockUseWorldProjection.mockReturnValue(
      projectionQuery({ data: null, isLoading: false, isError: false })
    );

    render(<CastleBroadcastPanel sessionId="game_waiting" isRunning />);

    expect(screen.getByText('Waiting for projection snapshot/report…')).toBeInTheDocument();
    expect(screen.queryByText('Projection request failed.')).not.toBeInTheDocument();
  });

  it('renders a compact world projection summary', () => {
    mockUseWorldProjection.mockReturnValue(
      projectionQuery({
        data: {
          schema_version: 'v1',
          session_id: 'game_live',
          day: 3,
          phase: 'round_table',
          location_id: 'round_table',
          prize_pot: 47280.49,
          alive_count: 2,
          players: [
            {
              id: 'player_00',
              display_name: 'Rae Sinclair',
              alive: true,
              seat_index: 0,
              role_visible: 'traitor',
            },
            {
              id: 'player_01',
              display_name: 'Gemma Ashworth-Clarke',
              alive: true,
              seat_index: 1,
              role_visible: 'faithful',
            },
          ],
        },
        isLoading: false,
        isError: false,
      })
    );

    render(<CastleBroadcastPanel sessionId="game_live" isRunning />);

    expect(screen.getByText(/Phase/)).toBeInTheDocument();
    expect(screen.getAllByText(/round_table/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/47,280/)).toBeInTheDocument();
    expect(screen.getByText(/Alive/)).toBeInTheDocument();
    expect(screen.getByText(/Rae Sinclair/)).toBeInTheDocument();
    expect(screen.getByText(/Gemma Ashworth-Clarke/)).toBeInTheDocument();
  });
});
