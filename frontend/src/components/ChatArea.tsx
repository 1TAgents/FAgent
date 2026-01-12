import React, { useState } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types';
import { PanelLeftOpen, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (content: string, model?: string) => Promise<void>;
  stopGeneration: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export function ChatArea({ 
  messages, 
  isLoading, 
  sendMessage, 
  stopGeneration,
  isSidebarOpen,
  onToggleSidebar
}: ChatAreaProps) {
  const [model, setModel] = useState("mimo-v2-flash");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const models = ["mimo-v2-flash", "glm-4.5-air", "qwen3-coder", "gpt-oss-120b"];

  return (
    <div className="flex-1 flex flex-col h-full relative">
      <div className="flex items-center justify-between px-4 py-2 border-b border-black/5 dark:border-white/5 bg-white dark:bg-zinc-950 h-[60px]">
        <div className="flex items-center gap-2">
           {!isSidebarOpen && (
              <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
                <PanelLeftOpen className="h-5 w-5" />
              </Button>
           )}
           
           <div className="relative">
             <Button 
               variant="ghost" 
               className="gap-2 text-lg font-semibold text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800"
               onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
             >
               {model}
               <ChevronDown className="h-4 w-4 opacity-50" />
             </Button>
             
             {isModelMenuOpen && (
               <>
                 <div className="fixed inset-0 z-10" onClick={() => setIsModelMenuOpen(false)} />
                 <div className="absolute top-full left-0 mt-1 w-40 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md shadow-lg z-20 py-1">
                   {models.map(m => (
                     <button
                       key={m}
                       className="w-full text-left px-4 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200"
                       onClick={() => {
                         setModel(m);
                         setIsModelMenuOpen(false);
                       }}
                     >
                       {m}
                     </button>
                   ))}
                 </div>
               </>
             )}
           </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative w-full h-full">
        <MessageList messages={messages} />
      </div>
      <div className="w-full pt-2 md:pt-0 dark:border-white/20 md:border-transparent md:dark:border-transparent md:w-[calc(100%-.5rem)] mx-auto">
        <ChatInput 
          onSend={(content) => sendMessage(content, model)} 
          isLoading={isLoading} 
          onStop={stopGeneration}
        />
      </div>
    </div>
  );
}
