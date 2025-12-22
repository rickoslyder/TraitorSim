/**
 * Trust matrix types
 */

export interface TrustSnapshot {
  day: number;
  phase: string;
  alive_count?: number;  // Number of alive players at time of snapshot
  matrix: TrustMatrix;
}

// TrustMatrix: observer -> target -> suspicion score (0.0 = trust, 1.0 = suspect)
export type TrustMatrix = Record<string, Record<string, number>>;

export interface TrustEdge {
  source: string;
  target: string;
  suspicion: number;
  delta?: number; // Change since last snapshot
}

/**
 * Convert trust matrix to edge list for graph visualization
 */
export function matrixToEdges(
  matrix: TrustMatrix,
  threshold: number = 0.1
): TrustEdge[] {
  const edges: TrustEdge[] = [];

  for (const [observer, targets] of Object.entries(matrix)) {
    for (const [target, suspicion] of Object.entries(targets)) {
      if (suspicion >= threshold && observer !== target) {
        edges.push({ source: observer, target, suspicion });
      }
    }
  }

  return edges;
}

/**
 * Get suspicion color based on value (0 = green, 0.5 = yellow, 1 = red)
 */
export function getSuspicionColor(suspicion: number): string {
  if (suspicion < 0.3) return '#22c55e'; // Green - trust
  if (suspicion < 0.5) return '#84cc16'; // Light green
  if (suspicion < 0.7) return '#eab308'; // Yellow - neutral
  if (suspicion < 0.85) return '#f97316'; // Orange - suspicious
  return '#ef4444'; // Red - certain traitor
}

/**
 * Get average suspicion of a player (how suspicious others are of them)
 */
export function getAverageSuspicion(
  matrix: TrustMatrix,
  playerId: string
): number {
  let total = 0;
  let count = 0;

  for (const [observer, targets] of Object.entries(matrix)) {
    if (observer !== playerId && targets[playerId] !== undefined) {
      total += targets[playerId];
      count++;
    }
  }

  return count > 0 ? total / count : 0;
}

/**
 * Interpolate between two trust matrices for smooth animation
 */
export function interpolateTrust(
  matrix1: TrustMatrix,
  matrix2: TrustMatrix,
  t: number // 0.0 to 1.0
): TrustMatrix {
  const result: TrustMatrix = {};

  // Get all observers from both matrices
  const observers = new Set([
    ...Object.keys(matrix1),
    ...Object.keys(matrix2),
  ]);

  for (const observer of observers) {
    result[observer] = {};
    const targets1 = matrix1[observer] || {};
    const targets2 = matrix2[observer] || {};

    const allTargets = new Set([
      ...Object.keys(targets1),
      ...Object.keys(targets2),
    ]);

    for (const target of allTargets) {
      const v1 = targets1[target] ?? 0.5;
      const v2 = targets2[target] ?? 0.5;
      result[observer][target] = v1 + (v2 - v1) * t;
    }
  }

  return result;
}
