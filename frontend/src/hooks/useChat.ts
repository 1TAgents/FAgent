import { useState, useCallback, useRef, useEffect } from 'react';
import type { Message, ChatSession } from '@/types';
import { sendMessageStream, createSession, getConversations, getMessages } from '@/lib/api';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [cid, setCid] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ChatSession[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 加载会话列表
  const fetchConversations = useCallback(async () => {
    try {
      const data = await getConversations();
      // 假设后端返回的数据结构匹配，或者需要适配
      const list = data.conversations.map((c: any) => ({
        id: c.cid.toString(),
        title: `Conversation ${c.cid}`,
        messages: [],
        createdAt: c.created_at ? new Date(c.created_at).getTime() : Date.now(),
        updatedAt: c.updated_at ? new Date(c.updated_at).getTime() : Date.now(),
      }));
      setConversations(list);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    }
  }, []);

  // 加载特定会话
  const selectSession = useCallback(async (sessionId: string) => {
    // 如果正在生成，先停止
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    setIsLoading(true);
    setMessages([]); // 先清空当前消息

    try {
      const numericCid = parseInt(sessionId);
      setCid(numericCid);
      
      const data = await getMessages(numericCid);
      const msgs = data.messages.map((m: any) => ({
        id: m.message_id.toString(),
        role: m.role,
        content: m.content,
        createdAt: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
      }));
      setMessages(msgs);
    } catch (error) {
      console.error(`Failed to load session ${sessionId}:`, error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 初始化加载会话列表
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

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
      let isNewSession = false;
      if (currentCid === null) {
        currentCid = await createSession();
        setCid(currentCid);
        isNewSession = true;
      }

      // 5. 调用 API 并流式更新
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

      // 如果是新会话，刷新列表
      if (isNewSession) {
        fetchConversations();
      }

    } catch (error) {
      console.error('Failed to send message:', error);
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
  }, [cid, fetchConversations]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
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
    resetSession,
    conversations,
    selectSession,
    currentSessionId: cid?.toString(),
    fetchConversations
  };
}
