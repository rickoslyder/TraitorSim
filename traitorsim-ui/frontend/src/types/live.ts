// Live game types

export interface LivePlayer {
  id: string;
  name: string;
  role?: 'FAITHFUL' | 'TRAITOR';
  isAlive: boolean;
  hasShield: boolean;
}

export interface LiveGameState {
  gameId: string;
  day: number;
  phase: string;
  players: LivePlayer[];
  prizePot: number;
  status: 'waiting' | 'in_progress' | 'completed';
}

export type DecisionType = 'VOTE' | 'MURDER' | 'RECRUIT' | 'MISSION' | 'SEER';

export interface PendingDecision {
  id: string;
  type: DecisionType;
  playerId: string;
  timeout: number;
  context: DecisionContext;
}

export interface DecisionContext {
  candidates?: string[];
  missionOptions?: MissionOption[];
  [key: string]: unknown;
}

export interface MissionOption {
  id: string;
  name: string;
  difficulty: number;
}

export type PlayerAction = 
  | { type: 'VOTE'; targetId: string }
  | { type: 'MURDER'; targetId: string }
  | { type: 'RECRUIT'; accept: boolean }
  | { type: 'MISSION'; optionId: string };

export interface AvailableActions {
  canVote: boolean;
  canMurder: boolean;
  canRecruit: boolean;
}

// WebSocket message types
export type ClientMessageType = 
  | 'JOIN_GAME'
  | 'READY'
  | 'SUBMIT_DECISION'
  | 'SEND_CHAT'
  | 'PING';

export type ServerMessageType =
  | 'GAME_STATE'
  | 'DECISION_REQUEST'
  | 'DECISION_ACCEPTED'
  | 'DECISION_REJECTED'
  | 'GAME_EVENT'
  | 'CHAT'
  | 'PHASE_CHANGE'
  | 'TIMER_UPDATE'
  | 'ERROR'
  | 'PONG';

export interface ChatMessage {
  playerId: string;
  message: string;
  timestamp: number;
}

export interface GameStateMessage {
  type: 'GAME_STATE';
  state: LiveGameState;
}

export interface DecisionRequestMessage {
  type: 'DECISION_REQUEST';
  decision: PendingDecision;
}

export interface DecisionAcceptedMessage {
  type: 'DECISION_ACCEPTED';
  decisionId: string;
}

export interface DecisionRejectedMessage {
  type: 'DECISION_REJECTED';
  decisionId: string;
  reason: string;
}

export interface GameEventMessage {
  type: 'GAME_EVENT';
  event: GameEvent;
}

export interface ChatServerMessage {
  type: 'CHAT';
  message: ChatMessage;
}

export interface PhaseChangeMessage {
  type: 'PHASE_CHANGE';
  day: number;
  phase: string;
}

export interface TimerUpdateMessage {
  type: 'TIMER_UPDATE';
  decisionId: string;
  timeRemaining: number;
}

export interface ErrorGameMessage {
  type: 'ERROR';
  message: string;
}

export interface PongMessage {
  type: 'PONG';
}

export type ServerMessage =
  | GameStateMessage
  | DecisionRequestMessage
  | DecisionAcceptedMessage
  | DecisionRejectedMessage
  | GameEventMessage
  | ChatServerMessage
  | PhaseChangeMessage
  | TimerUpdateMessage
  | ErrorGameMessage
  | PongMessage;

export interface GameEvent {
  id: string;
  type: 'BANISHMENT' | 'MURDER' | 'RECRUITMENT' | 'MISSION_COMPLETE' | 'PHASE_START';
  day: number;
  phase: string;
  data: Record<string, unknown>;
}
