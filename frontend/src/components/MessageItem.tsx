import React from 'react';
import { cn } from '@/lib/utils';

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
        <div className="w-[30px] flex flex-col relative items-end">
          <div className={cn(
            "relative h-[30px] w-[30px] p-1 rounded-sm flex items-center justify-center",
            role === 'assistant' ? "bg-green-500" : "bg-purple-500"
          )}>
            {role === 'assistant' ? 'AI' : 'U'}
          </div>
        </div>
        <div className="relative flex-1 overflow-hidden whitespace-pre-wrap leading-7">
          {content}
        </div>
      </div>
    </div>
  );
}
