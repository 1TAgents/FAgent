/**
 * 市场模块 API
 */

export interface MarketModuleInfo {
  name: string;
  display_name: string;
  available: boolean;
}

export interface MarketChatRequest {
  message: string;
  mode?: 'stock' | 'future' | null;
  context?: Record<string, any>;
}

export interface MarketChatResponse {
  reply: string;
  data?: Record<string, any>;
  suggestions?: string[];
  mode: string;
}

/**
 * 获取市场模块信息
 */
export async function getMarketModules(): Promise<Record<string, MarketModuleInfo>> {
  const response = await fetch('/api/chat/market/modules');
  if (!response.ok) {
    throw new Error('获取模块信息失败');
  }
  return response.json();
}

/**
 * 发送市场模块聊天请求
 */
export async function sendMarketChat(
  request: MarketChatRequest
): Promise<MarketChatResponse> {
  const response = await fetch('/api/chat/market/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || '发送消息失败');
  }
  
  return response.json();
}
