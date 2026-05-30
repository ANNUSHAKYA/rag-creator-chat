"use client";

import { useStore } from "@/app/store/useStore";
import IngestForm from "@/app/components/IngestForm";
import VideoCard from "@/app/components/VideoCard";
import ChatPanel from "@/app/components/ChatPanel";

export default function Home() {
  const { session, error } = useStore();

  if (!session) return <IngestForm />;

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Top bar */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <span className="text-xs font-bold text-white">AI</span>
          </div>
          <h1 className="text-base font-bold text-white">Creator Analytics RAG</h1>
        </div>
        <button
          onClick={() => useStore.setState({ session: null, messages: [] })}
          className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-800"
        >
          ← New Analysis
        </button>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mt-4 bg-red-900/30 border border-red-700/50 text-red-300 rounded-xl px-4 py-3 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Main layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left sidebar — video cards */}
        <aside className="w-80 shrink-0 p-4 space-y-4 overflow-y-auto border-r border-gray-800">
          <VideoCard video={session.video_a} label="A" />
          <VideoCard video={session.video_b} label="B" />
        </aside>

        {/* Right — chat */}
        <main className="flex-1 p-4 min-h-0">
          <ChatPanel />
        </main>
      </div>
    </div>
  );
}
