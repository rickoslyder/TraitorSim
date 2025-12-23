/**
 * GameRunner - Run and monitor game simulations in real-time
 *
 * Connects via WebSocket for live log streaming and status updates.
 * Shows game progress, controls, and scrollable log output.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRunStatus, useStartGame, useStopGame, useSyncGames } from '../../api/hooks';

interface GameRunnerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface LogLine {
  timestamp: string;
  text: string;
}

interface WebSocketMessage {
  type: 'status' | 'log' | 'heartbeat' | 'complete';
  data?: {
    line?: string;
    status?: string;
    current_day?: number;
    current_phase?: string;
    alive_players?: number;
    prize_pot?: number;
    winner?: string;
    error?: string;
    log_line_count?: number;
  };
}

export function GameRunner({ isOpen, onClose }: GameRunnerProps) {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // API hooks
  const { data: runStatus, refetch: refetchStatus } = useRunStatus();
  const startGameMutation = useStartGame();
  const stopGameMutation = useStopGame();
  const syncGamesMutation = useSyncGames();

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Detect manual scroll
  const handleScroll = useCallback(() => {
    if (logsContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setAutoScroll(isAtBottom);
    }
  }, []);

  // WebSocket connection
  useEffect(() => {
    if (!isOpen) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/games/run/ws`;

    const connect = () => {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          if (message.type === 'log' && message.data?.line) {
            const timestamp = new Date().toLocaleTimeString();
            setLogs(prev => [...prev, { timestamp, text: message.data!.line! }]);
          } else if (message.type === 'status') {
            refetchStatus();
          } else if (message.type === 'complete') {
            refetchStatus();
            // Sync games list after completion
            syncGamesMutation.mutate();
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        // Reconnect after 2 seconds if modal is still open
        setTimeout(() => {
          if (isOpen) connect();
        }, 2000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    };

    connect();

    // Ping to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isOpen, refetchStatus, syncGamesMutation]);

  const handleStartGame = () => {
    setLogs([]);
    startGameMutation.mutate({});
  };

  const handleStopGame = () => {
    stopGameMutation.mutate();
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const isRunning = runStatus?.running || false;
  const status = runStatus?.status || 'idle';

  // Phase emoji mapping
  const phaseEmoji: Record<string, string> = {
    breakfast: '🍳',
    mission: '🎯',
    social: '💬',
    roundtable: '⚖️',
    turret: '🗡️',
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <div className="text-2xl">🎮</div>
                <div>
                  <h2 className="text-xl font-bold text-white">Game Runner</h2>
                  <p className="text-sm text-gray-400">
                    {isRunning ? 'Game in progress...' : 'Start a new simulation'}
                  </p>
                </div>
              </div>

              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                aria-label="Close"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* Status bar */}
            {runStatus && (
              <div className="flex items-center gap-4 px-4 py-3 bg-gray-750 border-b border-gray-700">
                {/* Connection status */}
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      wsConnected ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="text-xs text-gray-400">
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>

                {isRunning && (
                  <>
                    <div className="w-px h-4 bg-gray-600" />

                    {/* Day/Phase */}
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-300">
                        Day {runStatus.current_day}
                      </span>
                      {runStatus.current_phase && (
                        <span className="text-sm text-gray-400">
                          {phaseEmoji[runStatus.current_phase] || ''}{' '}
                          {runStatus.current_phase}
                        </span>
                      )}
                    </div>

                    <div className="w-px h-4 bg-gray-600" />

                    {/* Players */}
                    {runStatus.alive_players > 0 && (
                      <div className="text-sm text-gray-300">
                        👥 {runStatus.alive_players} alive
                      </div>
                    )}

                    {/* Prize pot */}
                    {runStatus.prize_pot > 0 && (
                      <div className="text-sm text-yellow-400">
                        💰 £{runStatus.prize_pot.toLocaleString()}
                      </div>
                    )}
                  </>
                )}

                {/* Winner */}
                {runStatus.winner && (
                  <div
                    className={`text-sm font-medium ${
                      runStatus.winner === 'FAITHFUL'
                        ? 'text-blue-400'
                        : 'text-red-400'
                    }`}
                  >
                    🏆 {runStatus.winner} WIN!
                  </div>
                )}

                {/* Status badge */}
                <div className="ml-auto">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      status === 'running'
                        ? 'bg-green-600/20 text-green-400'
                        : status === 'completed'
                        ? 'bg-blue-600/20 text-blue-400'
                        : status === 'failed'
                        ? 'bg-red-600/20 text-red-400'
                        : status === 'stopped'
                        ? 'bg-yellow-600/20 text-yellow-400'
                        : 'bg-gray-600/20 text-gray-400'
                    }`}
                  >
                    {status.toUpperCase()}
                  </span>
                </div>
              </div>
            )}

            {/* Log output */}
            <div
              ref={logsContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-gray-900"
            >
              {logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <div className="text-4xl mb-4">📺</div>
                  <p>No logs yet. Start a game to see output.</p>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {logs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                      <span className="text-gray-600 select-none">
                        {log.timestamp}
                      </span>
                      <span
                        className={`flex-1 ${
                          log.text.includes('ERROR')
                            ? 'text-red-400'
                            : log.text.includes('WARNING')
                            ? 'text-yellow-400'
                            : log.text.includes('WINNER')
                            ? 'text-green-400 font-bold'
                            : log.text.includes('DAY')
                            ? 'text-blue-400 font-semibold'
                            : log.text.includes('murdered')
                            ? 'text-red-300'
                            : log.text.includes('banished')
                            ? 'text-orange-300'
                            : 'text-gray-300'
                        }`}
                      >
                        {log.text}
                      </span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              )}
            </div>

            {/* Auto-scroll indicator */}
            {!autoScroll && logs.length > 0 && (
              <button
                onClick={() => {
                  setAutoScroll(true);
                  logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="absolute bottom-24 right-8 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg shadow-lg hover:bg-blue-500 transition-colors"
              >
                ↓ Scroll to bottom
              </button>
            )}

            {/* Controls */}
            <div className="flex items-center gap-3 p-4 border-t border-gray-700 bg-gray-800">
              {!isRunning ? (
                <button
                  onClick={handleStartGame}
                  disabled={startGameMutation.isPending}
                  className="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {startGameMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Starting...
                    </>
                  ) : (
                    <>
                      <span>▶</span>
                      Start New Game
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={handleStopGame}
                  disabled={stopGameMutation.isPending}
                  className="flex items-center gap-2 px-6 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {stopGameMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Stopping...
                    </>
                  ) : (
                    <>
                      <span>■</span>
                      Stop Game
                    </>
                  )}
                </button>
              )}

              <button
                onClick={handleClearLogs}
                className="px-4 py-2.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              >
                Clear Logs
              </button>

              <div className="ml-auto text-sm text-gray-500">
                {logs.length} lines
                {runStatus?.log_line_count !== undefined &&
                  runStatus.log_line_count > logs.length && (
                    <span> ({runStatus.log_line_count} total)</span>
                  )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default GameRunner;
