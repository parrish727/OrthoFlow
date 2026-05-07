import React from "react";
import { LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Tooltip } from "../ui/Tooltip";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
  iconColor?: string;
  iconBg?: string;
  tooltip?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  iconColor = "text-blue-600",
  iconBg = "bg-blue-50",
  tooltip,
}: StatCardProps) {
  const TrendIcon =
    trend === undefined
      ? Minus
      : trend.value > 0
      ? TrendingUp
      : trend.value < 0
      ? TrendingDown
      : Minus;

  const trendColor =
    trend === undefined
      ? "text-slate-400"
      : trend.value > 0
      ? "text-emerald-600"
      : trend.value < 0
      ? "text-rose-500"
      : "text-slate-400";

  const card = (
    <div className="group relative flex flex-col gap-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/80 transition-all duration-200 hover:shadow-md hover:ring-slate-300">
      {/* Header row */}
      <div className="flex items-start justify-between">
        <div className={`rounded-xl p-2.5 ${iconBg}`}>
          <Icon className={`h-5 w-5 ${iconColor}`} strokeWidth={2} />
        </div>

        {trend !== undefined && (
          <span
            className={`flex items-center gap-1 text-xs font-semibold ${trendColor}`}
          >
            <TrendIcon className="h-3.5 w-3.5" />
            {Math.abs(trend.value)}%
          </span>
        )}
      </div>

      {/* Value + title */}
      <div className="space-y-0.5">
        <p className="text-2xl font-bold tracking-tight text-slate-900">
          {value}
        </p>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        {subtitle && (
          <p className="text-xs text-slate-400">{subtitle}</p>
        )}
      </div>

      {/* Trend label */}
      {trend && (
        <p className={`text-xs font-medium ${trendColor}`}>{trend.label}</p>
      )}

      {/* Tooltip hint icon */}
      {tooltip && (
        <span
          aria-hidden="true"
          className="absolute right-3 top-3 flex h-4 w-4 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-400 opacity-0 transition-opacity duration-150 group-hover:opacity-100"
        >
          ?
        </span>
      )}
    </div>
  );

  if (!tooltip) return card;

  return (
    <Tooltip content={tooltip} position="top" maxWidth="max-w-[220px]">
      {card}
    </Tooltip>
  );
}

export default StatCard;