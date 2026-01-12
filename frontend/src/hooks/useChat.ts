import { useState, useCallback, useRef, useEffect } from 'react';
import type { Message, ChatSession } from '@/types';
import { sendMessageStream, createSession, getConversations, getMessages, deleteSession as apiDeleteSession, renameSession as apiRenameSession } from '@/lib/api';

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
        title: c.title || `Conversation ${c.cid}`,
        messages: [],
        createdAt: c.created_at ? new Date(c.created_at).getTime() : Date.now(),
        updatedAt: c.updated_at ? new Date(c.updated_at).getTime() : Date.now(),
      }));
      setConversations(list);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    }
  }, []);

  // 删除会话
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiDeleteSession(sessionId);
      
      // Update local state
      setConversations(prev => prev.filter(c => c.id !== sessionId));
      
      // If deleted session is active, reset
      if (cid?.toString() === sessionId) {
        setCid(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      // Could add toast notification here
    }
  }, [cid]);

  // 重命名会话
  const renameSession = useCallback(async (sessionId: string, newTitle: string) => {
    try {
      // Optimistic update
      setConversations(prev => prev.map(c => 
        c.id === sessionId ? { ...c, title: newTitle } : c
      ));

      await apiRenameSession(sessionId, newTitle);
    } catch (error) {
      console.error('Failed to rename session:', error);
      // Revert on error would go here, simplified for now
      fetchConversations();
    }
  }, [fetchConversations]);

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

  const sendMessage = useCallback(async (content: string, model?: string) => {
    if (!content.trim()) return;

    // 如果没有会话，先创建
    let currentCid = cid;
    if (!currentCid) {
      try {
        setIsLoading(true);
        currentCid = await createSession();
        setCid(currentCid);
        
        // Optimistically add new session to list
        const newSession: ChatSession = {
          id: currentCid.toString(),
          title: 'New Chat',
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now()
        };
        setConversations(prev => [newSession, ...prev]);
      } catch (error) {
        console.error('Failed to create session:', error);
        setIsLoading(false);
        return;
      }
    }

    // 添加用户消息
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      createdAt: Date.now(),
    };
    
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // 创建新的 AI 消息占位
    const aiMsgId = (Date.now() + 1).toString();
    const aiMsg: Message = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
    };
    setMessages(prev => [...prev, aiMsg]);

    try {
      abortControllerRef.current = new AbortController();
      
      await sendMessageStream(
        currentCid,
        content,
        (chunk) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMsgId 
              ? { ...msg, content: msg.content + chunk }
              : msg
          ));
        },
        abortControllerRef.current.signal,
        model
      );
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Generation stopped by user');
      } else {
        console.error('Failed to send message:', error);
        setMessages(prev => prev.map(msg => 
          msg.id === aiMsgId 
            ? { ...msg, content: msg.content + '\n[Error: Failed to generate response]' }
            : msg
        ));
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      // Refresh conversations list to update timestamp/preview
      // fetchConversations(); 
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
    deleteSession,
    renameSession,
    currentSessionId: cid?.toString(),
    fetchConversations
  };
}
