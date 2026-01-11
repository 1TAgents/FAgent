import React from 'react';
import { Sidebar } from './Sidebar';
import { ChatArea } from './ChatArea';
import { useChat } from '@/hooks/useChat';

export function Layout() {
  const { 
    conversations, 
    selectSession, 
    currentSessionId, 
    resetSession,
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    deleteSession,
    renameSession
  } = useChat();

  return (
    <div className="flex h-screen bg-white dark:bg-zinc-950 overflow-hidden">
      <Sidebar 
        conversations={conversations}
        onSelectSession={selectSession}
        currentSessionId={currentSessionId}
        onNewChat={resetSession}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
      />
      <ChatArea 
        messages={messages}
        isLoading={isLoading}
        sendMessage={sendMessage}
        stopGeneration={stopGeneration}
      />
    </div>
  );
}
