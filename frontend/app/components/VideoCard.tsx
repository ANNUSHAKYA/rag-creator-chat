import Image from "next/image";
import type { VideoMetadata } from "@/app/types";

type Props = {
  video: VideoMetadata;
  label: "A" | "B";
};

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 text-center">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-white font-bold text-sm">{value}</p>
    </div>
  );
}

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function VideoCard({ video, label }: Props) {
  const isA = label === "A";

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div
        className={`px-4 py-3 border-b border-gray-800 flex items-center gap-2 ${
          isA ? "bg-blue-600/20" : "bg-purple-600/20"
        }`}
      >
        <span
          className={`text-white text-xs font-bold px-2 py-0.5 rounded ${
            isA ? "bg-blue-600" : "bg-purple-600"
          }`}
        >
          VIDEO {label}
        </span>
        <span className="text-xs text-gray-400 capitalize">{video.platform}</span>
      </div>

      {/* Thumbnail */}
      {video.thumbnail && (
        <div className="relative aspect-video bg-gray-800">
          <Image
            src={video.thumbnail}
            alt={video.title}
            fill
            unoptimized
            className="object-cover"
          />
          <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded">
            {Math.floor(video.duration_seconds / 60)}:
            {String(video.duration_seconds % 60).padStart(2, "0")}
          </div>
        </div>
      )}

      {/* Info */}
      <div className="p-4 space-y-3">
        <div>
          <h3 className="text-white font-semibold text-sm line-clamp-2 mb-1">
            {video.title || "Untitled"}
          </h3>
          <p className="text-gray-400 text-xs">
            by <span className="text-gray-200">{video.creator}</span>
            {video.follower_count != null && (
              <span className="ml-2 text-gray-500">
                · {fmt(video.follower_count)} followers
              </span>
            )}
          </p>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2">
          <StatBox label="Views" value={fmt(video.views)} />
          <StatBox label="Likes" value={fmt(video.likes)} />
          <StatBox label="Comments" value={fmt(video.comments)} />
          <StatBox label="Engagement" value={`${video.engagement_rate}%`} />
        </div>

        {/* Engagement bar */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Engagement rate</span>
            <span className={`font-semibold ${isA ? "text-blue-400" : "text-purple-400"}`}>
              {video.engagement_rate}%
            </span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                isA ? "bg-blue-500" : "bg-purple-500"
              }`}
              style={{ width: `${Math.min(video.engagement_rate * 10, 100)}%` }}
            />
          </div>
        </div>

        {/* Hashtags */}
        {video.hashtags && (
          <div className="flex flex-wrap gap-1">
            {(Array.isArray(video.hashtags)
              ? video.hashtags
              : typeof video.hashtags === "string"
              ? video.hashtags.split(", ")
              : []
            )
              .filter(Boolean)
              .slice(0, 5)
              .map((tag) => (
                <span
                  key={tag}
                  className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded-full"
                >
                  #{tag}
                </span>
              ))}
          </div>
        )}

        {/* Upload date */}
        {video.upload_date && (
          <p className="text-xs text-gray-600">
            Uploaded: {video.upload_date}
          </p>
        )}
      </div>
    </div>
  );
}
