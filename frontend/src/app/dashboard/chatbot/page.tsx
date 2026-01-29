"use client";

import { useState, useEffect } from "react";
import { chatApi, analyticsApi, SourceInfo, SourceChunk, SourceFullTextResponse } from "@/lib/api";
import { PDFViewer } from "@/components/PDFViewer";
import Cookies from "js-cookie";

const CHATBOT_URL = process.env.NEXT_PUBLIC_CHATBOT_URL || "http://100.51.125.89:3000";

// Format seconds to MM:SS or HH:MM:SS
function formatTimestamp(seconds: number | undefined): string {
  if (seconds === undefined || seconds === null) return "";
  const secs = Math.floor(seconds);
  const hours = Math.floor(secs / 3600);
  const mins = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${mins}:${s.toString().padStart(2, "0")}`;
}

// Extract YouTube video ID from URL
function getYouTubeVideoId(url: string): string | null {
  if (!url) return null;
  // Match various YouTube URL formats
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?\s]+)/,
    /youtube\.com\/v\/([^&?\s]+)/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

// Build YouTube embed URL with optional start time
function buildYouTubeEmbedUrl(videoId: string, startTime?: number): string {
  let url = `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
  if (startTime !== undefined) {
    url += `&start=${Math.floor(startTime)}`;
  }
  return url;
}

// Source type icons and colors
const sourceTypeConfig: Record<string, { icon: string; label: string; color: string }> = {
  audio: { icon: "🎧", label: "Podcast", color: "bg-purple-100 text-purple-800" },
  pdf: { icon: "📄", label: "Research Paper", color: "bg-red-100 text-red-800" },
  chm_video: { icon: "🎬", label: "CHM Video", color: "bg-blue-100 text-blue-800" },
};

