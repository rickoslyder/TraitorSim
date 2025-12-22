/**
 * Core game data types for TraitorSim UI
 */

import type { Player } from './player';
import type { GameEvent } from './events';
import type { TrustSnapshot } from './trust';

export type Role = 'FAITHFUL' | 'TRAITOR';

export type Phase = 'breakfast' | 'mission' | 'social' | 'roundtable' | 'turret';

export type Winner = 'FAITHFUL' | 'TRAITORS';

export type RuleVariant = 'uk' | 'us' | 'australia' | 'canada';

export interface GameConfig {
  total_players: number;
  num_traitors: number;
  max_days: number;
  enable_recruitment: boolean;
  enable_shields: boolean;
  enable_death_list: boolean;
  tie_break_method: string;
}

export interface GameSession {
  id: string;
  name: string;
  created_at: string;
  total_days: number;
  prize_pot: number;
  winner: Winner;
  rule_variant: RuleVariant;
  config?: GameConfig;
  players: Record<string, Player>;
  events: GameEvent[];
  trust_snapshots: TrustSnapshot[];
  // History tracking
  vote_history?: Array<Record<string, string>>;  // voter_id -> target_id per day
  breakfast_order_history?: string[][];  // player IDs in entry order per day
  murdered_players?: string[];
  banished_players?: string[];
  recruited_players?: string[];
  // Current holders
  shield_holder?: string;
  dagger_holder?: string;
  seer_holder?: string;
}

export interface GameSummary {
  id: string;
  name: string;
  created_at: string;
  total_days: number;
  prize_pot: number;
  winner: Winner;
  rule_variant: RuleVariant;
}
