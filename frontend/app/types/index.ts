export type Platform = "youtube" | "instagram";

export type VideoMetadata = {
  title: string;
  creator: string;
  platform: Platform;
  url: string;
  views: number;
  likes: number;
  comments: number;
  engagement_rate: number;
  follower_count: number | null;
  duration_seconds: number;
  upload_date: string;
  hashtags: string;
  thumbnail?: string;
};

export type Citation = {
  video_id: "A" | "B";
  chunk_index: number;
  is_hook: boolean;
  preview: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
};

export type SessionData = {
  session_id: string;
  video_a: VideoMetadata;
  video_b: VideoMetadata;
};
