/**
 * Behavioral Stats Calculator
 *
 * Calculates poker-tracker-style behavioral statistics for players from game events.
 * These stats help viewers understand player tendencies and strategies.
 */

import type { Player, GameEvent, TrustMatrix } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface BehavioralStats {
  // Voting patterns
  votesWithMajority: number; // 0-100%, how often they vote with the winning side
  votesAgainstTraitors: number; // 0-100%, of their banishment votes, how many were actual traitors
  votesForInnocents: number; // 0-100%, of their banishment votes, how many were faithful

  // Mission performance
  missionsParticipated: number;
  missionSuccessRate: number; // 0-100%
  averagePerformanceScore: number; // 0-1, average of their performance scores

  // Social dynamics
  conversationsInitiated: number;
  uniqueConversationPartners: number;
  suspicionReceived: number; // 0-1, average suspicion from others
  suspicionGiven: number; // 0-1, average suspicion they give to others

  // Breakfast order (if available)
  averageBreakfastPosition: number | null; // Average entry order (1 = first, higher = later)
  breakfastVariance: number | null; // How consistent is their order

  // Survival
  daysAlive: number;
  eliminationDay: number | null;

  // Power item usage
  hadShield: boolean;
  hadDagger: boolean;
  wasMurdered: boolean;
  wasBanished: boolean;
}

export interface PlayerTypeClassification {
  type: PlayerType;
  label: string;
  description: string;
  confidence: number; // 0-1, how confident we are in this classification
}

export type PlayerType =
  | 'traitor_angel' // Perfect faithful performance + defensive voting
  | 'paranoid_hunter' // High accusation rate, erratic voting
  | 'silent_follower' // Low participation, majority voting
  | 'strategic_leader' // High influence, coalition building
  | 'chaos_agent' // Unpredictable voting, mission inconsistency
  | 'reliable_voter' // Consistent majority voter
  | 'contrarian' // Often votes against majority
  | 'unknown'; // Not enough data

// ============================================================================
// Vote Analysis
// ============================================================================

/**
 * Calculate voting pattern statistics for a player
 */
export function calculateVotingStats(
  playerId: string,
  events: GameEvent[],
  players: Record<string, Player>
): { votesWithMajority: number; votesAgainstTraitors: number; votesForInnocents: number } {
  // Get all VOTE_TALLY events (which contain complete vote breakdowns)
  const voteTallies = events.filter(e => e.type === 'VOTE_TALLY');

  if (voteTallies.length === 0) {
    return { votesWithMajority: 0, votesAgainstTraitors: 0, votesForInnocents: 0 };
  }

  let votedWithMajority = 0;
  let totalVotes = 0;
  let votedForTraitors = 0;
  let votedForFaithful = 0;
  let relevantVotes = 0;

  for (const tally of voteTallies) {
    const data = tally.data as {
      votes: Record<string, string>;
      eliminated: string;
      eliminated_role?: string;
    };

    if (!data.votes || !data.eliminated) continue;

    // Check if this player voted in this round
    const playerVote = data.votes[playerId];
    if (!playerVote) continue;

    totalVotes++;

    // Did they vote for the eliminated person (majority)?
    if (playerVote === data.eliminated) {
      votedWithMajority++;
    }

    // Track if they voted for a traitor or faithful
    const targetPlayer = players[playerVote];
    if (targetPlayer) {
      relevantVotes++;
      if (targetPlayer.role === 'TRAITOR') {
        votedForTraitors++;
      } else {
        votedForFaithful++;
      }
    }
  }

  return {
    votesWithMajority: totalVotes > 0 ? Math.round((votedWithMajority / totalVotes) * 100) : 0,
    votesAgainstTraitors: relevantVotes > 0 ? Math.round((votedForTraitors / relevantVotes) * 100) : 0,
    votesForInnocents: relevantVotes > 0 ? Math.round((votedForFaithful / relevantVotes) * 100) : 0,
  };
}

// ============================================================================
// Mission Analysis
// ============================================================================

/**
 * Calculate mission participation and performance statistics
 */
export function calculateMissionStats(
  playerId: string,
  events: GameEvent[]
): { missionsParticipated: number; successRate: number; avgPerformance: number } {
  const missionEvents = events.filter(e => e.type === 'MISSION_COMPLETE');

  let participated = 0;
  let successes = 0;
  let totalPerformance = 0;

  for (const mission of missionEvents) {
    const data = mission.data as {
      participants?: string[];
      success?: boolean;
      performance_scores?: Record<string, number>;
    };

    if (!data.participants) continue;

    // Check if player participated
    if (data.participants.includes(playerId)) {
      participated++;

      if (data.success) {
        successes++;
      }

      // Track performance score
      if (data.performance_scores && data.performance_scores[playerId] !== undefined) {
        totalPerformance += data.performance_scores[playerId];
      }
    }
  }

  return {
    missionsParticipated: participated,
    successRate: participated > 0 ? Math.round((successes / participated) * 100) : 0,
    avgPerformance: participated > 0 ? totalPerformance / participated : 0,
  };
}

