/**
 * Chat panel component.
 * Supports public chat and traitor-only chat (for traitors).
 */

import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../../types/live';

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string, channel: 'public' | 'traitor') => void;
  isTraitor: boolean;
  disabled?: boolean;
}

export function ChatPanel({
  messages,
  onSend,
  isTraitor,
  disabled = false,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [channel, setChannel] = useState<'public' | 'traitor'>('public');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed, isTraitor ? channel : 'public');
    setInput('');
  };

  // Filter messages based on channel visibility
  const visibleMessages = messages.filter(
    (m) => m.channel === 'public' || (m.channel === 'traitor' && isTraitor)
  );

  return (
    <div className="h-full flex flex-col bg-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300">Chat</h3>
        {isTraitor && (
          <div className="flex rounded-lg bg-gray-700 p-0.5">
            <button
              onClick={() => setChannel('public')}
              className={`
                px-2.5 py-1 text-xs font-medium rounded-md transition-colors
                ${channel === 'public' ? 'bg-gray-600 text-white' : 'text-gray-400 hover:text-white'}
              `}
            >
              Public
            </button>
            <button
              onClick={() => setChannel('traitor')}
              className={`
                px-2.5 py-1 text-xs font-medium rounded-md transition-colors
                ${channel === 'traitor' ? 'bg-red-600 text-white' : 'text-gray-400 hover:text-white'}
              `}
            >
              🗡️ Traitor
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {visibleMessages.length === 0 ? (
          <p className="text-center text-gray-500 text-sm py-8">
            No messages yet. Start the conversation!
          </p>
        ) : (
          visibleMessages.map((message, i) => (
            <ChatMessageBubble key={i} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="p-3 border-t border-gray-700"
      >
        <div className="flex gap-2">
          <input
            name="chatMessage"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              isTraitor && channel === 'traitor'
                ? 'Message fellow Traitors…'
                : 'Type a message…'
            }
            autoComplete="off"
            disabled={disabled}
            maxLength={500}
            className={`
              flex-1 px-3 py-2 bg-gray-700 border rounded-lg text-white text-sm
              placeholder-gray-500 focus:ring-1 focus:outline-none
              ${
                channel === 'traitor' && isTraitor
                  ? 'border-red-600/50 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-600 focus:border-blue-500 focus:ring-blue-500'
              }
              disabled:opacity-50
            `}
          />
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm transition-colors
              ${
                channel === 'traitor' && isTraitor
                  ? 'bg-red-600 hover:bg-red-500 text-white'
                  : 'bg-blue-600 hover:bg-blue-500 text-white'
              }
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isTraitorChat = message.channel === 'traitor';

  return (
    <div
      className={`
        p-3 rounded-lg
        ${isTraitorChat ? 'bg-red-500/10 border border-red-500/30' : 'bg-gray-700/50'}
      `}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-sm font-medium ${isTraitorChat ? 'text-red-400' : 'text-blue-400'}`}>
          {message.sender_name}
        </span>
        {isTraitorChat && (
          <span className="text-xs text-red-400/60">🗡️</span>
        )}
        <span className="text-xs text-gray-500">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {/* Message content */}
      <p className="text-sm text-gray-200 break-words">{message.message}</p>
    </div>
  );
}

function formatTime(timestamp: string | number): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}
