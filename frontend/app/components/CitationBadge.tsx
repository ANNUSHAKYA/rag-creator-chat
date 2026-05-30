import type { Citation } from "@/app/types";

export default function CitationBadge({ citation }: { citation: Citation }) {
  const isA = citation.video_id === "A";
  return (
    <span
      title={citation.preview}
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full cursor-help border ${
        isA
          ? "bg-blue-900/40 text-blue-300 border-blue-800"
          : "bg-purple-900/40 text-purple-300 border-purple-800"
      }`}
    >
      Video {citation.video_id}
      {citation.is_hook && " · hook"}
      {" · chunk "}
      {citation.chunk_index}
    </span>
  );
}
