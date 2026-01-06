import { useState, useCallback, useRef } from 'react';
import type { Message } from '@/types';
import { sendMessageStream, createSession } from '@/lib/api';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [cid, setCid] = useState<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    // 1. 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // 2. 准备 AI 消息占位符
    const aiMessageId = (Date.now() + 1).toString();
    const aiMessage: Message = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      createdAt: Date.now() + 1,
    };

    setMessages((prev) => [...prev, aiMessage]);

    // 3. 创建 AbortController
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      // 4. 确保有会话 ID
      let currentCid = cid;
      if (currentCid === null) {
        currentCid = await createSession();
        setCid(currentCid);
      }

      // 5. 调用 API 并流式更新
      // 注意：这里我们只传递用户的新消息和 CID，后端会自行处理历史上下文
      await sendMessageStream(
        currentCid,
        content,
        (chunk) => {
          setMessages((prev) => {
            return prev.map((msg) => {
              if (msg.id === aiMessageId) {
                return { ...msg, content: msg.content + chunk };
              }
              return msg;
            });
          });
        },
        abortController.signal
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      // 在 AI 消息中显示错误（可选）
      setMessages((prev) => {
        return prev.map((msg) => {
          if (msg.id === aiMessageId) {
            return { ...msg, content: msg.content + `\n[Error: Failed to send message]` };
          }
          return msg;
        });
      });
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [cid]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    // 我们可能想要创建一个新会话，或者保留当前 cid？
    // 这里简单起见只清空前端显示。后端历史依然存在。
    // 如果想要全新开始，应该重置 cid:
    // setCid(null); 
  }, []);

  const resetSession = useCallback(() => {
    setMessages([]);
    setCid(null);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    stopGeneration,
    clearMessages,
    resetSession
  };
}
