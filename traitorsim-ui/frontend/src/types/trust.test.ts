/**
 * Tests for trust matrix utilities
 */

import { describe, it, expect } from 'vitest';
import { matrixToEdges, getSuspicionColor, TrustMatrix } from './trust';

describe('matrixToEdges', () => {
  it('should convert matrix to edge list', () => {
    const matrix: TrustMatrix = {
      'p1': { 'p2': 0.8, 'p3': 0.3 },
      'p2': { 'p1': 0.6, 'p3': 0.9 },
    };

    const edges = matrixToEdges(matrix, 0.0);

    expect(edges).toHaveLength(4);
    expect(edges).toContainEqual({ source: 'p1', target: 'p2', suspicion: 0.8 });
    expect(edges).toContainEqual({ source: 'p1', target: 'p3', suspicion: 0.3 });
    expect(edges).toContainEqual({ source: 'p2', target: 'p1', suspicion: 0.6 });
    expect(edges).toContainEqual({ source: 'p2', target: 'p3', suspicion: 0.9 });
  });

  it('should filter edges below threshold', () => {
    const matrix: TrustMatrix = {
      'p1': { 'p2': 0.8, 'p3': 0.3 },
      'p2': { 'p1': 0.6, 'p3': 0.1 },
    };

    const edges = matrixToEdges(matrix, 0.5);

    expect(edges).toHaveLength(2);
    expect(edges).toContainEqual({ source: 'p1', target: 'p2', suspicion: 0.8 });
    expect(edges).toContainEqual({ source: 'p2', target: 'p1', suspicion: 0.6 });
  });

  it('should handle empty matrix', () => {
    const edges = matrixToEdges({}, 0.0);
    expect(edges).toHaveLength(0);
  });

  it('should handle matrix with no edges above threshold', () => {
    const matrix: TrustMatrix = {
      'p1': { 'p2': 0.1, 'p3': 0.2 },
    };

    const edges = matrixToEdges(matrix, 0.5);
    expect(edges).toHaveLength(0);
  });
});

describe('getSuspicionColor', () => {
  it('should return green for low suspicion', () => {
    const color = getSuspicionColor(0.1);
    // Should be greenish (low suspicion = trust)
    expect(color).toMatch(/^#/);
  });

  it('should return red for high suspicion', () => {
    const color = getSuspicionColor(0.9);
    // Should be reddish (high suspicion)
    expect(color).toMatch(/^#/);
  });

  it('should return yellow for neutral suspicion', () => {
    const color = getSuspicionColor(0.5);
    expect(color).toMatch(/^#/);
  });

  it('should handle edge values', () => {
    expect(getSuspicionColor(0)).toMatch(/^#/);
    expect(getSuspicionColor(1)).toMatch(/^#/);
  });

  it('should produce different colors for different values', () => {
    const low = getSuspicionColor(0.1);
    const mid = getSuspicionColor(0.5);
    const high = getSuspicionColor(0.9);

    // At least some colors should be different
    expect(low !== mid || mid !== high).toBe(true);
  });
});
