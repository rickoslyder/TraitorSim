/**
 * Trust Network Graph - Force-directed visualization of player trust relationships
 *
 * Features:
 * - Force-directed layout with D3
 * - Hover to highlight connected nodes
 * - Click to select/focus player
 * - Responsive sizing with ResizeObserver
 * - Role reveal toggle
 */

import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { Player, TrustMatrix, matrixToEdges, getSuspicionColor, getArchetypeColor, interpolateTrust } from '../../types';
import { useGameStore } from '../../stores/gameStore';
import { useContainerSize, useReducedMotion, useTrustAnimation, usePOVVisibility } from '../../hooks';

interface TrustGraphProps {
  players: Record<string, Player>;
  trustMatrix: TrustMatrix;
  width?: number;
  height?: number;
}

interface GraphNode {
  id: string;
  name: string;
  role: string;
  archetype: string;
  alive: boolean;
  socialInfluence: number;
  color: string;
  // D3 force simulation adds these at runtime
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphLink {
  source: string;
  target: string;
  suspicion: number;
  color: string;
}

export function TrustGraph({ players, trustMatrix, width, height }: TrustGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<ForceGraphMethods<any, any>>();

  // Responsive sizing
  const containerSize = useContainerSize(containerRef);
  const reducedMotion = useReducedMotion();

  // Use container size if no explicit dimensions provided
  const graphWidth = width ?? containerSize.width;
  const graphHeight = height ?? containerSize.height;

  const {
    selectedPlayerId,
    selectPlayer,
    hoveredPlayerId,
    setHoveredPlayer,
    showEliminatedPlayers,
    trustThreshold,
    setTrustThreshold,
    currentDay,
    // Animation state
    previousTrustMatrix,
    animationProgress,
    isAnimating,
    setAnimationProgress,
  } = useGameStore();

  // POV-aware visibility for roles
  const { shouldShowRole, shouldRevealTraitor, getVisibleTrust } = usePOVVisibility(players);

  // Pre-compute which nodes should show roles (for canvas rendering efficiency)
  const roleVisibleNodeIds = useMemo(() => {
    const visible = new Set<string>();
    Object.entries(players).forEach(([id, player]) => {
      if (shouldShowRole(player)) {
        visible.add(id);
      }
    });
    return visible;
  }, [players, shouldShowRole]);

  // Pre-compute revealed traitors for highlighting
  const revealedTraitorIds = useMemo(() => {
    const revealed = new Set<string>();
    Object.entries(players).forEach(([id, player]) => {
      if (shouldRevealTraitor(player)) {
        revealed.add(id);
      }
    });
    return revealed;
  }, [players, shouldRevealTraitor]);

  // Apply POV filtering to trust matrix
  const visibleTrustMatrix = useMemo(() => {
    return getVisibleTrust(trustMatrix);
  }, [trustMatrix, getVisibleTrust]);

  // Drive the animation with requestAnimationFrame
  useTrustAnimation(isAnimating, setAnimationProgress, 500);

  // Compute interpolated trust matrix for smooth animation (using POV-filtered matrix)
  const animatedTrustMatrix = useMemo(() => {
    if (!isAnimating || animationProgress >= 1) {
      return visibleTrustMatrix;
    }
    // Interpolate between previous and current (both should be POV-filtered)
    return interpolateTrust(previousTrustMatrix, visibleTrustMatrix, animationProgress);
  }, [previousTrustMatrix, visibleTrustMatrix, animationProgress, isAnimating]);

  // Local hover state for immediate feedback
  const [localHoveredId, setLocalHoveredId] = useState<string | null>(null);
  const hoveredId = localHoveredId || hoveredPlayerId;

  // Calculate connected nodes for hover highlighting (use animated matrix)
  const connectedNodes = useMemo(() => {
    if (!hoveredId || !animatedTrustMatrix) return new Set<string>();

    const connected = new Set<string>();
    connected.add(hoveredId);

    // Add nodes this player suspects (outgoing edges)
    if (animatedTrustMatrix[hoveredId]) {
      Object.entries(animatedTrustMatrix[hoveredId]).forEach(([target, suspicion]) => {
        if (suspicion >= trustThreshold) {
          connected.add(target);
        }
      });
    }

    // Add nodes that suspect this player (incoming edges)
    Object.entries(animatedTrustMatrix).forEach(([observer, targets]) => {
      if (targets[hoveredId] && targets[hoveredId] >= trustThreshold) {
        connected.add(observer);
      }
    });

    return connected;
  }, [hoveredId, animatedTrustMatrix, trustThreshold]);

  // Convert players and trust matrix to graph data (use animated matrix for smooth transitions)
  const graphData = useMemo(() => {
    const nodes: GraphNode[] = [];
    const links: GraphLink[] = [];

    // Create nodes from players
    for (const [id, player] of Object.entries(players)) {
      if (!showEliminatedPlayers && !player.alive) continue;

      // Check if player was alive at current day
      if (player.eliminated_day && player.eliminated_day < currentDay) continue;

      nodes.push({
        id,
        name: player.name,
        role: player.role,
        archetype: player.archetype_id || '',
        alive: player.alive,
        socialInfluence: player.stats?.social_influence || 0.5,
        color: getArchetypeColor(player.archetype_id || ''),
      });
    }

    // Create links from animated trust matrix (smooth transitions)
    const edges = matrixToEdges(animatedTrustMatrix, trustThreshold);
    for (const edge of edges) {
      // Only add link if both nodes exist
      if (nodes.find(n => n.id === edge.source) && nodes.find(n => n.id === edge.target)) {
        links.push({
          source: edge.source,
          target: edge.target,
          suspicion: edge.suspicion,
          color: getSuspicionColor(edge.suspicion),
        });
      }
    }

    return { nodes, links };
  }, [players, animatedTrustMatrix, showEliminatedPlayers, trustThreshold, currentDay]);

  // Handle node click
  const handleNodeClick = useCallback((node: GraphNode) => {
    selectPlayer(node.id === selectedPlayerId ? null : node.id);
  }, [selectPlayer, selectedPlayerId]);

  // Handle node hover
  const handleNodeHover = useCallback((node: GraphNode | null) => {
    const nodeId = node?.id || null;
    setLocalHoveredId(nodeId);
    setHoveredPlayer(nodeId);
  }, [setHoveredPlayer]);

  // Draw custom node
  const drawNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isSelected = node.id === selectedPlayerId;
    const isHovered = node.id === hoveredId;
    const isConnected = connectedNodes.has(node.id);
    const isDimmed = hoveredId && !isConnected && !isSelected;
    const showRole = roleVisibleNodeIds.has(node.id);
    const isRevealedTraitor = revealedTraitorIds.has(node.id);

    const baseRadius = 6 + node.socialInfluence * 6;
    const radius = baseRadius / globalScale;
    const fontSize = 12 / globalScale;

    // Apply dimming for non-connected nodes during hover
    ctx.globalAlpha = isDimmed ? 0.2 : 1;

    // Draw outer ring for selected/hovered/revealed traitor
    if (isSelected || isHovered || isRevealedTraitor) {
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, radius + 3 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = isSelected ? '#3b82f6' : isRevealedTraitor ? '#dc2626' : '#f59e0b';
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI);
    ctx.fillStyle = node.alive ? node.color : '#4b5563';
    ctx.fill();

    // Draw role indicator if role is visible in current POV
    if (showRole) {
      ctx.beginPath();
      ctx.arc(node.x! + radius, node.y! - radius, 4 / globalScale, 0, 2 * Math.PI);
      ctx.fillStyle = node.role === 'TRAITOR' ? '#dc2626' : '#22c55e';
      ctx.fill();
    }

    // Draw elimination X for dead players
    if (!node.alive) {
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2 / globalScale;
      ctx.beginPath();
      ctx.moveTo(node.x! - radius * 0.7, node.y! - radius * 0.7);
      ctx.lineTo(node.x! + radius * 0.7, node.y! + radius * 0.7);
      ctx.moveTo(node.x! + radius * 0.7, node.y! - radius * 0.7);
      ctx.lineTo(node.x! - radius * 0.7, node.y! + radius * 0.7);
      ctx.stroke();
    }

    // Draw name label (only for selected, hovered, or connected during hover)
    if (isSelected || isHovered || !isDimmed) {
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(node.name.split(' ')[0], node.x!, node.y! + radius + 2 / globalScale);
    }

    // Reset alpha
    ctx.globalAlpha = 1;
  }, [selectedPlayerId, hoveredId, connectedNodes, roleVisibleNodeIds, revealedTraitorIds]);

  // Draw custom link
  const drawLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const source = link.source as unknown as GraphNode;
    const target = link.target as unknown as GraphNode;

    if (!source.x || !source.y || !target.x || !target.y) return;

    // Check if link is connected to hovered node
    const isConnectedLink = hoveredId && (
      source.id === hoveredId || target.id === hoveredId
    );
    const isDimmedLink = hoveredId && !isConnectedLink;

    // Apply dimming
    ctx.globalAlpha = isDimmedLink ? 0.1 : 0.6;

    // Draw line with increased width for connected links
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.strokeStyle = link.color;
    ctx.lineWidth = ((isConnectedLink ? 1 : 0.5) + link.suspicion * 2) / globalScale;
    ctx.stroke();

    // Draw arrow (only for connected links when hovering)
    if (!isDimmedLink) {
      const angle = Math.atan2(target.y - source.y, target.x - source.x);
      const arrowLength = 8 / globalScale;
      const arrowX = target.x - Math.cos(angle) * 15 / globalScale;
      const arrowY = target.y - Math.sin(angle) * 15 / globalScale;

      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowLength * Math.cos(angle - Math.PI / 6),
        arrowY - arrowLength * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        arrowX - arrowLength * Math.cos(angle + Math.PI / 6),
        arrowY - arrowLength * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fillStyle = link.color;
      ctx.fill();
    }

    ctx.globalAlpha = 1;
  }, [hoveredId]);

  // Zoom to fit on data change
  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      const timeout = setTimeout(() => {
        graphRef.current?.zoomToFit(reducedMotion ? 0 : 400, 50);
      }, 100);
      return () => clearTimeout(timeout);
    }
  }, [graphData, reducedMotion]);

  // Clear hover on mouse leave
  const handleMouseLeave = useCallback(() => {
    setLocalHoveredId(null);
    setHoveredPlayer(null);
  }, [setHoveredPlayer]);

  const handleResetZoom = useCallback(() => {
    graphRef.current?.zoomToFit(reducedMotion ? 0 : 400, 50);
  }, [reducedMotion]);

  const handleTrustThresholdChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setTrustThreshold(parseFloat(event.target.value));
  }, [setTrustThreshold]);

  if (graphData.nodes.length === 0) {
    return (
      <div ref={containerRef} className="trust-graph-container h-full flex items-center justify-center text-gray-400">
        No players to display
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="trust-graph-container relative h-full w-full"
      onMouseLeave={handleMouseLeave}
    >
      <div
        className="pointer-events-auto absolute left-4 top-4 z-10 w-64 rounded-lg border border-gray-700 bg-gray-900/95 p-4 text-xs text-gray-100 shadow-lg"
        role="region"
        aria-label="Trust graph controls"
      >
        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Legend</h3>
            <ul className="mt-2 space-y-2 text-gray-200">
              <li className="flex items-center gap-2">
                <span className="h-4 w-4 rounded-full border-2 border-blue-400" aria-hidden="true" />
                <span>Node ring: selected/hovered/revealed</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="relative h-4 w-4">
                  <span className="absolute right-0 top-0 h-2.5 w-2.5 rounded-full bg-red-500" aria-hidden="true" />
                </span>
                <span>Role dot: traitor (red) / faithful (green)</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="relative h-4 w-4 text-red-400" aria-hidden="true">
                  ✕
                </span>
                <span>Elimination X: player is out</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-1 w-12 rounded-full bg-gradient-to-r from-emerald-400 via-yellow-400 to-red-500" aria-hidden="true" />
                <span>Link color: low suspicion → high suspicion</span>
              </li>
            </ul>
          </div>
          <div>
            <label htmlFor="trust-threshold" className="text-sm font-medium text-white">
              Trust threshold
            </label>
            <div className="mt-2 flex items-center gap-2">
              <input
                id="trust-threshold"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={trustThreshold}
                onChange={handleTrustThresholdChange}
                className="w-full accent-blue-500"
                aria-valuemin={0}
                aria-valuemax={1}
                aria-valuenow={trustThreshold}
                aria-label="Trust threshold"
              />
              <span className="w-10 text-right tabular-nums text-gray-200" aria-live="polite">
                {trustThreshold.toFixed(2)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleResetZoom}
            className="w-full rounded-md border border-blue-400 px-3 py-2 text-sm font-medium text-blue-100 transition hover:bg-blue-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            aria-label="Reset zoom to fit the graph"
          >
            Reset zoom
          </button>
        </div>
      </div>
      {graphWidth > 0 && graphHeight > 0 && (
        <ForceGraph2D
          ref={graphRef as React.MutableRefObject<ForceGraphMethods<any, any> | undefined>}
          graphData={graphData}
          width={graphWidth}
          height={graphHeight}
          backgroundColor="#1f2937"
          nodeCanvasObject={drawNode}
          linkCanvasObject={drawLink}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          cooldownTicks={reducedMotion ? 0 : 100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          linkDirectionalArrowLength={0}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
        />
      )}
    </div>
  );
}

export default TrustGraph;
