import { useState, useEffect } from 'react';
import './DecisionModal.css';

interface DecisionModalProps {
  decisionId: string;
  decisionType: string;
  context: Record<string, unknown>;
  timeoutSeconds: number;
  deadline: string;
  onSubmit: (decisionId: string, result: unknown) => void;
}

export function DecisionModal({
  decisionId,
  decisionType,
  context,
  timeoutSeconds,
  deadline,
  onSubmit,
}: DecisionModalProps) {
  const [timeLeft, setTimeLeft] = useState(timeoutSeconds);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  // Countdown timer
  useEffect(() => {
    const deadlineTime = new Date(deadline).getTime();

    const updateTimer = () => {
      const now = Date.now();
      const remaining = Math.max(0, Math.floor((deadlineTime - now) / 1000));
      setTimeLeft(remaining);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  const handleSubmit = () => {
    if (!selectedOption) return;
    onSubmit(decisionId, { vote: selectedOption });
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Get candidates from context
  const candidates = (context.candidates as Array<{ id: string; name: string }>) || [];
  const phase = context.phase as string;
  const day = context.day as number;

  let title = 'Make Your Decision';
  let description = '';

  switch (decisionType) {
    case 'vote':
      title = 'Vote to Banish';
      description = `Day ${day}: Choose a player to banish from the castle.`;
      break;
    case 'murder':
      title = 'Choose Your Victim';
      description = 'Select a Faithful to murder tonight.';
      break;
    case 'recruit':
      title = 'Recruitment Offer';
      description = 'A Faithful has been offered recruitment. Accept or decline?';
      break;
    default:
      title = 'Make Your Decision';
  }

  return (
    <div className="decision-modal-overlay">
      <div className="decision-modal">
        <div className="decision-header">
          <h2>{title}</h2>
          <div className={`timer ${timeLeft < 30 ? 'urgent' : ''}`}>
            {formatTime(timeLeft)}
          </div>
        </div>

        <p className="description">{description}</p>

        <div className="options-list">
          {candidates.map((candidate) => (
            <button
              key={candidate.id}
              className={`option ${selectedOption === candidate.id ? 'selected' : ''}`}
              onClick={() => setSelectedOption(candidate.id)}
            >
              {candidate.name}
            </button>
          ))}
        </div>

        <div className="decision-actions">
          <button
            onClick={handleSubmit}
            disabled={!selectedOption || timeLeft === 0}
            className="submit-btn"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
