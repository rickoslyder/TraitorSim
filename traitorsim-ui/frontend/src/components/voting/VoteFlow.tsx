/**
 * VoteFlow - Sankey diagram visualization of voting patterns
 *
 * Shows how votes flow from voters to targets across the game,
 * helping identify voting blocs and suspicious patterns.
 */

import { useMemo, useState } from 'react';
import { ResponsiveSankey } from '@nivo/sankey';
import { motion } from 'framer-motion';
import { Player, GameEvent, getArchetypeColor } from '../../types';
import { useGameStore } from '../../stores/gameStore';

interface VoteFlowProps {
  players: Record<string, Player>;
  events: GameEvent[];
  day?: number;
}

interface SankeyNode {
  id: string;
  nodeColor: string;
}

interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

type ViewMode = 'all' | 'single-day' | 'by-voter' | 'by-target';

export function VoteFlow({ players, events, day }: VoteFlowProps) {
  const { currentDay, showRoles, selectPlayer } = useGameStore();
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [selectedDay, setSelectedDay] = useState<number>(day ?? currentDay);

  // Get all available days with votes
  const daysWithVotes = useMemo(() => {
    const days = new Set<number>();
    events.forEach(e => {
      if (e.type === 'VOTE' || e.type === 'VOTE_TALLY') {
        days.add(e.day);
      }
    });
    return Array.from(days).sort((a, b) => a - b);
  }, [events]);

  // Transform vote events into Sankey data
  const sankeyData = useMemo((): SankeyData => {
    // Filter vote events based on view mode
    let voteEvents = events.filter(e => e.type === 'VOTE');

    if (viewMode === 'single-day') {
      voteEvents = voteEvents.filter(e => e.day === selectedDay);
    } else {
      // For 'all' mode, limit to currentDay
      voteEvents = voteEvents.filter(e => e.day <= currentDay);
    }

    // Build nodes and aggregate votes
    const nodeIds = new Set<string>();
    const voteCounts: Record<string, Record<string, number>> = {};

    voteEvents.forEach(event => {
      const voter = event.actor;
      const target = event.target;

      if (voter && target) {
        nodeIds.add(voter);
        nodeIds.add(target);

        if (!voteCounts[voter]) voteCounts[voter] = {};
        voteCounts[voter][target] = (voteCounts[voter][target] || 0) + 1;
      }
    });

    // Create nodes with player colors
    const nodes: SankeyNode[] = Array.from(nodeIds).map(id => {
      const player = players[id];
      let nodeColor: string;

      if (showRoles && player) {
        nodeColor = player.role === 'TRAITOR' ? '#ef4444' : '#3b82f6';
      } else if (player?.archetype_id) {
        nodeColor = getArchetypeColor(player.archetype_id);
      } else {
        nodeColor = '#6b7280';
      }

      return { id, nodeColor };
    });

    // Create links from vote counts
    const links: SankeyLink[] = [];
    Object.entries(voteCounts).forEach(([voter, targets]) => {
      Object.entries(targets).forEach(([target, count]) => {
        // Skip self-votes (shouldn't happen, but just in case)
        if (voter !== target) {
          links.push({ source: voter, target, value: count });
        }
      });
    });

    return { nodes, links };
  }, [events, players, viewMode, selectedDay, currentDay, showRoles]);

  // Get player name for label
  const getPlayerName = (id: string): string => {
    const player = players[id];
    if (!player) return id;
    // Return first name for shorter labels
    return player.name.split(' ')[0];
  };

  // Empty state
  if (sankeyData.nodes.length === 0 || sankeyData.links.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <span className="text-4xl mb-2">🗳️</span>
        <p>No voting data available</p>
        {viewMode === 'single-day' && (
          <p className="text-sm mt-2">Try selecting a different day or view all days</p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-4 p-4 bg-gray-800 rounded-lg">
        {/* View mode selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">View:</span>
          <select
            value={viewMode}
            onChange={e => setViewMode(e.target.value as ViewMode)}
            className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Days (to current)</option>
            <option value="single-day">Single Day</option>
          </select>
        </div>

        {/* Day selector (only for single-day mode) */}
        {viewMode === 'single-day' && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Day:</span>
            <select
              value={selectedDay}
              onChange={e => setSelectedDay(Number(e.target.value))}
              className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {daysWithVotes.map(d => (
                <option key={d} value={d}>
                  Day {d}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Stats */}
        <div className="ml-auto flex items-center gap-4 text-sm text-gray-400">
          <span>
            {sankeyData.nodes.length} players · {sankeyData.links.length} vote connections
          </span>
        </div>
      </div>

      {/* Sankey diagram */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex-1 min-h-[400px]"
      >
        <ResponsiveSankey
          data={sankeyData}
          margin={{ top: 40, right: 160, bottom: 40, left: 50 }}
          align="justify"
          colors={(node: SankeyNode) => node.nodeColor}
          nodeOpacity={1}
          nodeHoverOpacity={1}
          nodeHoverOthersOpacity={0.35}
          nodeThickness={18}
          nodeSpacing={24}
          nodeBorderWidth={0}
          nodeBorderColor={{ from: 'color', modifiers: [['darker', 0.8]] }}
          nodeBorderRadius={3}
          linkOpacity={0.5}
          linkHoverOpacity={0.8}
          linkHoverOthersOpacity={0.1}
          linkContract={3}
          enableLinkGradient={true}
          labelPosition="outside"
          labelOrientation="horizontal"
          labelPadding={16}
          labelTextColor={{ from: 'color', modifiers: [['brighter', 1]] }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          label={(node: any) => getPlayerName(node.id as string)}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onClick={(data: any) => {
            // Handle node click
            if ('id' in data) {
              selectPlayer(data.id as string);
            }
          }}
          theme={{
            labels: {
              text: {
                fill: '#9ca3af',
                fontSize: 12,
              },
            },
            tooltip: {
              container: {
                background: '#1f2937',
                color: '#f3f4f6',
                fontSize: 12,
                borderRadius: 8,
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
              },
            },
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          nodeTooltip={({ node }: { node: any }) => {
            const player = players[node.id];
            // sourceLinks = links where this node is the source (votes cast)
            // targetLinks = links where this node is the target (votes received)
            const votesCast = node.sourceLinks?.reduce((sum: number, link: { value?: number }) => sum + (link.value || 0), 0) || 0;
            const votesReceived = node.targetLinks?.reduce((sum: number, link: { value?: number }) => sum + (link.value || 0), 0) || 0;

            return (
              <div className="bg-gray-800 px-3 py-2 rounded-lg shadow-lg border border-gray-700">
                <div className="font-medium text-white">{player?.name || node.id}</div>
                {player?.archetype_name && (
                  <div className="text-xs text-gray-400">{player.archetype_name}</div>
                )}
                <div className="mt-2 text-xs space-y-1">
                  <div className="text-green-400">Cast {votesCast} votes</div>
                  <div className="text-red-400">Received {votesReceived} votes</div>
                </div>
                {showRoles && player && (
                  <div className={`mt-2 text-xs font-medium ${
                    player.role === 'TRAITOR' ? 'text-red-400' : 'text-blue-400'
                  }`}>
                    {player.role}
                  </div>
                )}
              </div>
            );
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          linkTooltip={({ link }: { link: any }) => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            const source = players[sourceId as string];
            const target = players[targetId as string];

            return (
              <div className="bg-gray-800 px-3 py-2 rounded-lg shadow-lg border border-gray-700">
                <div className="text-sm text-white">
                  <span className="font-medium">{source?.name || sourceId}</span>
                  <span className="text-gray-400"> voted for </span>
                  <span className="font-medium">{target?.name || targetId}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {link.value} {link.value === 1 ? 'time' : 'times'}
                </div>
              </div>
            );
          }}
        />
      </motion.div>

      {/* Legend */}
      <div className="flex items-center gap-6 p-4 border-t border-gray-700 text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gradient-to-r from-blue-500 to-purple-500" />
          <span>Vote flow (thicker = more votes)</span>
        </div>
        {showRoles && (
          <>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-blue-500" />
              <span>Faithful</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-500" />
              <span>Traitor</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default VoteFlow;
