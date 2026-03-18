/**
 * 市场切换器组件
 * 
 * 用于在股票和期货模式之间切换
 */
import React from 'react';

interface MarketSwitcherProps {
  mode: 'stock' | 'future';
  onModeChange: (mode: 'stock' | 'future') => void;
}

export const MarketSwitcher: React.FC<MarketSwitcherProps> = ({
  mode,
  onModeChange,
}) => {
  return (
    <div className="inline-flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
      <button
        onClick={() => onModeChange('stock')}
        className={`
          flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all
          ${
            mode === 'stock'
              ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
          }
        `}
      >
        <span>📈</span>
        <span>股票</span>
      </button>
      
      <button
        onClick={() => onModeChange('future')}
        className={`
          flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all
          ${
            mode === 'future'
              ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
          }
        `}
      >
        <span>📉</span>
        <span>期货</span>
      </button>
    </div>
  );
};
