/**
 * Action panel component.
 * Renders the appropriate decision UI based on pending decision type.
 */

import { useState } from 'react';
import { VotingPanel } from './VotingPanel';
import { MurderPanel } from './MurderPanel';
import { CountdownTimer } from './CountdownTimer';
import type { PendingDecision, LiveGameState, PlayerAction } from '../../types/live';

interface ActionPanelProps {
  pendingDecision: PendingDecision | null;
  gameState: LiveGameState;
  onSubmit: (action: PlayerAction) => void;
  disabled?: boolean;
}

export function ActionPanel({
  pendingDecision,
  gameState,
  onSubmit,
  disabled = false,
}: ActionPanelProps) {
  // No pending decision - show waiting state
  if (!pendingDecision) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center">
        <div className="text-4xl mb-4">⏳</div>
        <h3 className="text-lg font-semibold text-white mb-2">
          Waiting for others...
        </h3>
        <p className="text-gray-400">
          {getPhaseDescription(gameState.phase)}
        </p>
      </div>
    );
  }

  // Render based on decision type
  switch (pendingDecision.decision_type) {
    case 'vote':
      return (
        <VotingPanel
          targets={pendingDecision.context.available_targets || gameState.players}
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onVote={(targetId) =>
            onSubmit({
              decision_type: 'vote',
              target_player_id: targetId,
            })
          }
          disabled={disabled}
          myPlayerId={gameState.my_player_id}
        />
      );

    case 'murder':
      return (
        <MurderPanel
          targets={pendingDecision.context.available_targets || gameState.players}
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onSelect={(targetId) =>
            onSubmit({
              decision_type: 'murder',
              target_player_id: targetId,
            })
          }
          disabled={disabled}
          fellowTraitors={gameState.fellow_traitors}
        />
      );

    case 'recruit_target':
      return (
        <RecruitTargetPanel
          targets={pendingDecision.context.available_targets || []}
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onSelect={(targetId) =>
            onSubmit({
              decision_type: 'recruit_target',
              target_player_id: targetId,
            })
          }
          disabled={disabled}
        />
      );

    case 'recruit_response':
      return (
        <RecruitResponsePanel
          recruiterName={pendingDecision.context.recruiter?.name || 'A Traitor'}
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onRespond={(accept) =>
            onSubmit({
              decision_type: 'recruit_response',
              choice: accept ? 'accept' : 'decline',
            })
          }
          disabled={disabled}
        />
      );

    case 'share_steal':
      return (
        <ShareStealPanel
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onChoice={(choice) =>
            onSubmit({
              decision_type: 'share_steal',
              choice,
            })
          }
          disabled={disabled}
        />
      );

    case 'vote_to_end':
      return (
        <VoteToEndPanel
          deadline={pendingDecision.deadline}
          totalSeconds={pendingDecision.timeout_seconds}
          onChoice={(choice) =>
            onSubmit({
              decision_type: 'vote_to_end',
              choice,
            })
          }
          disabled={disabled}
        />
      );

    default:
      return (
        <div className="bg-gray-800 rounded-xl p-6">
          <p className="text-gray-400">
            Unknown decision type: {pendingDecision.decision_type}
          </p>
        </div>
      );
  }
}

// Helper to get phase description
function getPhaseDescription(phase: string): string {
  const descriptions: Record<string, string> = {
    breakfast: 'The players are gathering for breakfast...',
    mission: 'A mission is in progress...',
    social: 'Players are discussing and forming alliances...',
    roundtable: 'The round table discussion is underway...',
    turret: 'Night has fallen. The Traitors are meeting...',
  };
  return descriptions[phase.toLowerCase().replace('state_', '')] || 'The game is in progress...';
}

