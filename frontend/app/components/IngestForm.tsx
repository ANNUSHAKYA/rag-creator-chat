"use client";

import { useState } from "react";
import { useStore } from "@/app/store/useStore";
import type { Platform } from "@/app/types";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function IngestForm() {
  const { setSession, setIsIngesting, setError, isIngesting, error } = useStore();
  const [videoA, setVideoA] = useState({ url: "", platform: "youtube" as Platform });
  const [videoB, setVideoB] = useState({ url: "", platform: "youtube" as Platform });
  const [progress, setProgress] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoA.url || !videoB.url) return;

    setIsIngesting(true);
    setError(null);
    setProgress("Fetching transcripts and metadata...");

    try {
      const res = await fetch(`${API}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_a_url: videoA.url,
          video_a_platform: videoA.platform,
          video_b_url: videoB.url,
          video_b_platform: videoB.platform,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Ingest failed");
      }

      const data = await res.json();
      setProgress("Embedding transcripts into vector DB...");
      await new Promise((r) => setTimeout(r, 500));

      setSession({
        session_id: data.session_id,
        video_a: data.video_a.metadata,
        video_b: data.video_b.metadata,
      });
    } catch (err: any) {
      setError(err.message ?? "Something went wrong during ingest.");
    } finally {
      setIsIngesting(false);
      setProgress("");
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Hero */}
        <div className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs font-medium px-3 py-1.5 rounded-full mb-4">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
            RAG-powered · Streaming · Citations
          </div>
          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
            Creator Analytics
          </h1>
          <p className="text-gray-400 text-lg">
            Drop two video URLs. Ask anything. Get answers grounded in real transcript data.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Video A */}
          <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800 ring-1 ring-blue-500/0 focus-within:ring-blue-500/30 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <span className="bg-blue-600 text-white text-xs font-bold px-2.5 py-1 rounded-lg">
                VIDEO A
              </span>
              <span className="text-gray-500 text-xs">First video to analyse</span>
            </div>
            <div className="flex gap-3">
              <select
                value={videoA.platform}
                onChange={(e) => setVideoA({ ...videoA, platform: e.target.value as Platform })}
                className="bg-gray-800 text-white border border-gray-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="youtube">YouTube</option>
                <option value="instagram">Instagram</option>
              </select>
              <input
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={videoA.url}
                onChange={(e) => setVideoA({ ...videoA, url: e.target.value })}
                className="flex-1 bg-gray-800 text-white border border-gray-700 rounded-xl px-4 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-gray-800" />
            <span className="text-gray-600 text-xs font-medium">vs</span>
            <div className="flex-1 h-px bg-gray-800" />
          </div>

          {/* Video B */}
          <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800 ring-1 ring-purple-500/0 focus-within:ring-purple-500/30 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <span className="bg-purple-600 text-white text-xs font-bold px-2.5 py-1 rounded-lg">
                VIDEO B
              </span>
              <span className="text-gray-500 text-xs">Second video to compare</span>
            </div>
            <div className="flex gap-3">
              <select
                value={videoB.platform}
                onChange={(e) => setVideoB({ ...videoB, platform: e.target.value as Platform })}
                className="bg-gray-800 text-white border border-gray-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 cursor-pointer"
              >
                <option value="youtube">YouTube</option>
                <option value="instagram">Instagram</option>
              </select>
              <input
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={videoB.url}
                onChange={(e) => setVideoB({ ...videoB, url: e.target.value })}
                className="flex-1 bg-gray-800 text-white border border-gray-700 rounded-xl px-4 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-900/30 border border-red-700/50 text-red-300 rounded-xl px-4 py-3 text-sm flex items-start gap-2">
              <span className="mt-0.5">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* Progress */}
          {isIngesting && progress && (
            <div className="bg-blue-900/20 border border-blue-700/40 text-blue-300 rounded-xl px-4 py-3 text-sm flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
              <span>{progress}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isIngesting || !videoA.url || !videoB.url}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-3.5 rounded-xl transition-all duration-200 shadow-lg shadow-blue-900/30"
          >
            {isIngesting ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing videos...
              </span>
            ) : (
              "Analyse Videos →"
            )}
          </button>

          <p className="text-center text-gray-600 text-xs">
            Transcripts are fetched via YouTube Transcript API · Whisper fallback for unsupported videos
          </p>
        </form>
      </div>
    </div>
  );
}
