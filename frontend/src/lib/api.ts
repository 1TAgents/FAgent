import type { Message } from '@/types';

const USE_MOCK = false; // Set to true to force mock mode

// 模拟延迟
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// 生成 Request ID (8位 UUID)
const generateRequestId = () => crypto.randomUUID().slice(0, 8);

// 模拟流式响应数据
const MOCK_RESPONSE = `这是一个模拟的流式响应（Mock Mode）。
如果您看到这条消息，说明后端服务不可用或已启用 Mock 模式。
请确保后端服务 (Port 8000) 已启动。`;

/**
 * 创建新会话
 */
export async function createSession(): Promise<number> {
  if (USE_MOCK) return 1;

  try {
    const response = await fetch('/api/chat/session/create', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Request-ID': generateRequestId()
      },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    const data = await response.json();
    return data.cid;
  } catch (error) {
    console.warn('Backend not available, falling back to mock session ID');
    if (process.env.NODE_ENV === 'development') {
        // Fallback for development if backend is down
        return 999; 
    }
    throw error;
  }
}

/**
 * 获取会话列表
 */
export async function getConversations(limit = 20, offset = 0) {
  if (USE_MOCK) return { conversations: [], count: 0 };

  const response = await fetch(`/api/chat/conversations?limit=${limit}&offset=${offset}`, {
    headers: {
      'X-Request-ID': generateRequestId()
    }
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 获取会话消息
 */
export async function getMessages(cid: number) {
  if (USE_MOCK) return { messages: [], count: 0 };

  const response = await fetch(`/api/chat/conversation/${cid}/messages`, {
    headers: {
      'X-Request-ID': generateRequestId()
    }
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 删除会话
 */
export async function deleteSession(cid: string) {
  if (USE_MOCK) return;
  
  const response = await fetch(`/api/chat/conversation/${cid}`, {
    method: 'DELETE',
    headers: {
      'X-Request-ID': generateRequestId()
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`);
  }
}

/**
 * 重命名会话
 */
export async function renameSession(cid: string, title: string) {
  if (USE_MOCK) return;
  
  // 注意：后端接口可能尚未就绪，如果返回 404/405 请忽略或处理
  const response = await fetch(`/api/chat/conversation/${cid}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': generateRequestId()
    },
    body: JSON.stringify({ title })
  });
  
  if (!response.ok) {
    // 暂时允许失败，因为后端接口可能未实现
    console.warn(`Failed to rename session (backend might not support it): ${response.statusText}`);
    // throw new Error(`Failed to rename session: ${response.statusText}`);
    return; 
  }
  return response.json();
}

/**
 * 发送消息并处理流式响应
 * @param cid 会话 ID
 * @param content 用户消息内容
 * @param onChunk 接收到数据块时的回调
 * @param signal AbortSignal 用于取消请求
 */
export async function sendMessageStream(
  cid: number,
  content: string,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  
  if (USE_MOCK || cid === 999) {
    await delay(500);
    const chunks = MOCK_RESPONSE.split('');
    for (const char of chunks) {
      if (signal?.aborted) break;
      await delay(30);
      onChunk(char);
    }
    return;
  }

  try {
    const response = await fetch('/api/chat/send/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': generateRequestId()
      },
      body: JSON.stringify({
        cid,
        user_message: content,
        temperature: 0.7
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('Response body is empty');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep the last incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);
          if (dataStr === '[DONE]') continue;
          
          try {
            const data = JSON.parse(dataStr);
            if (data.content) {
              onChunk(data.content);
            }
            if (data.error) {
              console.error('Stream error from backend:', data.error);
              onChunk(`\n[Error: ${data.error}]`);
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', dataStr);
          }
        }
      }
    }
  } catch (error) {
    if (signal?.aborted) {
      console.log('Request aborted');
    } else {
      console.error('Stream error:', error);
      // 如果是网络错误，尝试回退到 Mock 提示（仅开发环境）
      onChunk(`\n[Network Error: ${error instanceof Error ? error.message : String(error)}]`);
      throw error;
    }
  }
}
