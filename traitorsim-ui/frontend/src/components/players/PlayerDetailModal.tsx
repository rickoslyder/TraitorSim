/**
 * PlayerDetailModal - Full player profile with tabs for Profile, Trust, Events
 *
 * Shows comprehensive player information including:
 * - Demographics and backstory
 * - OCEAN personality traits
 * - Stats (intellect, dexterity, etc.)
 * - Trust relationships (who they suspect, who suspects them)
 * - Event timeline
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Player, TrustMatrix, GameEvent, getArchetypeColor, getSuspicionColor } from '../../types';
import { useGameStore } from '../../stores/gameStore';
import { useReducedMotion } from '../../hooks';

interface PlayerDetailModalProps {
  player: Player;
  players: Record<string, Player>;
  events: GameEvent[];
  trustMatrix: TrustMatrix;
  onClose: () => void;
}

type Tab = 'profile' | 'trust' | 'events';

export function PlayerDetailModal({
  player,
  players,
  events,
  trustMatrix,
  onClose,
}: PlayerDetailModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const { showRoles, setTimelinePosition } = useGameStore();
  const reducedMotion = useReducedMotion();

  // Filter events involving this player
  const playerEvents = useMemo(() => {
    return events.filter(e =>
      e.actor === player.id ||
      e.target === player.id ||
      (e.data?.participants as string[])?.includes(player.id) ||
      (e.data?.votes as Record<string, string>)?.[player.id] ||
      Object.values((e.data?.votes as Record<string, string>) || {}).includes(player.id)
    ).sort((a, b) => b.day - a.day);
  }, [events, player.id]);

  // Get trust relationships
  const trustRelationships = useMemo(() => {
    // Who this player suspects
    const suspects: { playerId: string; name: string; suspicion: number; role: string }[] = [];
    if (trustMatrix[player.id]) {
      Object.entries(trustMatrix[player.id]).forEach(([targetId, suspicion]) => {
        const target = players[targetId];
        if (target) {
          suspects.push({
            playerId: targetId,
            name: target.name,
            suspicion,
            role: target.role,
          });
        }
      });
    }
    suspects.sort((a, b) => b.suspicion - a.suspicion);

    // Who suspects this player
    const suspectedBy: { playerId: string; name: string; suspicion: number; role: string }[] = [];
    Object.entries(trustMatrix).forEach(([observerId, targets]) => {
      if (observerId !== player.id && targets[player.id] !== undefined) {
        const observer = players[observerId];
        if (observer) {
          suspectedBy.push({
            playerId: observerId,
            name: observer.name,
            suspicion: targets[player.id],
            role: observer.role,
          });
        }
      }
    });
    suspectedBy.sort((a, b) => b.suspicion - a.suspicion);

    return { suspects, suspectedBy };
  }, [trustMatrix, player.id, players]);

  // OCEAN traits for radar visualization
  const oceanTraits = [
    { key: 'O', label: 'Openness', value: player.personality?.openness ?? 0.5 },
    { key: 'C', label: 'Conscientiousness', value: player.personality?.conscientiousness ?? 0.5 },
    { key: 'E', label: 'Extraversion', value: player.personality?.extraversion ?? 0.5 },
    { key: 'A', label: 'Agreeableness', value: player.personality?.agreeableness ?? 0.5 },
    { key: 'N', label: 'Neuroticism', value: player.personality?.neuroticism ?? 0.5 },
  ];

  // Stats
  const stats = [
    { label: 'Intellect', value: player.stats?.intellect ?? 0.5 },
    { label: 'Dexterity', value: player.stats?.dexterity ?? 0.5 },
    { label: 'Composure', value: player.stats?.composure ?? 0.5 },
    { label: 'Social Influence', value: player.stats?.social_influence ?? 0.5 },
  ];

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'profile', label: 'Profile' },
    { id: 'trust', label: 'Trust', count: trustRelationships.suspects.length },
    { id: 'events', label: 'Events', count: playerEvents.length },
  ];

  const archetypeColor = getArchetypeColor(player.archetype_id || '');

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.2 }}
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: reducedMotion ? 1 : 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: reducedMotion ? 1 : 0.95, opacity: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.2 }}
        className="bg-gray-800 rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-start gap-4">
            {/* Avatar placeholder with archetype color */}
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold text-white"
              style={{ backgroundColor: archetypeColor }}
            >
              {player.name.charAt(0)}
            </div>

            <div className="flex-1 min-w-0">
              <h2 className="text-2xl font-bold text-white truncate">{player.name}</h2>
              <p className="text-gray-400">{player.archetype_name || player.archetype_id}</p>

              {/* Status badges */}
              <div className="flex flex-wrap gap-2 mt-2">
                {!player.alive && (
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    player.elimination_type === 'MURDERED' ? 'bg-red-600' : 'bg-orange-600'
                  }`}>
                    {player.elimination_type === 'MURDERED' ? 'Murdered' : 'Banished'} Day {player.eliminated_day}
                  </span>
                )}
                {player.was_recruited && (
                  <span className="px-2 py-0.5 rounded text-xs bg-purple-600">
                    Recruited
                  </span>
                )}
                {player.has_shield && (
                  <span className="px-2 py-0.5 rounded text-xs bg-yellow-600">
                    🛡️ Shield
                  </span>
                )}
                {player.has_dagger && (
                  <span className="px-2 py-0.5 rounded text-xs bg-red-700">
                    🗡️ Dagger
                  </span>
                )}
              </div>
            </div>

            {/* Role badge */}
            {showRoles && (
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                player.role === 'TRAITOR' ? 'bg-red-600' : 'bg-blue-600'
              }`}>
                {player.role}
              </span>
            )}

            {/* Close button */}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-white border-b-2 border-blue-500 bg-gray-750'
                  : 'text-gray-400 hover:text-white hover:bg-gray-750'
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-1 text-xs text-gray-500">({tab.count})</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            {activeTab === 'profile' && (
              <motion.div
                key="profile"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {/* Demographics */}
                {player.demographics && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-2">Demographics</h3>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Age:</span>
                        <span className="ml-2 text-white">{player.demographics.age}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Location:</span>
                        <span className="ml-2 text-white">{player.demographics.location}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Occupation:</span>
                        <span className="ml-2 text-white">{player.demographics.occupation}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Backstory */}
                {player.backstory && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-2">Backstory</h3>
                    <p className="text-sm text-gray-300 leading-relaxed">{player.backstory}</p>
                  </div>
                )}

                {/* OCEAN Personality */}
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-3">Personality (OCEAN)</h3>
                  <div className="space-y-2">
                    {oceanTraits.map(trait => (
                      <div key={trait.key} className="flex items-center gap-3">
                        <span className="w-32 text-sm text-gray-400">{trait.label}</span>
                        <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-blue-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${trait.value * 100}%` }}
                            transition={{ duration: reducedMotion ? 0 : 0.5 }}
                          />
                        </div>
                        <span className="w-12 text-sm text-gray-400 text-right">
                          {(trait.value * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Stats */}
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-3">Stats</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {stats.map(stat => (
                      <div key={stat.label} className="bg-gray-750 rounded-lg p-3">
                        <div className="text-xs text-gray-400 mb-1">{stat.label}</div>
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-white">
                            {(stat.value * 100).toFixed(0)}
                          </span>
                          <span className="text-gray-500 text-sm mb-1">/ 100</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'trust' && (
              <motion.div
                key="trust"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {/* Who they suspect */}
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-3">
                    {player.name.split(' ')[0]} suspects...
                  </h3>
                  {trustRelationships.suspects.length > 0 ? (
                    <div className="space-y-2">
                      {trustRelationships.suspects.slice(0, 10).map(({ playerId, name, suspicion, role }) => (
                        <div
                          key={playerId}
                          className="flex items-center gap-3 bg-gray-750 rounded-lg p-3"
                        >
                          <div
                            className="w-2 h-8 rounded"
                            style={{ backgroundColor: getSuspicionColor(suspicion) }}
                          />
                          <span className="flex-1 text-white">{name}</span>
                          {showRoles && (
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              role === 'TRAITOR' ? 'bg-red-600/30 text-red-400' : 'bg-blue-600/30 text-blue-400'
                            }`}>
                              {role}
                            </span>
                          )}
                          <span className="text-sm text-gray-400">
                            {(suspicion * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">No trust data available</p>
                  )}
                </div>

                {/* Who suspects them */}
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-3">
                    Suspected by...
                  </h3>
                  {trustRelationships.suspectedBy.length > 0 ? (
                    <div className="space-y-2">
                      {trustRelationships.suspectedBy.slice(0, 10).map(({ playerId, name, suspicion, role }) => (
                        <div
                          key={playerId}
                          className="flex items-center gap-3 bg-gray-750 rounded-lg p-3"
                        >
                          <div
                            className="w-2 h-8 rounded"
                            style={{ backgroundColor: getSuspicionColor(suspicion) }}
                          />
                          <span className="flex-1 text-white">{name}</span>
                          {showRoles && (
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              role === 'TRAITOR' ? 'bg-red-600/30 text-red-400' : 'bg-blue-600/30 text-blue-400'
                            }`}>
                              {role}
                            </span>
                          )}
                          <span className="text-sm text-gray-400">
                            {(suspicion * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">No one suspects this player</p>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === 'events' && (
              <motion.div
                key="events"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-2"
              >
                {playerEvents.length > 0 ? (
                  playerEvents.map((event, i) => (
                    <button
                      key={event.id ?? i}
                      onClick={() => setTimelinePosition(event.day, event.phase as any)}
                      className="w-full text-left bg-gray-750 rounded-lg p-3 hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">Day {event.day}</span>
                        <span className="text-xs text-gray-600">•</span>
                        <span className="text-xs text-gray-500 capitalize">{event.phase}</span>
                        <span className="flex-1" />
                        <span className="text-xs text-blue-400">Jump →</span>
                      </div>
                      <div className="text-sm text-white mt-1">
                        {event.type.replace(/_/g, ' ')}
                        {event.target && event.target !== player.id && (
                          <span className="text-gray-400"> → {event.target}</span>
                        )}
                        {event.actor && event.actor !== player.id && (
                          <span className="text-gray-400"> by {event.actor}</span>
                        )}
                      </div>
                      {event.narrative && (
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">{event.narrative}</p>
                      )}
                    </button>
                  ))
                ) : (
                  <p className="text-gray-500 text-sm text-center py-8">
                    No events involving this player
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default PlayerDetailModal;
