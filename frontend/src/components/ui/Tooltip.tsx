import React, { useState, useRef, useEffect, useCallback } from "react";

type TooltipPosition = "top" | "bottom" | "left" | "right";

interface TooltipProps {
  content: React.ReactNode;
  position?: TooltipPosition;
  delay?: number;
  maxWidth?: string;
  children: React.ReactElement;
  className?: string;
}

const POSITION_CLASSES: Record<
  TooltipPosition,
  { tooltip: string; arrow: string }
> = {
  top: {
    tooltip:
      "bottom-full left-1/2 -translate-x-1/2 mb-2.5",
    arrow:
      "top-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-[6px] border-l-[6px] border-r-[6px] border-t-slate-800",
  },
  bottom: {
    tooltip:
      "top-full left-1/2 -translate-x-1/2 mt-2.5",
    arrow:
      "bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-[6px] border-l-[6px] border-r-[6px] border-b-slate-800",
  },
  left: {
    tooltip:
      "right-full top-1/2 -translate-y-1/2 mr-2.5",
    arrow:
      "left-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-[6px] border-t-[6px] border-b-[6px] border-l-slate-800",
  },
  right: {
    tooltip:
      "left-full top-1/2 -translate-y-1/2 ml-2.5",
    arrow:
      "right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-[6px] border-t-[6px] border-b-[6px] border-r-slate-800",
  },
};

export function Tooltip({
  content,
  position = "top",
  delay = 150,
  maxWidth = "max-w-xs",
  children,
  className = "",
}: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [rendered, setRendered] = useState(false);
  const showTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const clearTimers = useCallback(() => {
    if (showTimer.current) clearTimeout(showTimer.current);
    if (hideTimer.current) clearTimeout(hideTimer.current);
  }, []);

  const show = useCallback(() => {
    clearTimers();
    setRendered(true);
    showTimer.current = setTimeout(() => setVisible(true), delay);
  }, [clearTimers, delay]);

  const hide = useCallback(() => {
    clearTimers();
    setVisible(false);
    hideTimer.current = setTimeout(() => setRendered(false), 200);
  }, [clearTimers]);

  // Clean up on unmount
  useEffect(() => () => clearTimers(), [clearTimers]);

  // Close on Escape key
  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") hide();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [visible, hide]);

  const pos = POSITION_CLASSES[position];

  // Clone child to attach interaction handlers without losing existing ones
  const child = React.cloneElement(children, {
    onMouseEnter: (e: React.MouseEvent) => {
      show();
      children.props.onMouseEnter?.(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      hide();
      children.props.onMouseLeave?.(e);
    },
    onFocus: (e: React.FocusEvent) => {
      show();
      children.props.onFocus?.(e);
    },
    onBlur: (e: React.FocusEvent) => {
      hide();
      children.props.onBlur?.(e);
    },
    "aria-describedby": rendered ? "tooltip-popup" : undefined,
  });

  return (
    <span className={`relative inline-flex items-center ${className}`}>
      {child}

      {rendered && (
        <span
          ref={tooltipRef}
          id="tooltip-popup"
          role="tooltip"
          className={[
            "pointer-events-none absolute z-50 transition-all duration-200",
            pos.tooltip,
            visible
              ? "opacity-100 translate-y-0 scale-100"
              : "opacity-0 scale-95",
          ].join(" ")}
        >
          {/* Bubble */}
          <span
            className={[
              "block rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium",
              "leading-snug text-white shadow-xl ring-1 ring-white/10",
              maxWidth,
              "whitespace-normal break-words text-center",
            ].join(" ")}
          >
            {content}
          </span>

          {/* Arrow */}
          <span
            aria-hidden="true"
            className={`absolute h-0 w-0 border-solid ${pos.arrow}`}
          />
        </span>
      )}
    </span>
  );
}

export default Tooltip;