// ============================================================================
// Social Dynamics Analysis
// ============================================================================

/**
 * Calculate social interaction statistics
 */
export function calculateSocialStats(
  playerId: string,
  events: GameEvent[]
): { conversationsInitiated: number; uniquePartners: number } {
  // Since we don't have explicit CONVERSATION events, we infer social interactions
  // from phase-based activities during social phases and breakfast interactions
  const socialEvents = events.filter(
    e => (e.phase === 'social' || e.phase === 'breakfast') &&
         (e.actor === playerId || e.target === playerId)
  );

  const partners = new Set<string>();
  let initiated = 0;

  for (const event of socialEvents) {
    if (event.actor === playerId) {
      initiated++;
      if (event.target) partners.add(event.target);
    } else if (event.target === playerId && event.actor) {
      partners.add(event.actor);
    }
  }

  // Also count vote events as social interactions (public accusations)
  const voteEvents = events.filter(
    e => e.type === 'VOTE' && (e.actor === playerId || e.target === playerId)
  );

  for (const vote of voteEvents) {
    if (vote.actor === playerId && vote.target) {
      partners.add(vote.target);
    } else if (vote.target === playerId && vote.actor) {
      partners.add(vote.actor);
    }
  }

  return {
    conversationsInitiated: initiated,
    uniquePartners: partners.size,
  };
}

/**
 * Calculate suspicion statistics from trust matrix
 */
export function calculateSuspicionStats(
  playerId: string,
  trustMatrix: TrustMatrix
): { received: number; given: number } {
  let totalReceived = 0;
  let countReceived = 0;
  let totalGiven = 0;
  let countGiven = 0;

  // Suspicion received (how much others suspect this player)
  for (const [observer, targets] of Object.entries(trustMatrix)) {
    if (observer !== playerId && targets[playerId] !== undefined) {
      totalReceived += targets[playerId];
      countReceived++;
    }
  }

  // Suspicion given (how much this player suspects others)
  const playerSuspicions = trustMatrix[playerId];
  if (playerSuspicions) {
    for (const [target, suspicion] of Object.entries(playerSuspicions)) {
      if (target !== playerId) {
        totalGiven += suspicion;
        countGiven++;
      }
    }
  }

  return {
    received: countReceived > 0 ? totalReceived / countReceived : 0,
    given: countGiven > 0 ? totalGiven / countGiven : 0,
  };
}

// ============================================================================
// Breakfast Order Analysis
// ============================================================================

/**
 * Calculate breakfast order statistics (the "breakfast tell")
 */
