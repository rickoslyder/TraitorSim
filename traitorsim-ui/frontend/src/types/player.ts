/**
 * Player data types
 */

import { Role } from './game';

export interface Personality {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export interface Stats {
  intellect: number;
  dexterity: number;
  composure: number;
  social_influence: number;
}

export interface Demographics {
  age: number;
  location: string;
  occupation: string;
  ethnicity?: string;
}

export type EliminationType = 'BANISHED' | 'MURDERED';

export interface Player {
  id: string;
  name: string;
  role: Role;
  archetype_id?: string;
  archetype_name?: string;
  alive: boolean;
  eliminated_day?: number;
  elimination_type?: EliminationType;
  personality: Personality;
  stats: Stats;
  backstory?: string;
  strategic_profile?: string;
  demographics?: Demographics;
  // Status flags
  has_shield?: boolean;
  has_dagger?: boolean;
  was_recruited?: boolean;
}

// Legacy alias for archetype field
export type { Player as PlayerData };

// Archetype color mapping
export const ARCHETYPE_COLORS: Record<string, string> = {
  'the-prodigy': '#8b5cf6',
  'the-charming-sociopath': '#ec4899',
  'the-misguided-survivor': '#6b7280',
  'the-comedic-psychic': '#f59e0b',
  'the-bitter-traitor': '#dc2626',
  'the-infatuated-faithful': '#f472b6',
  'the-quirky-outsider': '#22c55e',
  'the-incompetent-authority': '#78716c',
  'the-zealot': '#a855f7',
  'the-romantic': '#fb7185',
  'the-smug-player': '#fbbf24',
  'the-mischievous-operator': '#14b8a6',
  'the-charismatic-leader': '#3b82f6',
};

export function getArchetypeColor(archetype: string): string {
  const key = archetype.toLowerCase().replace(/\s+/g, '-');
  return ARCHETYPE_COLORS[key] || '#6b7280';
}
