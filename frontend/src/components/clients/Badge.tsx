"use client";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "platform";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  platform?: "youtube" | "linkedin" | "twitter" | "tiktok";
  size?: "sm" | "md";
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  error: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
  platform: "", // Handled separately
};

const platformStyles: Record<string, string> = {
  youtube: "bg-red-100 text-red-700",
  linkedin: "bg-blue-100 text-blue-700",
  twitter: "bg-gray-900 text-white",
  tiktok: "bg-gray-900 text-white",
};

const sizeStyles: Record<string, string> = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-2.5 py-1",
};

export function Badge({ children, variant = "default", platform, size = "sm" }: BadgeProps) {
  const style = variant === "platform" && platform
    ? platformStyles[platform] || variantStyles.default
    : variantStyles[variant];

  return (
    <span className={`inline-flex items-center rounded-full font-medium ${style} ${sizeStyles[size]}`}>
      {children}
    </span>
  );
}