// Recruit target panel (simplified)
function RecruitTargetPanel({
  targets,
  deadline,
  totalSeconds,
  onSelect,
  disabled,
}: {
  targets: { id: string; name: string; alive: boolean }[];
  deadline: string;
  totalSeconds: number;
  onSelect: (targetId: string) => void;
  disabled: boolean;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = () => {
    if (selected && !confirmed) {
      setConfirmed(true);
      onSelect(selected);
    }
  };

  return (
    <div className="bg-gradient-to-br from-gray-900 to-purple-950/30 border border-purple-800/50 rounded-xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-purple-400 flex items-center gap-2">
            <span>🎭</span> Choose a Recruit
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Select a Faithful to offer the chance to become a Traitor.
          </p>
        </div>
        <CountdownTimer deadline={deadline} totalSeconds={totalSeconds} size="md" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {targets.filter(t => t.alive).map((target) => (
          <button
            key={target.id}
            onClick={() => !confirmed && !disabled && setSelected(target.id)}
            disabled={confirmed || disabled}
            className={`
              p-4 rounded-lg border-2 transition-colors transition-transform text-center
              ${selected === target.id ? 'border-purple-500 bg-purple-500/20' : 'border-gray-600 bg-gray-700/50'}
              ${confirmed || disabled ? 'opacity-50' : 'cursor-pointer hover:border-purple-600/50'}
            `}
            aria-label={`Select ${target.name} as recruit target`}
          >
            <span className="font-medium text-white">{target.name}</span>
          </button>
        ))}
      </div>

      <div className="flex justify-center">
        <button
          onClick={handleConfirm}
          disabled={!selected || confirmed || disabled}
          className={`px-8 py-3 rounded-lg font-semibold ${
            selected && !confirmed ? 'bg-purple-600 hover:bg-purple-500 text-white' : 'bg-gray-600 text-gray-400'
          }`}
        >
          {confirmed ? 'Recruit Offer Sent' : 'Confirm Selection'}
        </button>
      </div>
    </div>
  );
}

// Recruit response panel
function RecruitResponsePanel({
  recruiterName,
  deadline,
  totalSeconds,
  onRespond,
  disabled,
}: {
  recruiterName: string;
  deadline: string;
  totalSeconds: number;
  onRespond: (accept: boolean) => void;
  disabled: boolean;
}) {
  const [choice, setChoice] = useState<boolean | null>(null);

  const handleChoice = (accept: boolean) => {
    if (choice === null && !disabled) {
      setChoice(accept);
      onRespond(accept);
    }
  };

  return (
    <div className="bg-gradient-to-br from-gray-900 to-purple-950/30 border border-purple-800/50 rounded-xl p-6 space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-purple-400 mb-2">🎭 You Have Been Chosen</h2>
        <p className="text-gray-300">
          <span className="text-purple-400 font-medium">{recruiterName}</span> has revealed they are a Traitor
          and offers you the chance to join them.
        </p>
      </div>

      <CountdownTimer deadline={deadline} totalSeconds={totalSeconds} size="lg" />

      <div className="flex justify-center gap-4">
        <button
          onClick={() => handleChoice(true)}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === true
              ? 'bg-purple-600 text-white'
              : choice !== null
              ? 'bg-gray-700 text-gray-500'
              : 'bg-purple-600 hover:bg-purple-500 text-white'
          }`}
          aria-label="Accept recruitment and become a Traitor"
        >
          🎭 Accept
        </button>
        <button
          onClick={() => handleChoice(false)}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === false
              ? 'bg-blue-600 text-white'
              : choice !== null
              ? 'bg-gray-700 text-gray-500'
              : 'bg-blue-600 hover:bg-blue-500 text-white'
          }`}
          aria-label="Decline recruitment and stay Faithful"
        >
          💙 Stay Faithful
        </button>
      </div>

      {choice !== null && (
        <p className="text-center text-gray-400">
          {choice ? 'You have joined the Traitors.' : 'You remain Faithful.'}
        </p>
      )}
    </div>
  );
}

// Share/Steal panel
function ShareStealPanel({
  deadline,
  totalSeconds,
  onChoice,
  disabled,
}: {
  deadline: string;
  totalSeconds: number;
  onChoice: (choice: string) => void;
  disabled: boolean;
}) {
  const [choice, setChoice] = useState<string | null>(null);

  const handleChoice = (c: string) => {
    if (!choice && !disabled) {
      setChoice(c);
      onChoice(c);
    }
  };

  return (
    <div className="bg-gradient-to-br from-gray-900 to-yellow-950/30 border border-yellow-800/50 rounded-xl p-6 space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-yellow-400 mb-2">💰 The Traitor's Dilemma</h2>
        <p className="text-gray-300">
          Will you share the prize pot equally, or try to steal it all?
        </p>
      </div>

      <CountdownTimer deadline={deadline} totalSeconds={totalSeconds} size="lg" />

      <div className="flex justify-center gap-4">
        <button
          onClick={() => handleChoice('share')}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === 'share'
              ? 'bg-green-600 text-white'
              : 'bg-green-600 hover:bg-green-500 text-white'
          } ${choice && choice !== 'share' ? 'opacity-50' : ''}`}
          aria-label="Share the prize pot equally"
        >
          🤝 Share
        </button>
        <button
          onClick={() => handleChoice('steal')}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === 'steal'
              ? 'bg-red-600 text-white'
              : 'bg-red-600 hover:bg-red-500 text-white'
          } ${choice && choice !== 'steal' ? 'opacity-50' : ''}`}
          aria-label="Steal the entire prize pot"
        >
          💀 Steal
        </button>
      </div>
    </div>
  );
}

// Vote to end panel
function VoteToEndPanel({
  deadline,
  totalSeconds,
  onChoice,
  disabled,
}: {
  deadline: string;
  totalSeconds: number;
  onChoice: (choice: string) => void;
  disabled: boolean;
}) {
  const [choice, setChoice] = useState<string | null>(null);

  const handleChoice = (c: string) => {
    if (!choice && !disabled) {
      setChoice(c);
      onChoice(c);
    }
  };

  return (
    <div className="bg-gradient-to-br from-gray-900 to-blue-950/30 border border-blue-800/50 rounded-xl p-6 space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-blue-400 mb-2">🏁 End Game Vote</h2>
        <p className="text-gray-300">
          Do you believe all Traitors have been eliminated? Vote to end and claim the prize, or continue hunting.
        </p>
      </div>

      <CountdownTimer deadline={deadline} totalSeconds={totalSeconds} size="lg" />

      <div className="flex justify-center gap-4">
        <button
          onClick={() => handleChoice('end')}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === 'end'
              ? 'bg-green-600 text-white'
              : 'bg-green-600 hover:bg-green-500 text-white'
          } ${choice && choice !== 'end' ? 'opacity-50' : ''}`}
          aria-label="End the game and claim the prize"
        >
          🏆 End Game
        </button>
        <button
          onClick={() => handleChoice('continue')}
          disabled={choice !== null || disabled}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-colors transition-transform ${
            choice === 'continue'
              ? 'bg-orange-600 text-white'
              : 'bg-orange-600 hover:bg-orange-500 text-white'
          } ${choice && choice !== 'continue' ? 'opacity-50' : ''}`}
          aria-label="Continue hunting for Traitors"
        >
          🔍 Continue
        </button>
      </div>
    </div>
  );
}
