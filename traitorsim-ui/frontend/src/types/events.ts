/**
 * Game event types
 */

export type EventType =
  | 'GAME_START'
  | 'DAY_START'
  | 'PHASE_CHANGE'
  | 'MISSION_SUCCESS'
  | 'MISSION_FAIL'
  | 'MISSION_COMPLETE'  // New: structured mission data with performance scores
  | 'SHIELD_AWARDED'
  | 'SEER_AWARDED'
  | 'DAGGER_AWARDED'
  | 'VOTE'
  | 'VOTE_TALLY'  // New: complete vote breakdown with counts
  | 'TIE_VOTE'
  | 'REVOTE'
  | 'BANISHMENT'
  | 'MURDER'  // New: structured murder event
  | 'MURDER_ATTEMPT'
  | 'MURDER_SUCCESS'
  | 'MURDER_BLOCKED'
  | 'RECRUITMENT'  // New: unified recruitment event
  | 'RECRUITMENT_OFFER'
  | 'RECRUITMENT_ACCEPTED'
  | 'RECRUITMENT_REFUSED'
  | 'SEER_USED'
  | 'VOTE_TO_END'
  | 'BREAKFAST_ORDER'  // New: breakfast entry order (meta-tell)
  | 'GAME_END';

export interface GameEvent {
  id?: string;
  type: EventType;
  day: number;
  phase: string;
  actor?: string;
  target?: string;
  data: Record<string, unknown>;
  narrative?: string;
}

// Event type display info
export const EVENT_INFO: Record<EventType, { icon: string; color: string; label: string }> = {
  GAME_START: { icon: '🎬', color: 'bg-blue-500', label: 'Game Started' },
  DAY_START: { icon: '🌅', color: 'bg-yellow-500', label: 'Day Started' },
  PHASE_CHANGE: { icon: '🔄', color: 'bg-gray-500', label: 'Phase Change' },
  MISSION_SUCCESS: { icon: '✅', color: 'bg-green-500', label: 'Mission Success' },
  MISSION_FAIL: { icon: '❌', color: 'bg-red-500', label: 'Mission Failed' },
  MISSION_COMPLETE: { icon: '🎯', color: 'bg-blue-500', label: 'Mission Complete' },
  SHIELD_AWARDED: { icon: '🛡️', color: 'bg-yellow-500', label: 'Shield Awarded' },
  SEER_AWARDED: { icon: '👁️', color: 'bg-cyan-500', label: 'Seer Power Awarded' },
  DAGGER_AWARDED: { icon: '🗡️', color: 'bg-red-500', label: 'Dagger Awarded' },
  VOTE: { icon: '🗳️', color: 'bg-purple-500', label: 'Vote Cast' },
  VOTE_TALLY: { icon: '📊', color: 'bg-purple-600', label: 'Vote Tally' },
  TIE_VOTE: { icon: '⚖️', color: 'bg-orange-500', label: 'Tie Vote' },
  REVOTE: { icon: '🔄', color: 'bg-purple-400', label: 'Revote' },
  BANISHMENT: { icon: '🚪', color: 'bg-orange-500', label: 'Banished' },
  MURDER: { icon: '💀', color: 'bg-red-600', label: 'Murder' },
  MURDER_ATTEMPT: { icon: '🔪', color: 'bg-red-400', label: 'Murder Attempt' },
  MURDER_SUCCESS: { icon: '💀', color: 'bg-red-600', label: 'Murdered' },
  MURDER_BLOCKED: { icon: '🛡️', color: 'bg-green-500', label: 'Murder Blocked' },
  RECRUITMENT: { icon: '🎭', color: 'bg-red-500', label: 'Recruitment' },
  RECRUITMENT_OFFER: { icon: '🤝', color: 'bg-red-500', label: 'Recruitment Offer' },
  RECRUITMENT_ACCEPTED: { icon: '🎭', color: 'bg-red-600', label: 'Joined Traitors' },
  RECRUITMENT_REFUSED: { icon: '✋', color: 'bg-green-500', label: 'Refused Recruitment' },
  SEER_USED: { icon: '👁️', color: 'bg-cyan-500', label: 'Seer Power Used' },
  VOTE_TO_END: { icon: '🏁', color: 'bg-blue-500', label: 'Vote to End' },
  BREAKFAST_ORDER: { icon: '☀️', color: 'bg-amber-500', label: 'Breakfast' },
  GAME_END: { icon: '🏆', color: 'bg-yellow-500', label: 'Game Ended' },
};

export function getEventInfo(type: EventType) {
  return EVENT_INFO[type] || { icon: '❓', color: 'bg-gray-500', label: type };
}
