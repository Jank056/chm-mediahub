"use client";

interface ThumbnailProps {
  src?: string | null;
  alt: string;
  aspectRatio?: "16:9" | "9:16" | "1:1";
  size?: "sm" | "md" | "lg";
  fallbackIcon?: React.ReactNode;
}

const aspectRatioStyles = {
  "16:9": "aspect-video",
  "9:16": "aspect-[9/16]",
  "1:1": "aspect-square",
};

const sizeStyles = {
  sm: "w-24",
  md: "w-40",
  lg: "w-64",
};

export function Thumbnail({
  src,
  alt,
  aspectRatio = "16:9",
  size = "md",
  fallbackIcon,
}: ThumbnailProps) {
  const aspectClass = aspectRatioStyles[aspectRatio];
  const sizeClass = sizeStyles[size];

  if (!src) {
    return (
      <div
        className={`${sizeClass} ${aspectClass} bg-gray-200 rounded-lg flex items-center justify-center`}
      >
        {fallbackIcon || (
          <svg
            className="w-8 h-8 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`${sizeClass} ${aspectClass} object-cover rounded-lg`}
    />
  );
}
