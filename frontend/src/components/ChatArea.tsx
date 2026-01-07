import React from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
}

export function ChatArea({ messages, isLoading, sendMessage, stopGeneration }: ChatAreaProps) {
  return (
    <div className="flex-1 flex flex-col h-full relative">
      <div className="flex-1 overflow-hidden relative w-full h-full">
        <MessageList messages={messages} />
      </div>
      <div className="w-full pt-2 md:pt-0 dark:border-white/20 md:border-transparent md:dark:border-transparent md:w-[calc(100%-.5rem)]">
        <ChatInput 
          onSend={sendMessage} 
          isLoading={isLoading} 
          onStop={stopGeneration}
        />
      </div>
    </div>
  );
}
