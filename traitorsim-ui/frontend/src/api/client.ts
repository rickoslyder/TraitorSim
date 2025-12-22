/**
 * API client for TraitorSim backend
 *
 * This module provides type-safe API calls to the FastAPI backend.
 * All response types are properly defined - no 'unknown' types.
 */

import type {
  GameSession,
  GameSummary,
  GameEvent,
  Player,
  TrustMatrix,
  Phase,
} from '../types';

const API_BASE = '/api';

// ============================================================================
// Error Handling
// ============================================================================

export interface ApiError {
  detail: string;
  status: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw { detail: error.detail || 'Request failed', status: response.status } as ApiError;
  }
  return response.json();
}

// ============================================================================
// Response Types - Properly typed (no 'unknown')
// ============================================================================

export interface GamesListResponse {
  games: GameSummary[];
  total: number;
  reports_dir: string;
}

export interface TrustMatrixResponse {
  day: number;
  phase: Phase;
  matrix: TrustMatrix;
  alive_count: number;
}

export interface EventFilters {
  day?: number;
  phase?: string;
  eventType?: string;
  playerId?: string;
  limit?: number;
  offset?: number;
}

export interface EventsResponse {
  events: GameEvent[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface PlayerTimelineResponse {
  player: Player;
  events: GameEvent[];
  total: number;
}

export interface VotingPatternsResponse {
  vote_matrix: Record<string, Record<string, number>>;
  votes_received: Record<string, number>;
  total_voting_rounds: number;
  banishments: Array<{
    day: number;
    player_id: string;
    player_name: string;
    role: string;
  }>;
  traitor_voters: Record<string, number>;
}

export interface TrustEvolutionResponse {
  observer_id?: string;
  target_id?: string;
  evolution?: Array<{
    day: number;
    phase: Phase;
    suspicion: number;
  }>;
  target_evolution?: Record<string, Array<{
    day: number;
    phase: Phase;
    avg_suspicion: number;
    num_observers: number;
  }>>;
  total_snapshots: number;
}

export interface MissionPerformanceResponse {
  missions: Array<{
    day: number;
    mission_name: string;
    success: boolean;
    success_rate: number;
    earnings: number;
    top_performers: Array<[string, number]>;
  }>;
  player_avg_scores: Record<string, number>;
  total_missions: number;
}

export interface BreakfastAnalysisResponse {
  days: Array<{
    day: number;
    entry_order: string[];
    last_to_arrive: string;
    victim_revealed?: string;
  }>;
  last_arrivals: Record<string, number>;
  suspicious_patterns: Array<{
    player_id: string;
    player_name: string;
    times_last: number;
    role: string;
  }>;
  total_days: number;
}

export interface SyncResponse {
  imported: string[];
  count: number;
  reports_dir: string;
}

export interface ImportResponse {
  id: string;
  message: string;
}

export interface RefreshResponse {
  message: string;
  imported: string[];
  imported_count: number;
  total_games: number;
  reports_dir: string;
}

export interface DeleteResponse {
  message: string;
}

// ============================================================================
// Games API
// ============================================================================

export const gamesApi = {
  /**
   * List all games with pagination
   */
  async list(limit: number = 50, offset: number = 0): Promise<GamesListResponse> {
    const response = await fetch(`${API_BASE}/games?limit=${limit}&offset=${offset}`);
    return handleResponse<GamesListResponse>(response);
  },

  /**
   * Get full game data by ID
   */
  async get(id: string): Promise<GameSession> {
    const response = await fetch(`${API_BASE}/games/${id}`);
    return handleResponse<GameSession>(response);
  },

  /**
   * Sync games from filesystem reports directory
   */
  async sync(): Promise<SyncResponse> {
    const response = await fetch(`${API_BASE}/games/sync`, {
      method: 'POST',
    });
    return handleResponse<SyncResponse>(response);
  },

  /**
   * Import a game from JSON file upload
   */
  async import(file: File): Promise<ImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/games/import`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ImportResponse>(response);
  },

  /**
   * Force refresh: sync + clear cache
   */
  async refresh(): Promise<RefreshResponse> {
    const response = await fetch(`${API_BASE}/games/refresh`, {
      method: 'POST',
    });
    return handleResponse<RefreshResponse>(response);
  },

  /**
   * Delete a game from database
   */
  async delete(id: string): Promise<DeleteResponse> {
    const response = await fetch(`${API_BASE}/games/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<DeleteResponse>(response);
  },
};

// ============================================================================
// Analysis API
// ============================================================================

export const analysisApi = {
  /**
   * Get trust matrix at specific day/phase
   */
  async getTrustMatrix(
    gameId: string,
    day?: number,
    phase?: string
  ): Promise<TrustMatrixResponse> {
    const params = new URLSearchParams();
    if (day !== undefined) params.append('day', day.toString());
    if (phase) params.append('phase', phase);

    const response = await fetch(`${API_BASE}/games/${gameId}/trust-matrix?${params}`);
    return handleResponse<TrustMatrixResponse>(response);
  },

  /**
   * Get events with optional filters
   */
  async getEvents(
    gameId: string,
    filters?: EventFilters
  ): Promise<EventsResponse> {
    const params = new URLSearchParams();
    if (filters?.day !== undefined) params.append('day', filters.day.toString());
    if (filters?.phase) params.append('phase', filters.phase);
    if (filters?.eventType) params.append('event_type', filters.eventType);
    if (filters?.playerId) params.append('player_id', filters.playerId);
    if (filters?.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters?.offset !== undefined) params.append('offset', filters.offset.toString());

    const response = await fetch(`${API_BASE}/games/${gameId}/events?${params}`);
    return handleResponse<EventsResponse>(response);
  },

  /**
   * Get player's event timeline
   */
  async getPlayerTimeline(
    gameId: string,
    playerId: string
  ): Promise<PlayerTimelineResponse> {
    const response = await fetch(`${API_BASE}/games/${gameId}/players/${playerId}/timeline`);
    return handleResponse<PlayerTimelineResponse>(response);
  },

  /**
   * Get voting patterns analysis
   */
  async getVotingPatterns(gameId: string): Promise<VotingPatternsResponse> {
    const response = await fetch(`${API_BASE}/games/${gameId}/voting-patterns`);
    return handleResponse<VotingPatternsResponse>(response);
  },

  /**
   * Get trust evolution over time
   */
  async getTrustEvolution(
    gameId: string,
    observerId?: string,
    targetId?: string
  ): Promise<TrustEvolutionResponse> {
    const params = new URLSearchParams();
    if (observerId) params.append('observer_id', observerId);
    if (targetId) params.append('target_id', targetId);

    const response = await fetch(`${API_BASE}/games/${gameId}/trust-evolution?${params}`);
    return handleResponse<TrustEvolutionResponse>(response);
  },

  /**
   * Get mission performance data
   */
  async getMissionPerformance(gameId: string): Promise<MissionPerformanceResponse> {
    const response = await fetch(`${API_BASE}/games/${gameId}/mission-performance`);
    return handleResponse<MissionPerformanceResponse>(response);
  },

  /**
   * Get breakfast order analysis
   */
  async getBreakfastAnalysis(gameId: string): Promise<BreakfastAnalysisResponse> {
    const response = await fetch(`${API_BASE}/games/${gameId}/breakfast-analysis`);
    return handleResponse<BreakfastAnalysisResponse>(response);
  },

  /**
   * Get specific player data
   */
  async getPlayer(gameId: string, playerId: string): Promise<Player> {
    const response = await fetch(`${API_BASE}/games/${gameId}/players/${playerId}`);
    return handleResponse<Player>(response);
  },
};
