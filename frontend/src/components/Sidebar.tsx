import React from 'react';

export function Sidebar() {
  return (
    <div className="w-[260px] bg-black text-white flex flex-col h-full border-r border-zinc-800 hidden md:flex">
      <div className="p-4">
        <button className="w-full border border-zinc-700 rounded-md p-3 text-left hover:bg-zinc-900 transition-colors text-sm text-zinc-200">
          + New chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {/* Chat History List */}
      </div>
      <div className="p-4 border-t border-zinc-800">
        <div className="text-sm text-zinc-400">User Profile</div>
      </div>
    </div>
  );
}
