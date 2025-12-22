/**
 * TanStack Query hooks for TraitorSim API
 *
 * These hooks provide automatic caching, background refetching,
 * and proper loading/error states for all API calls.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gamesApi, analysisApi } from './client';
import type { GameSession, GameSummary, Phase } from '../types';

// ============================================================================
// Query Keys - centralized for consistency
// ============================================================================

export const queryKeys = {
  games: {
    all: ['games'] as const,
    list: (limit: number, offset: number) => ['games', 'list', { limit, offset }] as const,
    detail: (id: string) => ['games', id] as const,
  },
  analysis: {
    trustMatrix: (gameId: string, day?: number, phase?: string) =>
      ['games', gameId, 'trust-matrix', { day, phase }] as const,
    events: (gameId: string, filters?: EventFilters) =>
      ['games', gameId, 'events', filters] as const,
    votingPatterns: (gameId: string) =>
      ['games', gameId, 'voting-patterns'] as const,
    trustEvolution: (gameId: string, observerId?: string, targetId?: string) =>
      ['games', gameId, 'trust-evolution', { observerId, targetId }] as const,
    missionPerformance: (gameId: string) =>
      ['games', gameId, 'mission-performance'] as const,
    breakfastAnalysis: (gameId: string) =>
      ['games', gameId, 'breakfast-analysis'] as const,
    playerTimeline: (gameId: string, playerId: string) =>
      ['games', gameId, 'players', playerId, 'timeline'] as const,
  },
};

// ============================================================================
// Types for API responses
// ============================================================================

interface EventFilters {
  day?: number;
  phase?: string;
  eventType?: string;
  playerId?: string;
  limit?: number;
  offset?: number;
}

interface GamesListResponse {
  games: GameSummary[];
  total: number;
  reports_dir: string;
}

interface TrustMatrixResponse {
  day: number;
  phase: string;
  matrix: Record<string, Record<string, number>>;
  alive_count: number;
}

interface EventsResponse {
  events: Array<{
    type: string;
    day: number;
    phase: string;
    actor?: string;
    target?: string;
    data: Record<string, unknown>;
    narrative?: string;
  }>;
  total: number;
  limit?: number;
  offset?: number;
}

interface VotingPatternsResponse {
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

interface TrustEvolutionResponse {
  observer_id?: string;
  target_id?: string;
  evolution?: Array<{ day: number; phase: string; suspicion: number }>;
  target_evolution?: Record<string, Array<{
    day: number;
    phase: string;
    avg_suspicion: number;
    num_observers: number;
  }>>;
  total_snapshots: number;
}

interface MissionPerformanceResponse {
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

interface BreakfastAnalysisResponse {
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

interface PlayerTimelineResponse {
  player: {
    id: string;
    name: string;
    role: string;
    archetype_name?: string;
    alive: boolean;
  };
  events: Array<{
    type: string;
    day: number;
    phase: string;
    actor?: string;
    target?: string;
    data: Record<string, unknown>;
    narrative?: string;
  }>;
  total: number;
}

interface SyncResponse {
  imported: string[];
  count: number;
  reports_dir: string;
}

interface ImportResponse {
  id: string;
  message: string;
}

// ============================================================================
// Game Queries
// ============================================================================

/**
 * Fetch list of all games with pagination
 */
