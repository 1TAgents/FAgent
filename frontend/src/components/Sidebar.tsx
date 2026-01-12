import React, { useMemo, useState } from 'react';
import type { ChatSession } from '@/types';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Pencil, Trash2, Check, X, MessageSquare, PanelLeftClose, LogIn, LogOut, User as UserIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { AuthModal } from "@/components/AuthModal";

interface SidebarProps {
  conversations: ChatSession[];
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  currentSessionId?: string;
  onNewChat: () => void;
  onToggleSidebar: () => void;
}

export function Sidebar({ 
  conversations, 
  onSelectSession, 
  onDeleteSession, 
  onRenameSession, 
  currentSessionId, 
  onNewChat,
  onToggleSidebar
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  
  const { user, isAuthenticated, logout } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  
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

  const handleStartEdit = (e: React.MouseEvent, session: ChatSession) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingId && editTitle.trim()) {
      onRenameSession(editingId, editTitle.trim());
      setEditingId(null);
    }
  };

  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeleteId(id);
  };

  const confirmDelete = () => {
    if (deleteId) {
      onDeleteSession(deleteId);
      setDeleteId(null);
    }
  };

  return (
    <div className="w-full bg-black text-white flex flex-col h-full border-r border-zinc-800 flex">
      <div className="p-3 flex items-center gap-2">
        <Button 
          variant="outline" 
          className="flex-1 justify-start gap-2 bg-transparent text-white border-white/20 hover:bg-zinc-900"
          onClick={onNewChat}
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-zinc-400 hover:text-white hover:bg-zinc-900"
          onClick={onToggleSidebar}
        >
          <PanelLeftClose className="h-4 w-4" />
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
                    <div
                      key={session.id}
                      className={cn(
                        "group flex items-center gap-2 px-3 py-2 text-sm text-zinc-100 rounded-md transition-colors hover:bg-zinc-900 cursor-pointer relative",
                        currentSessionId === session.id && "bg-zinc-800"
                      )}
                      onClick={() => onSelectSession(session.id)}
                    >
                      <MessageSquare className="h-4 w-4 shrink-0 text-zinc-500" />
                      
                      {editingId === session.id ? (
                        <div className="flex items-center gap-1 flex-1 min-w-0" onClick={(e) => e.stopPropagation()}>
                          <Input
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="h-7 px-2 py-0 bg-zinc-950 border-zinc-700 text-xs focus-visible:ring-1 focus-visible:ring-zinc-600"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSaveEdit(e as any);
                              if (e.key === 'Escape') handleCancelEdit(e as any);
                            }}
                          />
                          <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0 hover:bg-zinc-800" onClick={handleSaveEdit}>
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0 hover:bg-zinc-800" onClick={handleCancelEdit}>
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ) : (
                        <>
                          <span className="truncate flex-1">{session.title}</span>
                          
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity absolute right-2 bg-gradient-to-l from-zinc-900 via-zinc-900/80 to-transparent pl-4">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6 text-zinc-400 hover:text-white hover:bg-zinc-700"
                              onClick={(e) => handleStartEdit(e, session)}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6 text-zinc-400 hover:text-red-400 hover:bg-zinc-700"
                              onClick={(e) => handleDeleteClick(e, session.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
      
      <div className="p-4 border-t border-zinc-800">
        {isAuthenticated && user ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="h-8 w-8 rounded-full bg-zinc-700 flex items-center justify-center text-zinc-300">
                <UserIcon className="h-4 w-4" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-medium text-white truncate">{user.username}</span>
                <span className="text-xs text-zinc-500 truncate">Free Plan</span>
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="icon" 
              className="text-zinc-400 hover:text-white hover:bg-zinc-800"
              onClick={logout}
              title="Sign Out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Button 
            className="w-full justify-start gap-2 bg-zinc-800 hover:bg-zinc-700 text-white"
            onClick={() => setIsAuthModalOpen(true)}
          >
            <LogIn className="h-4 w-4" />
            Sign In / Sign Up
          </Button>
        )}
      </div>

      <AuthModal 
        isOpen={isAuthModalOpen} 
        onClose={() => setIsAuthModalOpen(false)} 
      />

      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={confirmDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
