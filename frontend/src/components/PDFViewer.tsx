"use client";

/**
 * PDF Viewer Modal Component
 * Displays PDF in an iframe with download option
 * Adapted from CHM Chatbot's PDF viewer
 */

import { useState } from "react";

interface PDFViewerProps {
  url: string;
  title: string;
  onClose: () => void;
}

export function PDFViewer({ url, title, onClose }: PDFViewerProps) {
  const [loading, setLoading] = useState(true);

  // Extract filename from URL for download (remove query params and hash)
  const filename =
    (url.split("/").pop() || "document.pdf").split("#")[0].split("?")[0];

  // Build download URL with ?download=true parameter
  const getDownloadUrl = () => {
    const baseUrl = url.split("#")[0]; // Remove hash (page number)
    const separator = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${separator}download=true`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      {/* Modal container */}
      <div className="relative w-[95vw] h-[90vh] max-w-6xl bg-white rounded-lg shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <h3 className="text-sm font-semibold text-gray-800 truncate max-w-[60%]">
            {title}
          </h3>
          <div className="flex items-center gap-2">
            {/* Download button */}
            <a
              href={getDownloadUrl()}
              download={filename}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              ⬇️ Download
            </a>
            {/* Open in new tab */}
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              ↗️ Open
            </a>
            {/* Close button */}
            <button
              onClick={onClose}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-md transition-colors text-lg"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* PDF iframe */}
        <div className="flex-1 relative bg-gray-100">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-gray-600">Loading PDF...</span>
              </div>
            </div>
          )}
          <iframe
            src={`${url}#toolbar=1&navpanes=1&scrollbar=1`}
            className="w-full h-full border-0"
            onLoad={() => setLoading(false)}
            title={title}
          />
        </div>
      </div>

      {/* Click outside to close */}
      <div className="absolute inset-0 -z-10" onClick={onClose} />
    </div>
  );
}
