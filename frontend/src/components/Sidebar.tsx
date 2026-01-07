import React, { useMemo } from 'react';
import type { ChatSession } from '@/types';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  conversations: ChatSession[];
  onSelectSession: (id: string) => void;
  currentSessionId?: string;
  onNewChat: () => void;
}

export function Sidebar({ conversations, onSelectSession, currentSessionId, onNewChat }: SidebarProps) {
  
  const groupedConversations = useMemo(() => {
    const groups: Record<string, ChatSession[]> = {
      'Today': [],
      'Yesterday': [],
      'Previous 7 Days': [],
      'Previous 30 Days': [],
      'Older': []
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterday = today - 86400000;
    const last7Days = today - 86400000 * 7;
    const last30Days = today - 86400000 * 30;

    // Sort by updated time desc first
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

    sorted.forEach(session => {
      const time = session.updatedAt;
      if (time >= today) {
        groups['Today'].push(session);
      } else if (time >= yesterday) {
        groups['Yesterday'].push(session);
      } else if (time >= last7Days) {
        groups['Previous 7 Days'].push(session);
      } else if (time >= last30Days) {
        groups['Previous 30 Days'].push(session);
      } else {
        groups['Older'].push(session);
      }
    });

    return groups;
  }, [conversations]);

  return (
    <div className="w-[260px] bg-black text-white flex flex-col h-full border-r border-zinc-800 hidden md:flex">
      <div className="p-3">
        <Button 
          variant="outline" 
          className="w-full justify-start gap-2 bg-transparent text-white border-white/20 hover:bg-zinc-900"
          onClick={onNewChat}
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="flex flex-col gap-4 py-2">
          {Object.entries(groupedConversations).map(([label, sessions]) => {
            if (sessions.length === 0) return null;
            return (
              <div key={label}>
                <div className="px-3 py-2 text-xs font-medium text-zinc-500">{label}</div>
                <div className="flex flex-col gap-1">
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => onSelectSession(session.id)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 text-sm text-zinc-100 rounded-md transition-colors hover:bg-zinc-900 text-left truncate w-full group relative",
                        currentSessionId === session.id && "bg-zinc-800"
                      )}
                    >
                      <span className="truncate flex-1">{session.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
      
      <div className="p-4 border-t border-zinc-800">
        <div className="text-sm text-zinc-400">User Profile</div>
      </div>
    </div>
  );
}
