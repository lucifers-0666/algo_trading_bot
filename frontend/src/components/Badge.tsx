import React from "react";

export type BadgeVariant = "good" | "bad" | "warning" | "neutral" | "info";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = "neutral", size = "sm" }) => {
  return (
    <span className={`badge-pill badge-${variant} badge-${size}`}>
      {children}
    </span>
  );
};

