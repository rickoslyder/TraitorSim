/**
 * Modal for creating a new game lobby.
 * Collects game name, host display name, and initial configuration.
 */

import React, { useState, useCallback } from 'react';
import type { LobbyConfig } from '../../types/lobby';

interface CreateGameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (
    name: string,
    displayName: string,
    config: Partial<LobbyConfig>,
    isPrivate: boolean
  ) => Promise<void>;
  isCreating: boolean;
  error: string | null;
}

const DEFAULT_CONFIG: Partial<LobbyConfig> = {
  rule_variant: 'UK',
  total_players: 12,
  num_traitors: 3,
  max_days: 10,
  enable_recruitment: true,
  enable_shields: true,
  enable_death_list: false,
  tie_break_method: 'revote',
  decision_timeout: 120,
  ai_fill_empty_slots: true,
};

export function CreateGameModal({
  isOpen,
  onClose,
  onCreate,
  isCreating,
  error,
}: CreateGameModalProps) {
  const [gameName, setGameName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [config, setConfig] = useState<Partial<LobbyConfig>>(DEFAULT_CONFIG);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!gameName.trim() || !displayName.trim()) return;

      await onCreate(gameName.trim(), displayName.trim(), config, isPrivate);
    },
    [gameName, displayName, config, isPrivate, onCreate]
  );

  const handleConfigChange = useCallback(
    <K extends keyof LobbyConfig>(key: K, value: LobbyConfig[K]) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Create New Game</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white transition-colors"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Error message */}
            {error && (
              <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Game Name */}
            <div>
              <label htmlFor="gameName" className="block text-sm font-medium text-gray-300 mb-1">
                Game Name
              </label>
              <input
                id="gameName"
                name="gameName"
                type="text"
                value={gameName}
                onChange={(e) => setGameName(e.target.value)}
                placeholder="Enter a name for your game…"
                autoComplete="off"
                spellCheck={false}
                required
                maxLength={50}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Display Name */}
            <div>
              <label htmlFor="displayName" className="block text-sm font-medium text-gray-300 mb-1">
                Your Display Name
              </label>
              <input
                id="displayName"
                name="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your name…"
                autoComplete="username"
                spellCheck={false}
                required
                maxLength={30}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Privacy toggle */}
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isPrivate}
                onChange={(e) => setIsPrivate(e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
              />
              <div>
                <span className="text-gray-300 font-medium">Private Game</span>
                <p className="text-xs text-gray-500">
                  Only players with the invite code can join
                </p>
              </div>
            </label>

            {/* Advanced settings toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
            >
              <svg
                className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              Advanced Settings
            </button>

            {/* Advanced settings */}
            {showAdvanced && (
              <div className="space-y-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                {/* Rule Variant */}
                <div>
                  <label htmlFor="ruleVariant" className="block text-sm font-medium text-gray-300 mb-1">
                    Rule Variant
                  </label>
                  <select
                    id="ruleVariant"
                    name="ruleVariant"
                    value={config.rule_variant}
                    onChange={(e) => handleConfigChange('rule_variant', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  >
                    <option value="UK">UK Rules</option>
                    <option value="US">US Rules</option>
                    <option value="Australia">Australian Rules</option>
                  </select>
                </div>

                {/* Player counts */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="totalPlayers" className="block text-sm font-medium text-gray-300 mb-1">
                      Total Players
                    </label>
                    <input
                      id="totalPlayers"
                      name="totalPlayers"
                      type="number"
                      min={4}
                      max={24}
                      value={config.total_players}
                      onChange={(e) =>
                        handleConfigChange('total_players', parseInt(e.target.value))
                      }
                      autoComplete="off"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    />
                  </div>
                  <div>
                    <label htmlFor="numTraitors" className="block text-sm font-medium text-gray-300 mb-1">
                      Traitors
                    </label>
                    <input
                      id="numTraitors"
                      name="numTraitors"
                      type="number"
                      min={1}
                      max={Math.floor((config.total_players || 12) / 3)}
                      value={config.num_traitors}
                      onChange={(e) =>
                        handleConfigChange('num_traitors', parseInt(e.target.value))
                      }
                      autoComplete="off"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    />
                  </div>
                </div>

                {/* Checkboxes */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.ai_fill_empty_slots}
                      onChange={(e) =>
                        handleConfigChange('ai_fill_empty_slots', e.target.checked)
                      }
                      className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500"
                    />
                    <span className="text-sm text-gray-300">
                      Fill empty slots with AI players
                    </span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.enable_shields}
                      onChange={(e) =>
                        handleConfigChange('enable_shields', e.target.checked)
                      }
                      className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500"
                    />
                    <span className="text-sm text-gray-300">Enable Shields</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.enable_recruitment}
                      onChange={(e) =>
                        handleConfigChange('enable_recruitment', e.target.checked)
                      }
                      className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500"
                    />
                    <span className="text-sm text-gray-300">Enable Recruitment</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onClose}
            disabled={isCreating}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isCreating || !gameName.trim() || !displayName.trim()}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating && (
              <svg
                className="w-4 h-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {isCreating ? 'Creating...' : 'Create Game'}
          </button>
        </div>
      </div>
    </div>
  );
}
