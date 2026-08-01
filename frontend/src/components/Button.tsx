import { forwardRef, type ButtonHTMLAttributes } from "react";

import { Spinner } from "@/components/Spinner";

type Variant = "primary" | "secondary" | "outline" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-primary-500 text-white hover:bg-primary-600 disabled:bg-primary-300",
  secondary: "bg-secondary-400 text-primary-900 hover:bg-secondary-500 disabled:bg-secondary-200",
  outline: "border-2 border-primary-500 text-primary-600 hover:bg-primary-50 disabled:opacity-50",
  danger: "bg-danger-500 text-white hover:bg-danger-600 disabled:bg-danger-500/50",
  ghost: "text-primary-600 hover:bg-primary-50 disabled:opacity-50",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "text-sm px-3 py-1.5",
  md: "text-base px-4 py-2.5",
  lg: "text-lg px-6 py-3",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", isLoading = false, disabled, className = "", children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors
        focus-visible:outline-3 focus-visible:outline-primary-500 disabled:cursor-not-allowed
        ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      aria-busy={isLoading}
      {...rest}
    >
      {isLoading && <Spinner size="sm" />}
      {children}
    </button>
  );
});
