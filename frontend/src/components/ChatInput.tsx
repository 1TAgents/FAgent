import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import type { AvailableModel } from '@/lib/api';

interface ChatInputProps {
  onSend: (content: string) => void;
  isLoading: boolean;
  onStop: () => void;
  model?: string;
  models?: AvailableModel[];
  onModelChange?: (model: string) => void;
}

const fallbackModels: AvailableModel[] = [
  { id: 'deepseek-v4-pro', name: 'DeepSeek V4 Pro' },
];

export function ChatInput({
  onSend,
  isLoading,
  onStop,
  model = 'deepseek-v4-pro',
  models = fallbackModels,
  onModelChange
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    adjustHeight();
  };

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto'; // Reset height
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (isLoading) return;
    if (!input.trim()) return;
    
    onSend(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input]);

  const currentModel = models.find(m => m.id === model) || models[0] || fallbackModels[0];

  return (
    <div className="stretch mx-2 flex flex-row gap-3 last:mb-2 md:mx-4 md:last:mb-6 lg:mx-auto lg:max-w-2xl xl:max-w-3xl">
      <div className="relative flex h-full flex-1 flex-col">
        <div className="relative rounded-xl bg-white dark:bg-[#40414f] shadow-[0_0_0_1px_rgba(0,0,0,0.05)] dark:shadow-none border border-gray-200 dark:border-transparent overflow-visible">
          <Textarea
            ref={textareaRef}
            className="min-h-[24px] w-full resize-none border-0 shadow-none focus-visible:ring-0 px-4 py-4 pr-24 bg-transparent text-gray-900 dark:text-gray-100 placeholder:text-gray-400"
            placeholder="Send a message..."
            rows={1}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            style={{ maxHeight: '200px', overflowY: 'auto' }}
          />
          
          {/* 模型选择下拉框 */}
          <div className="absolute bottom-2 right-14 flex items-center gap-1">
            <div className="relative">
              <button
                onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
                className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                {currentModel.name}
                <ChevronDown className="w-3 h-3" />
              </button>
              
              {isModelMenuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setIsModelMenuOpen(false)} />
                  <div className="absolute bottom-full right-0 mb-2 w-48 bg-white dark:bg-[#343541] border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-20 py-1 overflow-hidden">
                    {models.map(m => (
                      <button
                        key={m.id}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors ${
                          m.id === model 
                            ? 'text-green-600 dark:text-green-400 bg-gray-50 dark:bg-gray-700' 
                            : 'text-gray-700 dark:text-gray-200'
                        }`}
                        onClick={() => {
                          onModelChange?.(m.id);
                          setIsModelMenuOpen(false);
                        }}
                      >
                        {m.name}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
          
          {/* 发送/停止按钮 */}
          <Button
            size="icon"
            variant="ghost"
            onClick={isLoading ? onStop : handleSend}
            disabled={!input.trim() && !isLoading}
            className={`absolute bottom-2 right-2 h-8 w-8 rounded-lg transition-all ${
              input.trim() || isLoading
                ? 'bg-green-600 hover:bg-green-700 text-white' 
                : 'bg-gray-200 dark:bg-gray-600 text-gray-400 dark:text-gray-300'
            }`}
          >
            {isLoading ? (
              <Square className="h-4 w-4 fill-current" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        
        <div className="text-center mt-2">
          <p className="text-xs text-gray-400">AI can make mistakes. Please check important info.</p>
        </div>
      </div>
    </div>
  );
}
