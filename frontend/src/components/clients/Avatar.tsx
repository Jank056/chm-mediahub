"use client";

interface AvatarProps {
  name: string;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeStyles: Record<string, { container: string; text: string }> = {
  sm: { container: "w-8 h-8", text: "text-xs" },
  md: { container: "w-10 h-10", text: "text-sm" },
  lg: { container: "w-12 h-12", text: "text-base" },
  xl: { container: "w-16 h-16", text: "text-xl" },
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getColorFromName(name: string): string {
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-purple-500",
    "bg-orange-500",
    "bg-pink-500",
    "bg-teal-500",
    "bg-indigo-500",
    "bg-rose-500",
  ];
  const index = name.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[index % colors.length];
}

export function Avatar({ name, imageUrl, size = "md" }: AvatarProps) {
  const styles = sizeStyles[size];
  const initials = getInitials(name);
  const bgColor = getColorFromName(name);

  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={name}
        className={`${styles.container} rounded-full object-cover`}
      />
    );
  }

  return (
    <div
      className={`${styles.container} ${bgColor} rounded-full flex items-center justify-center text-white font-semibold ${styles.text}`}
    >
      {initials}
    </div>
  );
}
