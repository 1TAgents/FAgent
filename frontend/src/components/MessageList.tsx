import React, { useEffect, useRef } from 'react';
import { MessageItem } from './MessageItem';
import type { Message } from '@/types';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sparkles, MessageCircle, Code2, Lightbulb, Wand2 } from "lucide-react";

interface MessageListProps {
  messages: Message[];
}

const examplePrompts = [
  { icon: Sparkles, text: "Help me write a creative story", desc: "Creative writing assistant" },
  { icon: Code2, text: "Explain how async/await works in JavaScript", desc: "Programming help" },
  { icon: Lightbulb, text: "Give me ideas for a weekend project", desc: "Brainstorming" },
  { icon: Wand2, text: "Help me summarize this article", desc: "Content summarization" },
];

export function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <ScrollArea className="h-full w-full">
      <div className="flex flex-col items-center text-sm pb-32">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] w-full max-w-2xl px-4">
            {/* Logo 标题 */}
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">FAgent</h1>
              <p className="text-gray-500 dark:text-gray-400">Your AI assistant</p>
            </div>
            
            {/* 示例提示按钮 - ChatGPT 风格网格 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              {examplePrompts.map((prompt, index) => (
                <button
                  key={index}
                  className="flex items-start gap-3 p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#202123] hover:bg-gray-50 dark:hover:bg-[#2A2B32] transition-colors text-left group"
                >
                  <div className="p-2 rounded-md bg-gray-100 dark:bg-gray-800 group-hover:bg-gray-200 dark:group-hover:bg-gray-700 transition-colors">
                    <prompt.icon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{prompt.text}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{prompt.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem key={msg.id} role={msg.role} content={msg.content} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}
