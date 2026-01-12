import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { ChatArea } from './ChatArea';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

export function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
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
      <div 
        className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0",
          isSidebarOpen ? "w-[260px]" : "w-0"
        )}
      >
        <div className="w-[260px] h-full">
          <Sidebar 
            conversations={conversations}
            onSelectSession={selectSession}
            currentSessionId={currentSessionId}
            onNewChat={resetSession}
            onDeleteSession={deleteSession}
            onRenameSession={renameSession}
            onToggleSidebar={() => setIsSidebarOpen(false)}
          />
        </div>
      </div>
      <ChatArea 
        messages={messages}
        isLoading={isLoading}
        sendMessage={sendMessage}
        stopGeneration={stopGeneration}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />
    </div>
  );
}