export function useGames(limit = 50, offset = 0) {
  return useQuery({
    queryKey: queryKeys.games.list(limit, offset),
    queryFn: () => gamesApi.list(limit, offset) as Promise<GamesListResponse>,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Fetch full game data by ID
 */
export function useGame(gameId: string | null) {
  return useQuery({
    queryKey: queryKeys.games.detail(gameId || ''),
    queryFn: () => gamesApi.get(gameId!) as Promise<GameSession>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10, // 10 minutes - game data doesn't change
  });
}

// ============================================================================
// Analysis Queries
// ============================================================================

/**
 * Fetch trust matrix for specific day/phase
 */
export function useTrustMatrix(
  gameId: string | null,
  day?: number,
  phase?: Phase
) {
  return useQuery({
    queryKey: queryKeys.analysis.trustMatrix(gameId || '', day, phase),
    queryFn: () => analysisApi.getTrustMatrix(gameId!, day, phase) as Promise<TrustMatrixResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch events with optional filters
 */
export function useEvents(
  gameId: string | null,
  filters?: EventFilters
) {
  return useQuery({
    queryKey: queryKeys.analysis.events(gameId || '', filters),
    queryFn: () => analysisApi.getEvents(gameId!, filters) as Promise<EventsResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch voting patterns analysis
 */
export function useVotingPatterns(gameId: string | null) {
  return useQuery({
    queryKey: queryKeys.analysis.votingPatterns(gameId || ''),
    queryFn: () => analysisApi.getVotingPatterns(gameId!) as Promise<VotingPatternsResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch trust evolution over time
 */
export function useTrustEvolution(
  gameId: string | null,
  observerId?: string,
  targetId?: string
) {
  return useQuery({
    queryKey: queryKeys.analysis.trustEvolution(gameId || '', observerId, targetId),
    queryFn: () => analysisApi.getTrustEvolution(gameId!, observerId, targetId) as Promise<TrustEvolutionResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch mission performance data
 */
export function useMissionPerformance(gameId: string | null) {
  return useQuery({
    queryKey: queryKeys.analysis.missionPerformance(gameId || ''),
    queryFn: () => analysisApi.getMissionPerformance(gameId!) as Promise<MissionPerformanceResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch breakfast order analysis
 */
export function useBreakfastAnalysis(gameId: string | null) {
  return useQuery({
    queryKey: queryKeys.analysis.breakfastAnalysis(gameId || ''),
    queryFn: () => analysisApi.getBreakfastAnalysis(gameId!) as Promise<BreakfastAnalysisResponse>,
    enabled: !!gameId,
    staleTime: 1000 * 60 * 10,
  });
}

/**
 * Fetch player timeline (events involving a specific player)
 */
export function usePlayerTimeline(gameId: string | null, playerId: string | null) {
  return useQuery({
    queryKey: queryKeys.analysis.playerTimeline(gameId || '', playerId || ''),
    queryFn: () => analysisApi.getPlayerTimeline(gameId!, playerId!) as Promise<PlayerTimelineResponse>,
    enabled: !!gameId && !!playerId,
    staleTime: 1000 * 60 * 10,
  });
}

// ============================================================================
// Mutations
// ============================================================================

/**
 * Sync games from filesystem
 */
export function useSyncGames() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => gamesApi.sync() as Promise<SyncResponse>,
    onSuccess: (data) => {
      // Invalidate games list to refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.games.all });
      return data;
    },
  });
}

/**
 * Import a game from JSON file
 */
export function useImportGame() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => gamesApi.import(file) as Promise<ImportResponse>,
    onSuccess: (data) => {
      // Invalidate games list and prefetch the new game
      queryClient.invalidateQueries({ queryKey: queryKeys.games.all });
      return data;
    },
  });
}

/**
 * Refresh all games (sync + clear cache)
 */
export function useRefreshGames() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => gamesApi.refresh(),
    onSuccess: () => {
      // Clear all game-related cache
      queryClient.invalidateQueries({ queryKey: queryKeys.games.all });
    },
  });
}

/**
 * Delete a game
 */
export function useDeleteGame() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (gameId: string) => gamesApi.delete(gameId),
    onSuccess: (_, gameId) => {
      // Remove from cache and invalidate list
      queryClient.removeQueries({ queryKey: queryKeys.games.detail(gameId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.games.all });
    },
  });
}

// ============================================================================
// Utility hooks
// ============================================================================

/**
 * Prefetch a game's data (useful for hover preloading)
 */
export function usePrefetchGame() {
  const queryClient = useQueryClient();

  return (gameId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.games.detail(gameId),
      queryFn: () => gamesApi.get(gameId),
      staleTime: 1000 * 60 * 10,
    });
  };
}
