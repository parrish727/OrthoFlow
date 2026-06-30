'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';

interface AnnualOrthoStartsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; label: string };
  icon?: React.ReactNode;
  tooltip?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function AnnualOrthoStartsCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  tooltip,
  className = '',
  size = 'md',
}: AnnualOrthoStartsCardProps) {
  const [showTooltip, setShowTooltip] = React.useState(false);

  const sizeClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const valueSizeClasses = {
    sm: 'text-2xl',
    md: 'text-3xl',
    lg: 'text-4xl',
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <TrendingUp className="w-4 h-4" />;
    if (trend.value < 0) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) return 'text-emerald-400';
    if (trend.value < 0) return 'text-red-400';
    return 'text-zinc-400';
  };

  return (
    <div className={`relative bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 rounded-2xl ${sizeClasses[size]} ${className}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon && <span className="text-blue-400">{icon}</span>}
          <span className="text-sm font-medium text-zinc-400">{title}</span>
        </div>
        {tooltip && (
          <div className="relative">
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
              aria-label={`Info: ${title}`}
            >
              <Info className="w-4 h-4" />
            </button>
            {showTooltip && (
              <div className="absolute right-0 top-6 z-50 w-64 p-3 bg-zinc-800 border border-zinc-700 rounded-xl shadow-xl text-xs text-zinc-300 leading-relaxed">
                {tooltip}
              </div>
            )}
          </div>
        )}
      </div>

      <div className={`${valueSizeClasses[size]} font-bold text-white tracking-tight`}>
        {value}
      </div>

      <div className="flex items-center justify-between mt-2">
        {subtitle && (
          <span className="text-xs text-zinc-500">{subtitle}</span>
        )}
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium ${getTrendColor()}`}>
            {getTrendIcon()}
            <span>{trend.value > 0 ? '+' : ''}{trend.value}%</span>
            <span className="text-zinc-500 ml-1">{trend.label}</span>
          </div>
        )}
      </div>
    </div>
  );
}
