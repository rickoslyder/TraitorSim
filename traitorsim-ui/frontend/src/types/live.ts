// Live game types - matching the original UI components

export interface LivePlayer {
  id: string;
  name: string;
  role?: 'FAITHFUL' | 'TRAITOR';
  isAlive: boolean;
  hasShield: boolean;
  hasDagger?: boolean;
  is_human?: boolean;
  // For backward compatibility with components using 'alive'
  alive?: boolean;
  has_shield?: boolean;
  has_dagger?: boolean;
}

export interface LiveGameState {
  gameId: string;
  day: number;
  phase: string;
  players: LivePlayer[];
  my_player_id: string;
  my_role?: 'FAITHFUL' | 'TRAITOR';
  my_alive?: boolean;
  fellow_traitors?: string[];
  prizePot: number;
  status: 'waiting' | 'in_progress' | 'completed';
  // For backward compatibility
  alive_count?: number;
}

export type DecisionType = 'vote' | 'murder' | 'recruit_target' | 'recruit_accept' | 'mission' | 'seer';

export interface PendingDecision {
  id: string;
  decision_type: DecisionType;
  playerId: string;
  timeout: number;
  timeout_seconds?: number;
  deadline?: string;
  context: {
    available_targets?: LivePlayer[];
    mission_options?: MissionOption[];
    [key: string]: unknown;
  };
}

export interface MissionOption {
  id: string;
  name: string;
  difficulty: number;
}

export interface PlayerAction {
  decision_type: string;
  target_player_id?: string;
  accept?: boolean;
  option_id?: string;
}

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
  sender_name?: string;
  message: string;
  timestamp: number;
  channel?: 'public' | 'traitors' | 'system';
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
  is_private?: boolean;
  narrative?: string;
}

export interface PlayerStatusMessage {
  playerId: string;
  status: 'connected' | 'disconnected' | 'deciding';
}
