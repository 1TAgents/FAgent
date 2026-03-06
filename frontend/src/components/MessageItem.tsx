import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface MessageItemProps {
  role: 'user' | 'assistant';
  content: string;
}

export function MessageItem({ role, content }: MessageItemProps) {
  return (
    <div
      className={cn(
        "group w-full text-gray-800 dark:text-gray-100 border-b border-black/10 dark:border-gray-900/50",
        role === 'assistant' ? "bg-gray-50 dark:bg-[#444654]" : "dark:bg-gray-800"
      )}
    >
      <div className="text-base gap-4 md:gap-6 md:max-w-2xl lg:max-w-xl xl:max-w-3xl p-4 md:py-6 flex lg:px-0 m-auto">
        <div className="flex flex-col relative items-end">
          <Avatar className="h-8 w-8">
            <AvatarFallback className={cn(
              "text-white text-xs font-medium",
              role === 'assistant' ? "bg-green-500" : "bg-purple-500"
            )}>
              {role === 'assistant' ? 'AI' : 'U'}
            </AvatarFallback>
          </Avatar>
        </div>
        <div className="relative flex-1 overflow-hidden leading-7 prose dark:prose-invert max-w-none break-words">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
