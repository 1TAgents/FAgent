import React from 'react';
import type { ChatSession } from '@/types';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  conversations: ChatSession[];
  onSelectSession: (id: string) => void;
  currentSessionId?: string;
  onNewChat: () => void;
}

export function Sidebar({ conversations, onSelectSession, currentSessionId, onNewChat }: SidebarProps) {
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
        <div className="flex flex-col gap-2 py-2">
          {conversations.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={cn(
                "flex items-center gap-3 px-3 py-3 text-sm text-zinc-100 rounded-md transition-colors hover:bg-zinc-900 text-left truncate w-full",
                currentSessionId === session.id && "bg-zinc-800"
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0 text-zinc-400" />
              <span className="truncate flex-1">{session.title}</span>
            </button>
          ))}
        </div>
      </ScrollArea>
      
      <div className="p-4 border-t border-zinc-800">
        <div className="text-sm text-zinc-400">User Profile</div>
      </div>
    </div>
  );
}