// Tree node component for a source (simplified - no expand/collapse)
function SourceTreeNode({
  source,
  onSelect,
  isSelected,
}: {
  source: SourceInfo;
  onSelect: () => void;
  isSelected: boolean;
}) {
  const config = sourceTypeConfig[source.source_type] || { icon: "📁", label: "Content", color: "bg-gray-100 text-gray-800" };

  return (
    <div
      className={`border-l-2 ${isSelected ? "border-blue-500 bg-blue-50" : "border-transparent hover:bg-gray-50"}`}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer"
        onClick={onSelect}
      >
        {/* Icon */}
        <span className="text-lg">{config.icon}</span>

        {/* Title and metadata */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 truncate">
            {source.title || "Untitled"}
          </div>
          {source.doctors && (
            <div className="text-sm text-gray-500 truncate">{source.doctors}</div>
          )}
        </div>

        {/* Chunk count badge */}
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {source.chunk_count} segments
        </span>
      </div>
    </div>
  );
}

// Folder component for grouping sources (simplified - no inline chunk expansion)
function SourceFolder({
  type,
  sources,
  selectedSource,
  onSelectSource,
}: {
  type: string;
  sources: SourceInfo[];
  selectedSource: string | null;
  onSelectSource: (source: SourceInfo) => void;
}) {
  const [isOpen, setIsOpen] = useState(true);
  const config = sourceTypeConfig[type] || { icon: "📁", label: type, color: "bg-gray-100 text-gray-800" };

  return (
    <div className="mb-4">
      {/* Folder header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-t-lg font-medium text-gray-700"
      >
        <span>{isOpen ? "📂" : "📁"}</span>
        <span>{config.label}s</span>
        <span className="text-sm text-gray-500">({sources.length})</span>
      </button>

      {/* Folder contents */}
      {isOpen && (
        <div className="bg-white border border-t-0 border-gray-200 rounded-b-lg">
          {sources.map((source) => (
            <SourceTreeNode
              key={source.id}
              source={source}
              onSelect={() => onSelectSource(source)}
              isSelected={selectedSource === source.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// RAG Explanation Modal
function RAGExplanationModal({ onClose, chunkCount }: { onClose: () => void; chunkCount: number }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-xl font-bold text-gray-900">How the Chatbot Processes Content</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
          </div>

          {/* Visual Pipeline */}
          <div className="space-y-3 mb-6">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <span className="text-2xl">📄</span>
              <div>
                <div className="font-medium">Original Document</div>
                <div className="text-sm text-gray-500">Podcast transcript or PDF</div>
              </div>
            </div>
            <div className="text-center text-gray-400">↓</div>
            <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
              <span className="text-2xl">✂️</span>
              <div>
                <div className="font-medium">Chunking</div>
                <div className="text-sm text-gray-500">Podcasts: ~256 tokens (~1-2 min) • PDFs: ~768 tokens</div>
              </div>
            </div>
            <div className="text-center text-gray-400">↓</div>
            <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
              <span className="text-2xl">🔢</span>
              <div>
                <div className="font-medium">Embedding</div>
                <div className="text-sm text-gray-500">Each chunk → 1,536-dimension vector</div>
              </div>
            </div>
            <div className="text-center text-gray-400">↓</div>
            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
              <span className="text-2xl">💾</span>
              <div>
                <div className="font-medium">Vector Database</div>
                <div className="text-sm text-gray-500">ChromaDB enables semantic similarity search</div>
              </div>
            </div>
            <div className="text-center text-gray-400">↓</div>
            <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
              <span className="text-2xl">🔍</span>
              <div>
                <div className="font-medium">Your Query</div>
                <div className="text-sm text-gray-500">Finds chunks most similar to your question</div>
              </div>
            </div>
            <div className="text-center text-gray-400">↓</div>
            <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
              <span className="text-2xl">🤖</span>
              <div>
                <div className="font-medium">AI Response</div>
                <div className="text-sm text-gray-500">Generated using retrieved chunks as context</div>
              </div>
            </div>
          </div>

          {/* Explanation text */}
          <div className="text-sm text-gray-600 space-y-3 border-t pt-4">
            <p>
              When you ask the chatbot a question, it converts your query into a mathematical
              embedding and compares it against all pre-indexed content segments. The most
              relevant segments are retrieved and used as context for generating an accurate,
              grounded response.
            </p>
            <p>
              The numbered references in chat responses link directly to these specific segments,
              allowing you to verify the source material.
            </p>
            <p className="font-medium text-gray-700">
              This document has {chunkCount} segments.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Constants for pagination
const CHARS_PER_PAGE = 8000; // ~2000 words per page
const SEGMENTS_PER_PAGE = 10; // Number of segments to show per page

// Source detail panel with whole document / chunked toggle
function SourceDetailPanel({
  source,
  chunks,
  isLoading,
  onClose,
  shootId,
  hasTranscript,
}: {
  source: SourceInfo;
  chunks: SourceChunk[];
  isLoading: boolean;
  onClose: () => void;
  shootId?: string;
  hasTranscript?: boolean;
}) {
  const config = sourceTypeConfig[source.source_type] || { icon: "📁", label: "Content", color: "bg-gray-100 text-gray-800" };
  const videoId = source.youtube_url ? getYouTubeVideoId(source.youtube_url) : null;
  const [currentTime, setCurrentTime] = useState<number | undefined>(undefined);
  const [viewMode, setViewMode] = useState<"whole" | "chunked">("whole");
  const [fullTextData, setFullTextData] = useState<SourceFullTextResponse | null>(null);
  const [isLoadingFullText, setIsLoadingFullText] = useState(false);
  const [showRAGModal, setShowRAGModal] = useState(false);
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [segmentPage, setSegmentPage] = useState(0);

  // Build full PDF URL
  const pdfUrl = source.source_type === "pdf" && source.url
    ? `http://100.51.125.89:8000${source.url}`
    : null;

  // Build embed URL with current timestamp
  const embedUrl = videoId ? buildYouTubeEmbedUrl(videoId, currentTime) : null;

  // Calculate pagination for full text
  const totalPages = fullTextData ? Math.ceil(fullTextData.full_text.length / CHARS_PER_PAGE) : 0;
  const currentPageText = fullTextData
    ? fullTextData.full_text.slice(currentPage * CHARS_PER_PAGE, (currentPage + 1) * CHARS_PER_PAGE)
    : "";

  // Calculate pagination for segments
  const totalSegmentPages = Math.ceil(chunks.length / SEGMENTS_PER_PAGE);
  const currentSegments = chunks.slice(
    segmentPage * SEGMENTS_PER_PAGE,
    (segmentPage + 1) * SEGMENTS_PER_PAGE
  );
  const segmentOffset = segmentPage * SEGMENTS_PER_PAGE;

  // Reset full text data and pages when source changes
  useEffect(() => {
    setFullTextData(null);
    setCurrentPage(0);
    setSegmentPage(0);
  }, [source.id]);

  // Load full text when switching to whole view or on mount
  useEffect(() => {
    if (viewMode === "whole" && !fullTextData && !isLoadingFullText) {
      loadFullText();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, source.id, fullTextData]);

  const loadFullText = async () => {
    setIsLoadingFullText(true);
    try {
      const data = await chatApi.getSourceFullText(source.id);
      setFullTextData(data);
    } catch (error) {
      console.error("Error loading full text:", error);
    } finally {
      setIsLoadingFullText(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.color}`}>
                {config.icon} {config.label}
              </span>
              <span className="text-xs text-gray-400">
                {chunks.length} segments
              </span>
            </div>
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {source.title || "Untitled"}
            </h2>
            {source.doctors && (
              <p className="text-sm text-gray-600 mt-1">{source.doctors}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {/* Action buttons row */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          {source.youtube_url && (
            <a
              href={source.youtube_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
            >
              ▶ Watch
            </a>
          )}
          {source.source_type === "pdf" && pdfUrl && (
            <button
              onClick={() => setShowPDFViewer(true)}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
            >
              📄 View PDF
            </button>
          )}
          {source.source_type === "audio" && shootId && hasTranscript && (
            <a
              href={analyticsApi.getShootTranscriptDownloadUrl(shootId)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700"
              onClick={(e) => {
                // Add auth token to the download request
                const token = Cookies.get("access_token");
                if (token) {
                  e.preventDefault();
                  // Fetch with auth and trigger download
                  fetch(analyticsApi.getShootTranscriptDownloadUrl(shootId), {
                    headers: { Authorization: `Bearer ${token}` },
                  })
                    .then((res) => res.blob())
                    .then((blob) => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `${source.title || "transcript"}.txt`;
                      document.body.appendChild(a);
                      a.click();
                      window.URL.revokeObjectURL(url);
                      a.remove();
                    });
                }
              }}
            >
              Download
            </a>
          )}

          {/* View mode toggle */}
          <div className="flex items-center gap-1 ml-auto">
            <span className="text-xs text-gray-500 mr-1">View:</span>
            <button
              onClick={() => setViewMode("whole")}
              className={`px-2 py-1 text-xs font-medium rounded-l border ${
                viewMode === "whole"
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Whole
            </button>
            <button
              onClick={() => setViewMode("chunked")}
              className={`px-2 py-1 text-xs font-medium rounded-r border-t border-b border-r ${
                viewMode === "chunked"
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Segments
            </button>
          </div>

          {/* RAG info button */}
          <button
            onClick={() => setShowRAGModal(true)}
            className="px-2 py-1 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
            title="How RAG works"
          >
            ℹ️ How it works
          </button>
        </div>
      </div>

      {/* Embedded video player for podcasts */}
      {embedUrl && (
        <div className="border-b border-gray-200">
          <div className="relative w-full" style={{ paddingTop: "56.25%" }}>
            <iframe
              key={embedUrl}
              src={embedUrl}
              className="absolute top-0 left-0 w-full h-full"
              title={source.title || "Video"}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </div>
      )}

      {/* Content area - switches between whole and chunked view */}
      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === "whole" ? (
          /* Whole document view with pagination */
          <div>
            {isLoadingFullText || isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
              </div>
            ) : fullTextData ? (
              <div>
                {/* Pagination controls - top */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                    <span className="text-sm text-gray-500">
                      Page {currentPage + 1} of {totalPages}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                        disabled={currentPage === 0}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                        disabled={currentPage >= totalPages - 1}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}

                {/* Text content */}
                <div className="prose prose-sm max-w-none">
                  <p className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                    {currentPage > 0 && <span className="text-gray-400">...</span>}
                    {currentPageText}
                    {currentPage < totalPages - 1 && <span className="text-gray-400">...</span>}
                  </p>
                </div>

                {/* Pagination controls - bottom */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
                    <span className="text-sm text-gray-500">
                      Page {currentPage + 1} of {totalPages}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                        disabled={currentPage === 0}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                        disabled={currentPage >= totalPages - 1}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                Failed to load document text
              </div>
            )}
          </div>
        ) : (
          /* Chunked/Segments view with pagination */
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              {isLoading ? "Loading..." : `${chunks.length} Indexed Segments`}
              {videoId && <span className="text-gray-400 font-normal"> — Click timestamp to jump</span>}
            </h3>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
              </div>
            ) : (
              <div>
                {/* Pagination controls - top */}
                {totalSegmentPages > 1 && (
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                    <span className="text-sm text-gray-500">
                      Showing {segmentOffset + 1}-{Math.min(segmentOffset + SEGMENTS_PER_PAGE, chunks.length)} of {chunks.length}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSegmentPage(Math.max(0, segmentPage - 1))}
                        disabled={segmentPage === 0}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setSegmentPage(Math.min(totalSegmentPages - 1, segmentPage + 1))}
                        disabled={segmentPage >= totalSegmentPages - 1}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {currentSegments.map((chunk, idx) => {
                    const globalIdx = segmentOffset + idx;
                    return (
                      <div
                        key={chunk.id}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex items-center justify-between mb-2">
                          {source.source_type === "audio" && videoId && chunk.start_time !== undefined ? (
                            <button
                              onClick={() => setCurrentTime(chunk.start_time)}
                              className="text-xs font-mono text-blue-600 hover:text-blue-800 hover:underline"
                              title="Jump to this timestamp"
                            >
                              ▶ {formatTimestamp(chunk.start_time)}
                              {chunk.end_time !== undefined && ` - ${formatTimestamp(chunk.end_time)}`}
                            </button>
                          ) : (
                            <span className="text-xs font-mono text-gray-500">
                              {source.source_type === "pdf" && chunk.page_num !== undefined
                                ? `Page ${chunk.page_num}`
                                : chunk.start_time !== undefined
                                  ? formatTimestamp(chunk.start_time)
                                  : `#${globalIdx + 1}`}
                              {chunk.end_time !== undefined && ` - ${formatTimestamp(chunk.end_time)}`}
                            </span>
                          )}
                          <span className="text-xs text-gray-400">
                            Segment {globalIdx + 1}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {chunk.text}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* Pagination controls - bottom */}
                {totalSegmentPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
                    <span className="text-sm text-gray-500">
                      Showing {segmentOffset + 1}-{Math.min(segmentOffset + SEGMENTS_PER_PAGE, chunks.length)} of {chunks.length}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSegmentPage(Math.max(0, segmentPage - 1))}
                        disabled={segmentPage === 0}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setSegmentPage(Math.min(totalSegmentPages - 1, segmentPage + 1))}
                        disabled={segmentPage >= totalSegmentPages - 1}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* RAG Explanation Modal */}
      {showRAGModal && (
        <RAGExplanationModal
          onClose={() => setShowRAGModal(false)}
          chunkCount={chunks.length}
        />
      )}

      {/* PDF Viewer Modal */}
      {showPDFViewer && pdfUrl && (
        <PDFViewer
          url={pdfUrl}
          title={source.title || "PDF Document"}
          onClose={() => setShowPDFViewer(false)}
        />
      )}
    </div>
  );
}

// Shoot info for transcript mapping
interface ShootTranscriptInfo {
  id: string;
  name: string;
  doctors: string[];
  hasTranscript: boolean;
}

// Extract last name from a doctor name (handles "Dr. First Last", "Dr. Last", etc.)
function extractLastName(name: string): string {
  const normalized = name.toLowerCase().replace(/\s+/g, " ").trim();
  // Remove common prefixes
  const withoutPrefix = normalized.replace(/^(dr\.?|doctor)\s+/i, "");
  // Get the last word as the last name
  const parts = withoutPrefix.split(" ").filter(Boolean);
  return parts[parts.length - 1] || withoutPrefix;
}

// Check if two names match (handles partial names, spelling variations)
function doctorNamesMatch(name1: string, name2: string): boolean {
  const last1 = extractLastName(name1);
  const last2 = extractLastName(name2);

  // Exact match
  if (last1 === last2) return true;

  // Allow 1 character difference for typos (Erica vs Erika)
  if (Math.abs(last1.length - last2.length) <= 1) {
    let diffs = 0;
    const maxLen = Math.max(last1.length, last2.length);
    for (let i = 0; i < maxLen; i++) {
      if ((last1[i] || "") !== (last2[i] || "")) diffs++;
      if (diffs > 1) return false;
    }
    return true;
  }

  return false;
}

// Check if two doctor arrays match (order-independent, uses last name matching)
function doctorArraysMatch(arr1: string[], arr2: string[]): boolean {
  if (arr1.length !== arr2.length) return false;

  // For each doctor in arr1, find a matching doctor in arr2
  const used = new Set<number>();
  for (const doc1 of arr1) {
    let found = false;
    for (let i = 0; i < arr2.length; i++) {
      if (!used.has(i) && doctorNamesMatch(doc1, arr2[i])) {
        used.add(i);
        found = true;
        break;
      }
    }
    if (!found) return false;
  }
  return true;
}

// Helper to find the matching shoot for a source by doctors
function getShootForSource(
  source: SourceInfo,
  shoots: ShootTranscriptInfo[]
): ShootTranscriptInfo | undefined {
  if (!source.doctors) return undefined;

  // Parse source doctors from comma-separated string to array
  const sourceDoctors = source.doctors.split(",").map((d) => d.trim()).filter(Boolean);
  if (sourceDoctors.length === 0) return undefined;

  // Find matching shoot using fuzzy doctor matching
  for (const shoot of shoots) {
    if (doctorArraysMatch(sourceDoctors, shoot.doctors)) {
      return shoot;
    }
  }

  return undefined;
}

export default function ContentLibraryPage() {
  const [mode, setMode] = useState<"library" | "chatbot">("library");
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Source selection state
  const [selectedSource, setSelectedSource] = useState<SourceInfo | null>(null);
  const [sourceChunks, setSourceChunks] = useState<Record<string, SourceChunk[]>>({});
  const [loadingChunks, setLoadingChunks] = useState<Set<string>>(new Set());

  // Shoot data for transcript downloads (array for fuzzy matching)
  const [shootsList, setShootsList] = useState<ShootTranscriptInfo[]>([]);

  // Load sources and shoots on mount
  useEffect(() => {
    loadSources();
    loadShoots();
  }, []);

  const loadSources = async () => {
    try {
      setIsLoadingSources(true);
      const response = await chatApi.listSources();
      setSources(response.sources);
    } catch (error) {
      console.error("Error loading sources:", error);
    } finally {
      setIsLoadingSources(false);
    }
  };

  const loadShoots = async () => {
    try {
      const shoots = await analyticsApi.getShoots();

      // Check all shoots for transcripts in parallel
      const transcriptChecks = await Promise.allSettled(
        shoots.map(async (shoot) => {
          try {
            await analyticsApi.getShootTranscript(shoot.id);
            return { id: shoot.id, hasTranscript: true };
          } catch {
            return { id: shoot.id, hasTranscript: false };
          }
        })
      );

      const transcriptMap = new Map<string, boolean>();
      transcriptChecks.forEach((result) => {
        if (result.status === "fulfilled") {
          transcriptMap.set(result.value.id, result.value.hasTranscript);
        }
      });

      // Build array of shoot info for fuzzy matching
      const shootInfoList: ShootTranscriptInfo[] = shoots.map((shoot) => ({
        id: shoot.id,
        name: shoot.name,
        doctors: shoot.doctors || [],
        hasTranscript: transcriptMap.get(shoot.id) || false,
      }));

      setShootsList(shootInfoList);
    } catch (error) {
      console.error("Error loading shoots:", error);
    }
  };

  const loadSourceChunks = async (sourceId: string) => {
    if (sourceChunks[sourceId]) return; // Already loaded

    setLoadingChunks((prev) => new Set(prev).add(sourceId));
    try {
      const response = await chatApi.getSourceChunks(sourceId);
      setSourceChunks((prev) => ({ ...prev, [sourceId]: response.chunks }));
    } catch (error) {
      console.error("Error loading chunks:", error);
    } finally {
      setLoadingChunks((prev) => {
        const next = new Set(prev);
        next.delete(sourceId);
        return next;
      });
    }
  };


  const handleSelectSource = (source: SourceInfo) => {
    setSelectedSource(source);
    loadSourceChunks(source.id);
  };

  // Filter sources by search query
  const filteredSources = sources.filter((source) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      (source.title?.toLowerCase().includes(query)) ||
      (source.doctors?.toLowerCase().includes(query))
    );
  });

  // Group sources by type
  const podcastSources = filteredSources.filter((s) => s.source_type === "audio");
  const pdfSources = filteredSources.filter((s) => s.source_type === "pdf");

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Content Library</h1>
          {!isLoadingSources && (
            <span className="text-sm text-gray-500">
              {sources.length} sources • {sources.reduce((sum, s) => sum + s.chunk_count, 0)} indexed segments
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setMode("library")}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              mode === "library"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Library
          </button>
          <button
            onClick={() => setMode("chatbot")}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              mode === "chatbot"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Chatbot
          </button>
        </div>
      </div>

      {mode === "chatbot" ? (
        /* Chatbot iframe */
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden" style={{ minHeight: "600px" }}>
          <iframe
            src={CHATBOT_URL}
            className="w-full h-full border-0"
            style={{ minHeight: "600px" }}
            title="CHM Medical Chatbot"
            allow="microphone"
          />
        </div>
      ) : (
        /* Content Library */
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Left panel: Tree view */}
          <div className="w-1/2 flex flex-col bg-white rounded-lg shadow overflow-hidden">
            {/* Search bar */}
            <div className="p-3 border-b border-gray-200">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sources..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Tree content */}
            <div className="flex-1 overflow-y-auto p-3">
              {isLoadingSources ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
                </div>
              ) : filteredSources.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {searchQuery ? "No sources match your search" : "No sources found"}
                </div>
              ) : (
                <>
                  {podcastSources.length > 0 && (
                    <SourceFolder
                      type="audio"
                      sources={podcastSources}
                      selectedSource={selectedSource?.id || null}
                      onSelectSource={handleSelectSource}
                    />
                  )}
                  {pdfSources.length > 0 && (
                    <SourceFolder
                      type="pdf"
                      sources={pdfSources}
                      selectedSource={selectedSource?.id || null}
                      onSelectSource={handleSelectSource}
                    />
                  )}
                </>
              )}
            </div>
          </div>

          {/* Right panel: Detail view */}
          <div className="w-1/2">
            {selectedSource ? (
              <SourceDetailPanel
                source={selectedSource}
                chunks={sourceChunks[selectedSource.id] || []}
                isLoading={loadingChunks.has(selectedSource.id)}
                onClose={() => setSelectedSource(null)}
                shootId={getShootForSource(selectedSource, shootsList)?.id}
                hasTranscript={getShootForSource(selectedSource, shootsList)?.hasTranscript}
              />
            ) : (
              <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                <div className="text-center text-gray-500">
                  <div className="text-4xl mb-2">📚</div>
                  <p className="font-medium">Select a source to view details</p>
                  <p className="text-sm mt-1">
                    Click on a podcast or research paper to see its indexed segments
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
