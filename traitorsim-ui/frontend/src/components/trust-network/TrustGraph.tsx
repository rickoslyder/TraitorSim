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
import { Player, TrustMatrix, matrixToEdges, getSuspicionColor, getArchetypeColor } from '../../types';
import { useGameStore } from '../../stores/gameStore';
import { useContainerSize, useReducedMotion } from '../../hooks';

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
    showRoles,
    showEliminatedPlayers,
    trustThreshold,
    currentDay,
  } = useGameStore();

  // Local hover state for immediate feedback
  const [localHoveredId, setLocalHoveredId] = useState<string | null>(null);
  const hoveredId = localHoveredId || hoveredPlayerId;

  // Calculate connected nodes for hover highlighting
  const connectedNodes = useMemo(() => {
    if (!hoveredId || !trustMatrix) return new Set<string>();

    const connected = new Set<string>();
    connected.add(hoveredId);

    // Add nodes this player suspects (outgoing edges)
    if (trustMatrix[hoveredId]) {
      Object.entries(trustMatrix[hoveredId]).forEach(([target, suspicion]) => {
        if (suspicion >= trustThreshold) {
          connected.add(target);
        }
      });
    }

    // Add nodes that suspect this player (incoming edges)
    Object.entries(trustMatrix).forEach(([observer, targets]) => {
      if (targets[hoveredId] && targets[hoveredId] >= trustThreshold) {
        connected.add(observer);
      }
    });

    return connected;
  }, [hoveredId, trustMatrix, trustThreshold]);

  // Convert players and trust matrix to graph data
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

    // Create links from trust matrix
    const edges = matrixToEdges(trustMatrix, trustThreshold);
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
  }, [players, trustMatrix, showEliminatedPlayers, trustThreshold, currentDay]);

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

    const baseRadius = 6 + node.socialInfluence * 6;
    const radius = baseRadius / globalScale;
    const fontSize = 12 / globalScale;

    // Apply dimming for non-connected nodes during hover
    ctx.globalAlpha = isDimmed ? 0.2 : 1;

    // Draw outer ring for selected/hovered node
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, radius + 3 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = isSelected ? '#3b82f6' : '#f59e0b';
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI);
    ctx.fillStyle = node.alive ? node.color : '#4b5563';
    ctx.fill();

    // Draw role indicator if showing roles
    if (showRoles) {
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
  }, [selectedPlayerId, hoveredId, connectedNodes, showRoles]);

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

export default TrustGraph;
