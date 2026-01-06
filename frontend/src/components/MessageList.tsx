import React, { useEffect, useRef } from 'react';
import { MessageItem } from './MessageItem';
import type { Message } from '@/types';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-10 h-full scroll-smooth">
      <div className="flex flex-col items-center text-sm dark:bg-gray-800">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <h2 className="text-2xl font-bold mb-2">FAgent</h2>
            <p>Start a new conversation</p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem key={msg.id} role={msg.role} content={msg.content} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
