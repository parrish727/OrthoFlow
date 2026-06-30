'use client';

import React, { useState } from 'react';
import { MonthlyStartData } from '@/types/orthoStarts';

interface OrthoStartsChartProps {
  data: MonthlyStartData[];
  height?: number;
}

export default function OrthoStartsChart({ data, height = 280 }: OrthoStartsChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'starts' | 'consultations' | 'conversion'>('starts');

  const maxStarts = Math.max(...data.map((d) => d.starts), 1);
  const maxConsultations = Math.max(...data.map((d) => d.consultations), 1);
  const maxValue = viewMode === 'starts' ? maxStarts : viewMode === 'consultations' ? maxConsultations : 100;

  const getValue = (d: MonthlyStartData) => {
    switch (viewMode) {
      case 'starts': return d.starts;
      case 'consultations': return d.consultations;
      case 'conversion': return d.conversionRate;
    }
  };

  const getBarColor = (value: number, index: number) => {
    if (hoveredIndex === index) return 'bg-blue-400';
    if (viewMode === 'conversion') {
      if (value >= 75) return 'bg-emerald-500/70';
      if (value >= 60) return 'bg-amber-500/70';
      return 'bg-red-500/70';
    }
    return 'bg-blue-500/60';
  };

  return (
    <div className="bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white">Monthly Ortho Starts</h3>
          <p className="text-xs text-zinc-500 mt-1">Tracking new patient treatment initiations</p>
        </div>
        <div className="flex items-center gap-1 bg-zinc-800/60 rounded-xl p-1">
          {(['starts', 'consultations', 'conversion'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                viewMode === mode
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              {mode === 'conversion' ? 'Conv. Rate' : mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-end gap-2" style={{ height }}>
        {data.map((d, i) => {
          const value = getValue(d);
          const barHeight = (value / maxValue) * 100;

          return (
            <div
              key={d.month}
              className="flex-1 flex flex-col items-center gap-2 relative"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {hoveredIndex === i && (
                <div className="absolute -top-20 left-1/2 -translate-x-1/2 z-10 bg-zinc-800 border border-zinc-700 rounded-xl p-3 shadow-xl min-w-[140px]">
                  <p className="text-xs font-semibold text-white">{d.month}</p>
                  <div className="mt-1 space-y-0.5">
                    <p className="text-xs text-zinc-400">Starts: <span className="text-blue-400 font-medium">{d.starts}</span></p>
                    <p className="text-xs text-zinc-400">Consults: <span className="text-purple-400 font-medium">{d.consultations}</span></p>
                    <p className="text-xs text-zinc-400">Conv: <span className="text-emerald-400 font-medium">{d.conversionRate}%</span></p>
                  </div>
                </div>
              )}

              <div className="w-full flex items-end justify-center" style={{ height: height - 30 }}>
                <div
                  className={`w-full max-w-[32px] rounded-t-lg transition-all duration-300 ${getBarColor(value, i)}`}
                  style={{ height: `${Math.max(barHeight, 2)}%` }}
                />
              </div>

              <span className="text-[10px] text-zinc-500 font-medium">{d.month}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
