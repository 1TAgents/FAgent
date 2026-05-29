import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { Message } from '@/types';

interface MessageItemProps {
  role: Message['role'];
  content: string;
}

export function MessageItem({ role, content }: MessageItemProps) {
  const isUser = role === 'user';
  const avatarLabel = role === 'system' ? 'SYS' : isUser ? 'You' : 'AI';
  
  return (
    <div
      className={cn(
        "group w-full text-gray-800 dark:text-gray-100 border-b border-black/5 dark:border-white/10",
        isUser ? "bg-white dark:bg-[#343541]" : "bg-[#f7f7f8] dark:bg-[#444654]"
      )}
    >
      <div className="text-base gap-4 md:gap-6 md:max-w-2xl lg:max-w-xl xl:max-w-3xl p-4 md:py-6 flex lg:px-0 m-auto">
        {/* 头像 */}
        <div className={cn("flex flex-col relative shrink-0", isUser && "order-2")}>
          <Avatar className={cn("h-8 w-8", isUser ? "bg-[#10a37f]" : "bg-[#e69100]")}>
            <AvatarFallback className="text-white text-xs font-medium">
              {avatarLabel}
            </AvatarFallback>
          </Avatar>
        </div>
        
        {/* 消息内容 */}
        <div className={cn("relative flex-1 overflow-hidden leading-7 prose dark:prose-invert max-w-none break-words", isUser && "order-1")}>
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
