/**
 * 市场聊天界面示例
 * 
 * 展示如何集成市场切换器和聊天功能
 */
import React, { useState } from 'react';
import { MarketSwitcher } from '../components/MarketSwitcher';
import { useMarketMode } from '../hooks/useMarketMode';
import { sendMarketChat, MarketChatResponse } from '../api/market';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const MarketChatExample: React.FC = () => {
  const [mode, setMode] = useMarketMode();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (message: string) => {
    if (!message.trim()) return;
    
    setLoading(true);
    try {
      // 添加用户消息
      setMessages(prev => [...prev, { role: 'user', content: message }]);
      
      // 发送请求
      const response = await sendMarketChat({
        message,
        mode,
      });
      
      // 添加助手回复
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.reply 
      }]);
      
      setInput('');
    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '发送失败，请稍后重试' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* 头部：市场切换器 */}
      <div className="border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <MarketSwitcher mode={mode} onModeChange={setMode} />
      </div>
      
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="text-lg">
                当前模式：{mode === 'stock' ? '📈 股票' : '📉 期货'}
              </p>
              <p className="mt-2 text-sm">
                开始提问吧，例如：
              </p>
              <div className="mt-4 space-y-2">
                {mode === 'stock' ? (
                  <>
                    <p className="text-sm">• 帮我看看茅台行情</p>
                    <p className="text-sm">• 平安银行技术指标</p>
                    <p className="text-sm">• 回测双均线策略</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm">• 沪深 300 股指期货行情</p>
                    <p className="text-sm">• 螺纹钢主力合约走势</p>
                    <p className="text-sm">• 回测期货双均线策略</p>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-gray-100'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-gray-100 px-4 py-2 text-gray-400 dark:bg-gray-700">
                  思考中...
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* 输入框 */}
      <div className="border-t border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={`在${mode === 'stock' ? '股票' : '期货'}模式下提问...`}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-500 px-6 py-2 font-medium text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};
