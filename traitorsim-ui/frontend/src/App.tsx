/**
 * TraitorSim UI - Main Application
 *
 * Uses TanStack Query for server state and Zustand for UI state.
 */

import { useState, useEffect, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { POVSelector } from './components/layout/POVSelector';
import { PlayerGrid } from './components/players/PlayerGrid';
import { EventFeed } from './components/events/EventFeed';

// Lazy-loaded visualization components
const TrustGraph = lazy(() => import('./components/trust-network/TrustGraph').then(m => ({ default: m.TrustGraph })));
const TimelineScrubber = lazy(() => import('./components/timeline/TimelineScrubber').then(m => ({ default: m.TimelineScrubber })));
const PlaybackControls = lazy(() => import('./components/timeline/PlaybackControls').then(m => ({ default: m.PlaybackControls })));
const VotingHeatmap = lazy(() => import('./components/voting/VotingHeatmap').then(m => ({ default: m.VotingHeatmap })));
const VoteFlow = lazy(() => import('./components/voting/VoteFlow').then(m => ({ default: m.VoteFlow })));
const BreakfastOrderChart = lazy(() => import('./components/analysis/BreakfastOrderChart').then(m => ({ default: m.BreakfastOrderChart })));
const MissionBreakdown = lazy(() => import('./components/analysis/MissionBreakdown').then(m => ({ default: m.MissionBreakdown })));
const ScrollytellingView = lazy(() => import('./components/recap/ScrollytellingView').then(m => ({ default: m.ScrollytellingView })));
import {
  ErrorBoundary,
  QueryErrorFallback,
  LoadingFallback,
  EmptyStateFallback,
} from './components/ErrorBoundary';
import { useGameStore } from './stores/gameStore';
import { useGame, useRefreshGames } from './api/hooks';
import type { TrustSnapshot } from './types/trust';

type ViewTab = 'graph' | 'players' | 'voting' | 'events' | 'analysis' | 'story';
type VotingView = 'heatmap' | 'flow';

const TABS: { id: ViewTab; label: string; icon: string }[] = [
  { id: 'graph', label: 'Trust Network', icon: '🕸️' },
  { id: 'players', label: 'Players', icon: '👥' },
  { id: 'voting', label: 'Voting', icon: '🗳️' },
  { id: 'events', label: 'Events', icon: '📜' },
  { id: 'analysis', label: 'Analysis', icon: '📊' },
  { id: 'story', label: 'Story Mode', icon: '📖' },
];

function App() {
  // UI state from Zustand
  const {
    selectedGameId,
    currentDay,
    currentPhase,
    currentTrustMatrix,
    updateTrustMatrix,
  } = useGameStore();

  // Server state from TanStack Query
  const {
    data: currentGame,
    isLoading,
    error,
    refetch,
  } = useGame(selectedGameId);

  // Refresh mutation
  const refreshMutation = useRefreshGames();

  // Local UI state
  const [activeTab, setActiveTab] = useState<ViewTab>('graph');
  const [votingView, setVotingView] = useState<VotingView>('heatmap');

  // Update trust matrix when game data or timeline position changes
  useEffect(() => {
    if (currentGame?.trust_snapshots) {
      updateTrustMatrix(currentGame.trust_snapshots as TrustSnapshot[]);
    }
  }, [currentGame?.trust_snapshots, currentDay, currentPhase, updateTrustMatrix]);

  // Graph dimensions are now handled by useContainerSize in TrustGraph

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-900 flex flex-col">
        <Header onRefreshClick={handleRefresh} isRefreshing={refreshMutation.isPending} />

        <div className="flex-1 flex overflow-hidden">
          <Sidebar />

          <main className="flex-1 flex flex-col overflow-hidden">
            {/* Loading state */}
            {isLoading && (
              <div className="flex-1 flex items-center justify-center">
                <LoadingFallback message="Loading game data..." />
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="flex-1 flex items-center justify-center p-8">
                <QueryErrorFallback
                  error={error}
                  title="Failed to load game"
                  onRetry={() => refetch()}
                />
              </div>
            )}

            {/* No game selected */}
            {!isLoading && !error && !currentGame && (
              <div className="flex-1 flex items-center justify-center">
                <EmptyStateFallback
                  icon="🎭"
                  title="Welcome to TraitorSim"
                  message="Select a game from the sidebar to analyze"
                />
              </div>
            )}

            {/* Game loaded */}
            {!isLoading && !error && currentGame && (
              <>
                {/* Timeline, Playback Controls, and POV Selector */}
                <div className="p-4 border-b border-gray-700 space-y-4">
                  <div className="flex flex-col lg:flex-row gap-4">
                    <div className="flex-1 space-y-4">
                      <Suspense fallback={<div className="flex items-center justify-center h-24 text-gray-400">Loading timeline...</div>}>
                        <TimelineScrubber
                          totalDays={currentGame.total_days}
                          events={currentGame.events}
                        />
                        <PlaybackControls totalDays={currentGame.total_days} />
                      </Suspense>
                    </div>
                    {/* POV Selector - collapsible panel */}
                    <div className="lg:w-80 lg:border-l lg:border-gray-700 lg:pl-4">
                      <details className="group">
                        <summary className="flex items-center gap-2 cursor-pointer text-gray-400 hover:text-white mb-2">
                          <span className="text-sm font-medium">Viewing Mode</span>
                          <span className="text-xs text-gray-500">(click to expand)</span>
                        </summary>
                        <POVSelector players={currentGame.players} />
                      </details>
                    </div>
                  </div>
                </div>

                {/* Tab bar */}
                <div className="flex border-b border-gray-700">
                  {TABS.map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
                        activeTab === tab.id
                          ? 'text-white border-b-2 border-blue-500 bg-gray-800'
                          : 'text-gray-400 hover:text-white hover:bg-gray-800'
                      }`}
                      aria-selected={activeTab === tab.id}
                      role="tab"
                    >
                      <span>{tab.icon}</span>
                      <span>{tab.label}</span>
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-hidden" role="tabpanel">
                  <AnimatePresence mode="wait">
                    {activeTab === 'graph' && (
                      <motion.div
                        key="graph"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full p-4"
                      >
                        <ErrorBoundary
                          fallback={
                            <QueryErrorFallback
                              error="Failed to render trust network"
                              title="Visualization Error"
                            />
                          }
                        >
                          <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>}>
                            <TrustGraph
                              players={currentGame.players}
                              trustMatrix={currentTrustMatrix}
                            />
                          </Suspense>
                        </ErrorBoundary>
                      </motion.div>
                    )}

                    {activeTab === 'players' && (
                      <motion.div
                        key="players"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full overflow-y-auto"
                      >
                        <ErrorBoundary>
                          <PlayerGrid
                            players={currentGame.players}
                            trustMatrix={currentTrustMatrix}
                            events={currentGame.events}
                          />
                        </ErrorBoundary>
                      </motion.div>
                    )}

                    {activeTab === 'voting' && (
                      <motion.div
                        key="voting"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full flex flex-col overflow-hidden"
                      >
                        {/* Voting view toggle */}
                        <div className="flex items-center gap-2 p-4 border-b border-gray-700">
                          <span className="text-sm text-gray-400">View:</span>
                          <div className="flex rounded-lg bg-gray-800 p-1">
                            <button
                              onClick={() => setVotingView('heatmap')}
                              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                                votingView === 'heatmap'
                                  ? 'bg-blue-600 text-white'
                                  : 'text-gray-400 hover:text-white'
                              }`}
                            >
                              Heatmap
                            </button>
                            <button
                              onClick={() => setVotingView('flow')}
                              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                                votingView === 'flow'
                                  ? 'bg-blue-600 text-white'
                                  : 'text-gray-400 hover:text-white'
                              }`}
                            >
                              Sankey Flow
                            </button>
                          </div>
                        </div>

                        {/* Voting content */}
                        <div className="flex-1 p-4 overflow-auto">
                          <ErrorBoundary>
                            <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>}>
                              {votingView === 'heatmap' ? (
                                <VotingHeatmap
                                  players={currentGame.players}
                                  events={currentGame.events}
                                />
                              ) : (
                                <VoteFlow
                                  players={currentGame.players}
                                  events={currentGame.events}
                                />
                              )}
                            </Suspense>
                          </ErrorBoundary>
                        </div>
                      </motion.div>
                    )}

                    {activeTab === 'events' && (
                      <motion.div
                        key="events"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full p-4"
                      >
                        <ErrorBoundary>
                          <EventFeed events={currentGame.events} />
                        </ErrorBoundary>
                      </motion.div>
                    )}

                    {activeTab === 'analysis' && (
                      <motion.div
                        key="analysis"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full overflow-y-auto p-4"
                      >
                        <ErrorBoundary>
                          <div className="space-y-8 max-w-6xl mx-auto">
                            {/* Analysis header */}
                            <div className="text-center">
                              <h2 className="text-2xl font-bold text-white mb-2">
                                Game Analysis
                              </h2>
                              <p className="text-gray-400 text-sm">
                                Detect suspicious patterns like a true Traitors detective
                              </p>
                            </div>

                            {/* Breakfast Order Analysis */}
                            <section className="bg-gray-800 rounded-xl p-6">
                              <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>}>
                                <BreakfastOrderChart
                                  players={currentGame.players}
                                  events={currentGame.events}
                                />
                              </Suspense>
                            </section>

                            {/* Mission Performance Analysis */}
                            <section className="bg-gray-800 rounded-xl p-6">
                              <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>}>
                                <MissionBreakdown
                                  players={currentGame.players}
                                  events={currentGame.events}
                                />
                              </Suspense>
                            </section>
                          </div>
                        </ErrorBoundary>
                      </motion.div>
                    )}

                    {activeTab === 'story' && (
                      <motion.div
                        key="story"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full overflow-y-auto"
                      >
                        <ErrorBoundary>
                          <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400">Loading…</div>}>
                            <ScrollytellingView
                              players={currentGame.players}
                              events={currentGame.events}
                              totalDays={currentGame.total_days}
                              prizePot={currentGame.prize_pot}
                              winner={currentGame.winner === 'FAITHFUL' || currentGame.winner === 'TRAITORS' ? currentGame.winner : undefined}
                            />
                          </Suspense>
                        </ErrorBoundary>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </>
            )}
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default App;
