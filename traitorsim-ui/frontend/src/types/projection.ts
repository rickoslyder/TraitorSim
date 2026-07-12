/**
 * World projection v1 — API-CONTRACT.md / TraitorSim3D
 */

export type ProjectionPhase =
  | 'breakfast'
  | 'mission'
  | 'social'
  | 'round_table'
  | 'turret'
  | 'ended';

export interface PlayerProjection {
  id: string;
  display_name: string;
  alive: boolean;
  seat_index: number | null;
  role_visible: 'traitor' | 'faithful' | string | null;
}

export interface WorldProjection {
  schema_version: string;
  session_id: string;
  day: number;
  phase: ProjectionPhase;
  location_id: string;
  players: PlayerProjection[];
  prize_pot: number;
  alive_count: number;
}

export const UE_PROJECTION_URL =
  'https://traitorsim.rbnk.uk/api/sessions/{session_id}/projection/world';

export function ueSessionIdCopyText(sessionId: string): string {
  return sessionId;
}