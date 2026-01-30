// Lobby types

export interface LobbyPlayer {
  id: string;
  name: string;
  isReady: boolean;
  isHost: boolean;
}

export interface LobbyState {
  id: string;
  name: string;
  players: LobbyPlayer[];
  maxPlayers: number;
  numTraitors: number;
  status: 'waiting' | 'starting' | 'in_progress';
}

export interface LobbyConfig {
  rule_variant: string;
  total_players: number;
  num_traitors: number;
  max_days: number;
  decision_timeout: number;
  tie_break_method: string;
  enable_recruitment: boolean;
  enable_shields: boolean;
  enable_death_list: boolean;
  ai_fill_empty_slots: boolean;
}

export interface CreateLobbyRequest {
  name: string;
  hostName: string;
  maxPlayers: number;
  numTraitors: number;
}

export interface JoinLobbyRequest {
  lobbyId: string;
  playerName: string;
}

export interface LobbySlot {
  slot_index: number;
  player_type: 'human' | 'ai' | 'empty';
  player_id?: string;
  display_name?: string;
  is_host?: boolean;
  is_ready?: boolean;
  is_connected?: boolean;
}
