/**
 * Game configuration panel for the lobby.
 * Allows the host to modify game settings before starting.
 */

import { useState, useCallback } from 'react';
import type { LobbyConfig } from '../../types/lobby';

interface GameConfigPanelProps {
  config: LobbyConfig;
  canEdit: boolean;
  onUpdate: (config: LobbyConfig) => void;
}

export function GameConfigPanel({
  config,
  canEdit,
  onUpdate,
}: GameConfigPanelProps) {
  const [localConfig, setLocalConfig] = useState<LobbyConfig>(config);
  const [hasChanges, setHasChanges] = useState(false);

  const handleChange = useCallback(
    <K extends keyof LobbyConfig>(key: K, value: LobbyConfig[K]) => {
      setLocalConfig((prev) => ({ ...prev, [key]: value }));
      setHasChanges(true);
    },
    []
  );

  const handleSave = useCallback(() => {
    onUpdate(localConfig);
    setHasChanges(false);
  }, [localConfig, onUpdate]);

  const handleReset = useCallback(() => {
    setLocalConfig(config);
    setHasChanges(false);
  }, [config]);

  return (
    <div className="bg-gray-800 rounded-lg p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Game Configuration</h3>
        {!canEdit && (
          <span className="text-sm text-gray-400">Only the host can edit</span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Rule Variant */}
        <div>
          <label htmlFor="configRuleVariant" className="block text-sm font-medium text-gray-300 mb-1">
            Rule Variant
          </label>
          <select
            id="configRuleVariant"
            name="ruleVariant"
            value={localConfig.rule_variant}
            onChange={(e) => handleChange('rule_variant', e.target.value)}
            disabled={!canEdit}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="UK">UK Rules</option>
            <option value="US">US Rules</option>
            <option value="Australia">Australian Rules</option>
          </select>
        </div>

        {/* Total Players */}
        <div>
          <label htmlFor="configTotalPlayers" className="block text-sm font-medium text-gray-300 mb-1">
            Total Players
          </label>
          <input
            id="configTotalPlayers"
            name="totalPlayers"
            type="number"
            min={4}
            max={24}
            value={localConfig.total_players}
            onChange={(e) => handleChange('total_players', parseInt(e.target.value))}
            disabled={!canEdit}
            autoComplete="off"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Number of Traitors */}
        <div>
          <label htmlFor="configNumTraitors" className="block text-sm font-medium text-gray-300 mb-1">
            Number of Traitors
          </label>
          <input
            id="configNumTraitors"
            name="numTraitors"
            type="number"
            min={1}
            max={Math.floor(localConfig.total_players / 3)}
            value={localConfig.num_traitors}
            onChange={(e) => handleChange('num_traitors', parseInt(e.target.value))}
            disabled={!canEdit}
            autoComplete="off"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Max Days */}
        <div>
          <label htmlFor="configMaxDays" className="block text-sm font-medium text-gray-300 mb-1">
            Max Days
          </label>
          <input
            id="configMaxDays"
            name="maxDays"
            type="number"
            min={3}
            max={20}
            value={localConfig.max_days}
            onChange={(e) => handleChange('max_days', parseInt(e.target.value))}
            disabled={!canEdit}
            autoComplete="off"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Decision Timeout */}
        <div>
          <label htmlFor="configDecisionTimeout" className="block text-sm font-medium text-gray-300 mb-1">
            Decision Timeout (seconds)
          </label>
          <input
            id="configDecisionTimeout"
            name="decisionTimeout"
            type="number"
            min={30}
            max={300}
            step={10}
            value={localConfig.decision_timeout}
            onChange={(e) => handleChange('decision_timeout', parseInt(e.target.value))}
            disabled={!canEdit}
            autoComplete="off"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Tie Break Method */}
        <div>
          <label htmlFor="configTieBreakMethod" className="block text-sm font-medium text-gray-300 mb-1">
            Tie Break Method
          </label>
          <select
            id="configTieBreakMethod"
            name="tieBreakMethod"
            value={localConfig.tie_break_method}
            onChange={(e) => handleChange('tie_break_method', e.target.value)}
            disabled={!canEdit}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="revote">Revote</option>
            <option value="countback">Countback</option>
            <option value="random">Random</option>
          </select>
        </div>
      </div>

      {/* Boolean options */}
      <div className="space-y-3">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={localConfig.enable_recruitment}
            onChange={(e) => handleChange('enable_recruitment', e.target.checked)}
            disabled={!canEdit}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-gray-300">Enable Recruitment</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={localConfig.enable_shields}
            onChange={(e) => handleChange('enable_shields', e.target.checked)}
            disabled={!canEdit}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-gray-300">Enable Shields</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={localConfig.enable_death_list}
            onChange={(e) => handleChange('enable_death_list', e.target.checked)}
            disabled={!canEdit}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-gray-300">Enable Death List</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={localConfig.ai_fill_empty_slots}
            onChange={(e) => handleChange('ai_fill_empty_slots', e.target.checked)}
            disabled={!canEdit}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-gray-300">Fill empty slots with AI</span>
        </label>
      </div>

      {/* Save/Reset buttons */}
      {canEdit && hasChanges && (
        <div className="flex gap-3 pt-4 border-t border-gray-700">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-md transition-colors"
          >
            Save Changes
          </button>
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white font-medium rounded-md transition-colors"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
}
