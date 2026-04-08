import React, { useEffect, useState } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types';
import { PanelLeftOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getAvailableModels, type AvailableModel } from '@/lib/api';

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
  const [model, setModel] = useState("qwen3.5-plus");
  const [models, setModels] = useState<AvailableModel[]>([
    { id: 'qwen3.5-plus', name: 'Qwen 3.5 Plus' }
  ]);

  useEffect(() => {
    let cancelled = false;

    const loadModels = async () => {
      try {
        const result = await getAvailableModels();
        if (cancelled || !result.models?.length) return;

        setModels(result.models);
        setModel((current) => {
          if (result.models.some((item) => item.id === current)) {
            return current;
          }
          return result.default || result.models[0].id;
        });
      } catch (error) {
        console.error('加载模型列表失败:', error);
      }
    };

    void loadModels();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex-1 flex flex-col h-full relative bg-white dark:bg-[#343541]">
      {/* 顶部栏 - 简化版，只有侧边栏切换按钮 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-black/5 dark:border-white/10 absolute top-0 left-0 right-0 z-10">
        <div className="flex items-center gap-2">
          {!isSidebarOpen && (
            <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
              <PanelLeftOpen className="h-5 w-5" />
            </Button>
          )}
        </div>
      </div>

      {/* 消息列表区域 */}
      <div className="flex-1 overflow-hidden relative w-full h-full pt-[60px]">
        <MessageList messages={messages} />
      </div>
      
      {/* 输入框区域 */}
      <div className="w-full pt-2 md:pt-0 mx-auto bg-white dark:bg-[#343541]">
        <ChatInput 
          onSend={(content) => sendMessage(content, model)} 
          isLoading={isLoading} 
          onStop={stopGeneration}
          model={model}
          models={models}
          onModelChange={setModel}
        />
      </div>
    </div>
  );
}
