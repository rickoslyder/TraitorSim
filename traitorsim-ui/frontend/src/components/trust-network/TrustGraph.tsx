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
import type { Player } from '../../types/player';
import type { TrustMatrix } from '../../types/trust';
import { matrixToEdges, getSuspicionColor, interpolateTrust } from '../../types/trust';
import { getArchetypeColor } from '../../types/player';
import { useGameStore } from '../../stores/gameStore';
import { useContainerSize, useReducedMotion, useTrustAnimation } from '../../hooks/useContainerSize';
import { usePOVVisibility } from '../../hooks/usePOVVisibility';

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

  // Loading skeleton while data is being prepared
  const isLoading = Object.keys(players).length > 0 && graphData.nodes.length === 0 && showEliminatedPlayers;

  if (graphData.nodes.length === 0 && !isLoading) {
    return (
      <div ref={containerRef} className="trust-graph-container h-full flex items-center justify-center text-gray-400">
        No players to display
      </div>
    );
  }

  if (isLoading || (graphWidth === 0 && graphHeight === 0)) {
    return (
      <div ref={containerRef} className="trust-graph-container h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          {/* Skeleton loading animation */}
          <div className="relative w-48 h-48">
            {/* Animated circles representing nodes */}
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="absolute w-8 h-8 rounded-full bg-gray-700 animate-pulse"
                style={{
                  left: `${50 + 35 * Math.cos((i * Math.PI * 2) / 6)}%`,
                  top: `${50 + 35 * Math.sin((i * Math.PI * 2) / 6)}%`,
                  transform: 'translate(-50%, -50%)',
                  animationDelay: `${i * 100}ms`,
                }}
              />
            ))}
            {/* Center node */}
            <div
              className="absolute w-10 h-10 rounded-full bg-gray-600 animate-pulse left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2"
            />
          </div>
          <span className="text-gray-400 text-sm">Loading trust network...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="trust-graph-container h-full w-full"
      onMouseLeave={handleMouseLeave}
    >
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

export default React.memo(TrustGraph);