export function calculateBreakfastStats(
  playerId: string,
  events: GameEvent[]
): { average: number | null; variance: number | null } {
  const breakfastEvents = events.filter(e => e.type === 'BREAKFAST_ORDER');

  if (breakfastEvents.length === 0) {
    return { average: null, variance: null };
  }

  const positions: number[] = [];

  for (const breakfast of breakfastEvents) {
    const data = breakfast.data as { order?: string[] };
    if (!data.order) continue;

    const position = data.order.indexOf(playerId);
    if (position !== -1) {
      positions.push(position + 1); // 1-indexed
    }
  }

  if (positions.length === 0) {
    return { average: null, variance: null };
  }

  const average = positions.reduce((a, b) => a + b, 0) / positions.length;

  // Calculate variance
  const squaredDiffs = positions.map(p => Math.pow(p - average, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / positions.length;

  return { average, variance };
}

// ============================================================================
// Player Type Classification
// ============================================================================

/**
 * Classify a player's behavioral type based on their stats
 */
export function classifyPlayerType(
  player: Player,
  stats: BehavioralStats
): PlayerTypeClassification {
  // Not enough data
  if (stats.daysAlive < 2) {
    return {
      type: 'unknown',
      label: 'Unknown',
      description: 'Not enough data to classify',
      confidence: 0,
    };
  }

  // Traitor Angel: High majority voting + high mission success + is actually traitor
  if (
    player.role === 'TRAITOR' &&
    stats.votesWithMajority >= 70 &&
    stats.missionSuccessRate >= 80 &&
    stats.averagePerformanceScore >= 0.7
  ) {
    return {
      type: 'traitor_angel',
      label: 'Traitor Angel',
      description: 'Perfect faithful performance while secretly a traitor',
      confidence: 0.85,
    };
  }

  // Paranoid Hunter: Low majority voting + high suspicion given
  if (stats.votesWithMajority < 40 && stats.suspicionGiven > 0.6) {
    return {
      type: 'paranoid_hunter',
      label: 'Paranoid Hunter',
      description: 'High accusation rate with erratic voting',
      confidence: 0.7,
    };
  }

  // Silent Follower: High majority voting + low social interaction
  if (stats.votesWithMajority >= 80 && stats.conversationsInitiated < 3) {
    return {
      type: 'silent_follower',
      label: 'Silent Follower',
      description: 'Low participation, follows the crowd',
      confidence: 0.75,
    };
  }

  // Strategic Leader: Many conversations + high influence
  if (
    stats.uniqueConversationPartners >= 5 &&
    stats.conversationsInitiated >= 5 &&
    player.stats?.social_influence >= 0.6
  ) {
    return {
      type: 'strategic_leader',
      label: 'Strategic Leader',
      description: 'High influence, builds coalitions',
      confidence: 0.7,
    };
  }

  // Chaos Agent: Low mission success + erratic voting
  if (stats.missionSuccessRate < 50 && stats.votesWithMajority < 50) {
    return {
      type: 'chaos_agent',
      label: 'Chaos Agent',
      description: 'Unpredictable voting and mission performance',
      confidence: 0.6,
    };
  }

  // Contrarian: Low majority voting but otherwise engaged
  if (stats.votesWithMajority < 40 && stats.conversationsInitiated >= 2) {
    return {
      type: 'contrarian',
      label: 'Contrarian',
      description: 'Often votes against the majority',
      confidence: 0.65,
    };
  }

  // Reliable Voter: High majority voting (default for high conformity)
  if (stats.votesWithMajority >= 60) {
    return {
      type: 'reliable_voter',
      label: 'Reliable Voter',
      description: 'Consistent majority voter',
      confidence: 0.6,
    };
  }

  return {
    type: 'unknown',
    label: 'Unknown',
    description: 'Unclear behavioral pattern',
    confidence: 0.3,
  };
}

// ============================================================================
// Main Calculator
// ============================================================================

/**
 * Calculate all behavioral statistics for a player
 */
export function calculateBehavioralStats(
  player: Player,
  events: GameEvent[],
  players: Record<string, Player>,
  trustMatrix: TrustMatrix
): BehavioralStats {
  const votingStats = calculateVotingStats(player.id, events, players);
  const missionStats = calculateMissionStats(player.id, events);
  const socialStats = calculateSocialStats(player.id, events);
  const suspicionStats = calculateSuspicionStats(player.id, trustMatrix);
  const breakfastStats = calculateBreakfastStats(player.id, events);

  // Determine elimination info
  const wasMurdered = player.elimination_type === 'MURDERED';
  const wasBanished = player.elimination_type === 'BANISHED';

  // Check for power items (from events)
  const shieldEvents = events.filter(e => e.type === 'SHIELD_AWARDED' && e.target === player.id);
  const daggerEvents = events.filter(e => e.type === 'DAGGER_AWARDED' && e.target === player.id);

  // Calculate days alive
  const maxDay = events.reduce((max, e) => Math.max(max, e.day), 0);
  const daysAlive = player.eliminated_day ?? maxDay;

  return {
    // Voting
    votesWithMajority: votingStats.votesWithMajority,
    votesAgainstTraitors: votingStats.votesAgainstTraitors,
    votesForInnocents: votingStats.votesForInnocents,

    // Missions
    missionsParticipated: missionStats.missionsParticipated,
    missionSuccessRate: missionStats.successRate,
    averagePerformanceScore: missionStats.avgPerformance,

    // Social
    conversationsInitiated: socialStats.conversationsInitiated,
    uniqueConversationPartners: socialStats.uniquePartners,
    suspicionReceived: suspicionStats.received,
    suspicionGiven: suspicionStats.given,

    // Breakfast
    averageBreakfastPosition: breakfastStats.average,
    breakfastVariance: breakfastStats.variance,

    // Survival
    daysAlive,
    eliminationDay: player.eliminated_day ?? null,

    // Power items
    hadShield: shieldEvents.length > 0 || player.has_shield === true,
    hadDagger: daggerEvents.length > 0 || player.has_dagger === true,
    wasMurdered,
    wasBanished,
  };
}

// ============================================================================
// Display Helpers
// ============================================================================

/**
 * Format a percentage for display
 */
export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

/**
 * Get color for a stat value (green = good, red = bad for faithful)
 */
export function getStatColor(value: number, invert: boolean = false): string {
  const normalized = invert ? 1 - value / 100 : value / 100;

  if (normalized >= 0.7) return 'text-green-400';
  if (normalized >= 0.4) return 'text-yellow-400';
  return 'text-red-400';
}

/**
 * Get color class for player type
 */
export function getPlayerTypeColor(type: PlayerType): string {
  switch (type) {
    case 'traitor_angel':
      return 'bg-red-500/20 text-red-400 border-red-500/50';
    case 'paranoid_hunter':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
    case 'silent_follower':
      return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
    case 'strategic_leader':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'chaos_agent':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
    case 'reliable_voter':
      return 'bg-green-500/20 text-green-400 border-green-500/50';
    case 'contrarian':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
  }
}
