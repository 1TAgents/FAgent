/**
 * 市场模式持久化 Hook
 * 
 * 保存用户选择的市场模式到 localStorage
 */
import { useState, useEffect } from 'react';

type MarketMode = 'stock' | 'future';

const STORAGE_KEY = 'fagent_market_mode';

export function useMarketMode(): [MarketMode, (mode: MarketMode) => void] {
  const [mode, setModeState] = useState<MarketMode>('stock');

  // 从 localStorage 加载
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as MarketMode | null;
    if (saved && ['stock', 'future'].includes(saved)) {
      setModeState(saved);
    }
  }, []);

  // 保存到 localStorage
  const setMode = (newMode: MarketMode) => {
    setModeState(newMode);
    localStorage.setItem(STORAGE_KEY, newMode);
  };

  return [mode, setMode];
}
