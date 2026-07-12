/**
 * Castle broadcast — links live sim session to TraitorSim3D (UE ceremony).
 */
import { useCallback, useState } from 'react';
import { useWorldProjection } from '../../api/hooks';
import { UE_PROJECTION_URL } from '../../types/projection';

interface CastleBroadcastPanelProps {
  sessionId?: string;
  /** Also poll when idle but session id set (replay / manual UE test). */
  pollWhenIdle?: boolean;
  isRunning?: boolean;
}

export function CastleBroadcastPanel({
  sessionId,
  pollWhenIdle = false,
  isRunning = false,
}: CastleBroadcastPanelProps) {
  const enabled = Boolean(sessionId && (isRunning || pollWhenIdle));
  const { data: projection, isLoading, isError } = useWorldProjection(sessionId, enabled);
  const [copied, setCopied] = useState(false);

  const copySession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div
        className="mx-4 mb-2 rounded-lg border border-gray-700 bg-gray-800/80 p-3 text-sm text-gray-400"
        data-testid="castle-broadcast-empty"
      >
        <span className="font-medium text-gray-300">🏰 Castle broadcast (UE)</span>
        <p className="mt-1">Start a run — the session id appears here for TraitorSim3D.</p>
      </div>
    );
  }

  const projectionUrl = UE_PROJECTION_URL.replace('{session_id}', sessionId);

  return (
    <div
      className="mx-4 mb-2 rounded-lg border border-amber-900/50 bg-gradient-to-r from-gray-800 to-gray-900 p-3"
      data-testid="castle-broadcast-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-amber-200/90">🏰 Castle broadcast → TraitorSim3D</div>
          <p className="mt-0.5 text-xs text-gray-400">
            Set <code className="text-gray-300">SessionId</code> on{' '}
            <code className="text-gray-300">BP_CeremonyDirector</code>, PIE with prod BaseUrl.
          </p>
        </div>
        <button
          type="button"
          onClick={copySession}
          className="shrink-0 rounded-md bg-amber-700/30 px-3 py-1.5 text-xs font-medium text-amber-100 hover:bg-amber-700/50"
          data-testid="castle-broadcast-copy-session"
        >
          {copied ? 'Copied' : 'Copy session id'}
        </button>
      </div>

      <div className="mt-2 font-mono text-xs text-amber-100/80 break-all">{sessionId}</div>

      {enabled && (
        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          {isLoading && <span className="text-gray-500">Loading projection…</span>}
          {isError && <span className="text-red-400">Projection request failed.</span>}
          {!isLoading && !isError && projection === null && (
            <span className="text-gray-500">Waiting for projection snapshot/report…</span>
          )}
          {projection && (
            <>
              <div className="text-gray-300">
                <span className="text-gray-500">Phase</span> {projection.phase}{' '}
                <span className="text-gray-600">·</span> day {projection.day}{' '}
                <span className="text-gray-600">·</span> £
                {projection.prize_pot.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
              <div className="text-gray-300">
                <span className="text-gray-500">Alive</span> {projection.alive_count} ·{' '}
                <span className="text-gray-500">location</span> {projection.location_id}
              </div>
              <div className="sm:col-span-2 max-h-24 overflow-y-auto rounded bg-black/30 p-2 text-gray-400">
                {projection.players
                  .filter((p) => p.alive)
                  .slice(0, 8)
                  .map((p) => (
                    <span key={p.id} className="mr-2 inline-block">
                      {p.display_name}
                      {p.role_visible ? (
                        <span
                          className={
                            p.role_visible === 'traitor' ? ' text-red-400/80' : ' text-blue-400/60'
                          }
                        >
                          {' '}
                          ({p.role_visible})
                        </span>
                      ) : null}
                    </span>
                  ))}
                {projection.players.filter((p) => p.alive).length > 8 ? '…' : null}
              </div>
            </>
          )}
        </div>
      )}

      <details className="mt-2 text-xs text-gray-500">
        <summary className="cursor-pointer hover:text-gray-400">UE polling URL</summary>
        <code className="mt-1 block break-all text-gray-400">{projectionUrl}</code>
      </details>
    </div>
  );
}