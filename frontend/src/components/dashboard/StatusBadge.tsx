import React from "react";
import { CheckCircle2, Clock, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import { Tooltip } from "../ui/Tooltip";
import type { InvoiceStatus } from "../../types/invoice";

interface StatusBadgeProps {
  status: InvoiceStatus;
  showTooltip?: boolean;
}

interface StatusConfig {
  label: string;
  icon: React.ElementType;
  badge: string;
  dot: string;
  tooltip: string;
}

const STATUS_CONFIG: Record<InvoiceStatus, StatusConfig> = {
  approved: {
    label: "Approved",
    icon: CheckCircle2,
    badge:
      "bg-emerald-50 text-emerald-700 ring-emerald-200",
    dot: "bg-emerald-500",
    tooltip:
      "This invoice has been reviewed and approved. Payment can be processed.",
  },
  pending: {
    label: "Pending",
    icon: Clock,
    badge: "bg-amber-50 text-amber-700 ring-amber-200",
    dot: "bg-amber-400",
    tooltip:
      "Awaiting review. This invoice has been received but not yet acted on.",
  },
  "needs-review": {
    label: "Needs Review",
    icon: AlertTriangle,
    badge: "bg-rose-50 text-rose-700 ring-rose-200",
    dot: "bg-rose-500",
    tooltip:
      "AI flagged one or more issues. A human reviewer must inspect before approval.",
  },
  processing: {
    label: "Processing",
    icon: Loader2,
    badge: "bg-blue-50 text-blue-700 ring-blue-200",
    dot: "bg-blue-400",
    tooltip:
      "The AI pipeline is actively extracting and validating data for this invoice.",
  },
  rejected: {
    label: "Rejected",
    icon: XCircle,
    badge: "bg-slate-100 text-slate-500 ring-slate-200",
    dot: "bg-slate-400",
    tooltip:
      "This invoice was rejected and will not be processed for payment.",
  },
};

export function StatusBadge({ status, showTooltip = true }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  const badge = (
    <span
      className={`inline-flex cursor-default items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset transition-all duration-150 ${config.badge}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${config.dot}`} />
      <Icon
        className={`h-3 w-3 shrink-0 ${
          status === "processing" ? "animate-spin" : ""
        }`}
        strokeWidth={2.5}
      />
      {config.label}
    </span>
  );

  if (!showTooltip) return badge;

  return (
    <Tooltip
      content={config.tooltip}
      position="top"
      maxWidth="max-w-[200px]"
    >
      {badge}
    </Tooltip>
  );
}

export default StatusBadge;