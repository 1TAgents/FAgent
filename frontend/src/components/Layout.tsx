import React from 'react';
import { Sidebar } from './Sidebar';
import { ChatArea } from './ChatArea';

export function Layout() {
  return (
    <div className="flex h-screen bg-white dark:bg-zinc-950 overflow-hidden">
      <Sidebar />
      <ChatArea />
    </div>
  );
}
