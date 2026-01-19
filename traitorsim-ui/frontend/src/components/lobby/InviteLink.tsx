/**
 * Shareable invite link component.
 * Generates and displays a link for others to join the lobby.
 */

import { useState, useCallback } from 'react';

interface InviteLinkProps {
  gameId: string;
  inviteCode?: string | null;
}

export function InviteLink({ gameId, inviteCode }: InviteLinkProps) {
  const [copied, setCopied] = useState(false);

  // Build the invite URL
  const inviteUrl = inviteCode
    ? `${window.location.origin}/join/${gameId}?code=${inviteCode}`
    : `${window.location.origin}/join/${gameId}`;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [inviteUrl]);

  return (
    <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-2">
      <div className="flex-1 min-w-0">
        <input
          name="inviteUrl"
          type="url"
          readOnly
          value={inviteUrl}
          autoComplete="off"
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-300 truncate"
          onClick={(e) => e.currentTarget.select()}
          aria-label="Invite URL"
        />
      </div>
      <button
        onClick={handleCopy}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded font-medium text-sm transition-colors
          ${
            copied
              ? 'bg-green-600 text-white'
              : 'bg-blue-600 hover:bg-blue-500 text-white'
          }
        `}
        aria-label="Copy invite link to clipboard"
      >
        {copied ? (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            Copied!
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            Copy
          </>
        )}
      </button>
    </div>
  );
}
