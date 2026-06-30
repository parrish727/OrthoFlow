import {
  AnnualOrthoStartsMetrics,
  MonthlyStartData,
  OrthoStartsInsight,
  OrthoStartsGoal,
  IndustryBenchmarks,
  OrthoStartsByType,
  PhaseBreakdown,
} from '@/types/orthoStarts';

// AAO 2025 Survey benchmarks (from the provided AAO survey data)
const AAO_2025_BENCHMARKS: IndustryBenchmarks = {
  aaoMedianStarts: 275,
  aaoTopQuartileStarts: 425,
  practicePercentile: 0,
  aaoMedianFee: 6200,
  aaoAverageGrowthRate: 4.2,
  nationalAverageConversion: 68,
};

export function calculateGrowthRate(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return Number((((current - previous) / previous) * 100).toFixed(1));
}

export function projectAnnualStarts(monthlyData: MonthlyStartData[]): number {
  if (monthlyData.length === 0) return 0;
  if (monthlyData.length >= 12) {
    return monthlyData.slice(-12).reduce((sum, m) => sum + m.starts, 0);
  }
  const weights = monthlyData.map((_, i) => 1 + (i * 0.1));
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const weightedAvg = monthlyData.reduce((sum, m, i) => sum + m.starts * weights[i], 0) / totalWeight;
  return Math.round(weightedAvg * 12);
}

export function calculatePercentile(practiceStarts: number, benchmarks: IndustryBenchmarks): number {
  const median = benchmarks.aaoMedianStarts;
  const topQuartile = benchmarks.aaoTopQuartileStarts;

  if (practiceStarts >= topQuartile * 1.5) return 95;
  if (practiceStarts >= topQuartile) return 75;
  if (practiceStarts >= median) return 50 + ((practiceStarts - median) / (topQuartile - median)) * 25;
  if (practiceStarts >= median * 0.5) return 25 + ((practiceStarts - median * 0.5) / (median * 0.5)) * 25;
  return Math.max(5, Math.round((practiceStarts / (median * 0.5)) * 25));
}

export function calculateSeasonalityIndex(monthlyData: MonthlyStartData[]): Record<string, number> {
  if (monthlyData.length < 12) return {};
  const avg = monthlyData.reduce((s, m) => s + m.starts, 0) / monthlyData.length;
  const index: Record<string, number> = {};
  monthlyData.forEach((m) => {
    index[m.month] = Number((m.starts / avg).toFixed(2));
  });
  return index;
}

export function generateInsights(metrics: AnnualOrthoStartsMetrics): OrthoStartsInsight[] {
  const insights: OrthoStartsInsight[] = [];
  const now = new Date().toISOString();

  // Growth analysis
  if (metrics.growthRate > 10) {
    insights.push({
      id: 'growth-exceptional',
      type: 'growth',
      severity: 'positive',
      title: 'Exceptional Practice Growth',
      description: `Your practice grew ${metrics.growthRate}% year-over-year, significantly outpacing the AAO national average of ${metrics.benchmarks.aaoAverageGrowthRate}%.`,
      recommendation: 'Consider expanding capacity—additional chairs, extended hours, or associate hiring—to sustain this growth trajectory without compromising patient experience.',
      impact: `At this rate, you could add ${Math.round(metrics.totalStarts * (metrics.growthRate / 100))} additional starts next year.`,
      dataPoints: { growthRate: metrics.growthRate, aaoAverage: metrics.benchmarks.aaoAverageGrowthRate },
      createdAt: now,
    });
  } else if (metrics.growthRate > 0) {
    insights.push({
      id: 'growth-positive',
      type: 'growth',
      severity: 'positive',
      title: 'Steady Practice Growth',
      description: `Your practice grew ${metrics.growthRate}% year-over-year, ${metrics.growthRate >= metrics.benchmarks.aaoAverageGrowthRate ? 'meeting or exceeding' : 'slightly below'} the AAO national average.`,
      recommendation: 'Focus on optimizing consultation conversion rates and patient referral programs to accelerate growth.',
      impact: 'Maintaining consistent growth builds long-term practice value.',
      dataPoints: { growthRate: metrics.growthRate },
      createdAt: now,
    });
  } else if (metrics.growthRate < -5) {
    insights.push({
      id: 'growth-decline',
      type: 'growth',
      severity: 'critical',
      title: 'Significant Decline in Ortho Starts',
      description: `Your annual starts decreased by ${Math.abs(metrics.growthRate)}%. This requires immediate attention.`,
      recommendation: 'Audit your patient funnel: marketing reach → consultations → conversions. Identify where drop-off is occurring. Consider community outreach programs and digital marketing investment.',
      impact: `At current trajectory, projected revenue loss of $${Math.round(Math.abs(metrics.growthRate / 100) * metrics.totalStarts * metrics.revenuePerStart).toLocaleString()}.`,
      dataPoints: { decline: metrics.growthRate, revenueAtRisk: Math.abs(metrics.growthRate / 100) * metrics.totalStarts * metrics.revenuePerStart },
      createdAt: now,
    });
  }

  // Conversion rate analysis
  if (metrics.conversionRate < 60) {
    insights.push({
      id: 'conversion-low',
      type: 'operational',
      severity: 'warning',
      title: 'Below-Average Consultation Conversion Rate',
      description: `Your conversion rate of ${metrics.conversionRate}% is below the national average of ${metrics.benchmarks.nationalAverageConversion}%.`,
      recommendation: 'Review your consultation process. Consider same-day start options, flexible payment plans, and treatment coordinator training. Each 5% improvement in conversion could yield additional starts.',
      impact: `Improving to ${metrics.benchmarks.nationalAverageConversion}% could generate ${Math.round((metrics.benchmarks.nationalAverageConversion - metrics.conversionRate) / 100 * (metrics.totalStarts / (metrics.conversionRate / 100)))} additional starts annually.`,
      dataPoints: { currentRate: metrics.conversionRate, targetRate: metrics.benchmarks.nationalAverageConversion },
      createdAt: now,
    });
  } else if (metrics.conversionRate >= 80) {
    insights.push({
      id: 'conversion-excellent',
      type: 'operational',
      severity: 'positive',
      title: 'Outstanding Conversion Rate',
      description: `Your ${metrics.conversionRate}% conversion rate is well above the ${metrics.benchmarks.nationalAverageConversion}% national average.`,
      recommendation: 'Your consultation process is a competitive advantage. Document and standardize it. Focus marketing budget on driving more consultations since your conversion engine is highly efficient.',
      impact: 'Every additional consultation has an 80%+ chance of becoming a start.',
      dataPoints: { rate: metrics.conversionRate },
      createdAt: now,
    });
  }

  // AAO benchmarking
  const percentile = metrics.benchmarks.practicePercentile;
  if (percentile >= 75) {
    insights.push({
      id: 'benchmark-top',
      type: 'benchmark',
      severity: 'positive',
      title: 'Top Quartile Practice (AAO Benchmark)',
      description: `With ${metrics.totalStarts} annual starts, your practice ranks in the ${percentile}th percentile nationally per AAO 2025 survey data.`,
      recommendation: 'You are operating at elite levels. Focus on profitability per case, patient experience scores, and retention for Phase I-to-Phase II conversions.',
      impact: 'Top-quartile practices typically command premium fees and attract higher-quality referrals.',
      dataPoints: { percentile, aaoTopQuartile: metrics.benchmarks.aaoTopQuartileStarts },
      createdAt: now,
    });
  } else if (percentile < 50) {
    insights.push({
      id: 'benchmark-below-median',
      type: 'benchmark',
      severity: 'warning',
      title: 'Below AAO Median for Annual Starts',
      description: `Your ${metrics.totalStarts} annual starts place you below the AAO median of ${metrics.benchmarks.aaoMedianStarts}.`,
      recommendation: 'Evaluate your market area demographics and competition. Consider expanding referral networks, adding early orthodontics (Phase I) programs per AAO guidelines recommending evaluation by age 7, and increasing digital marketing presence.',
      impact: `Reaching the median could increase annual revenue by $${Math.round((metrics.benchmarks.aaoMedianStarts - metrics.totalStarts) * metrics.revenuePerStart).toLocaleString()}.`,
      dataPoints: { gap: metrics.benchmarks.aaoMedianStarts - metrics.totalStarts },
      createdAt: now,
    });
  }

  // Phase I/II analysis
  const phaseIRatio = metrics.phaseBreakdown.phaseI.starts / Math.max(metrics.totalStarts, 1);
  if (phaseIRatio < 0.1) {
    insights.push({
      id: 'phase1-opportunity',
      type: 'growth',
      severity: 'neutral',
      title: 'Phase I Early Treatment Opportunity',
      description: `Phase I starts represent only ${(phaseIRatio * 100).toFixed(1)}% of your total starts. The AAO recommends orthodontic evaluation by age 7, creating a significant early treatment pipeline.`,
      recommendation: 'Partner with pediatric dentists for early referrals. Educate parents on Phase I benefits—interceptive treatment can simplify Phase II and improve outcomes. This also creates a built-in pipeline for future comprehensive cases.',
      impact: `Each Phase I patient has a ${metrics.phaseBreakdown.phaseI.conversionToPhaseII}% chance of converting to Phase II, creating predictable future revenue.`,
      dataPoints: { phaseIStarts: metrics.phaseBreakdown.phaseI.starts, conversionToPhaseII: metrics.phaseBreakdown.phaseI.conversionToPhaseII },
      createdAt: now,
    });
  }

  // Aligner vs traditional mix
  const alignerRatio = metrics.startsByType.aligner / Math.max(metrics.totalStarts, 1);
  if (alignerRatio < 0.2) {
    insights.push({
      id: 'aligner-growth',
      type: 'marketing',
      severity: 'neutral',
      title: 'Aligner Adoption Below Market Trend',
      description: `Clear aligners represent ${(alignerRatio * 100).toFixed(1)}% of your starts. Market trends show growing consumer demand for aligner therapy.`,
      recommendation: 'Consider expanding aligner offerings and marketing them to adult patients. Direct-to-consumer aligner companies have increased awareness—position your practice as the professional, supervised alternative.',
      impact: 'Aligner cases often attract adult demographics who may not have considered traditional braces.',
      dataPoints: { alignerPercentage: (alignerRatio * 100).toFixed(1) },
      createdAt: now,
    });
  }

  // Seasonality detection
  if (metrics.monthlyData.length >= 6) {
    const seasonality = calculateSeasonalityIndex(metrics.monthlyData);
    const entries = Object.entries(seasonality);
    if (entries.length > 0) {
      const peakMonth = entries.reduce((a, b) => (a[1] > b[1] ? a : b));
      const lowMonth = entries.reduce((a, b) => (a[1] < b[1] ? a : b));

      if (peakMonth[1] > 1.3 || lowMonth[1] < 0.7) {
        insights.push({
          id: 'seasonality-pattern',
          type: 'operational',
          severity: 'neutral',
          title: 'Seasonal Start Pattern Detected',
          description: `Peak starts occur in ${peakMonth[0]} (${Math.round(peakMonth[1] * 100)}% of average) with lowest in ${lowMonth[0]} (${Math.round(lowMonth[1] * 100)}% of average).`,
          recommendation: `Plan marketing campaigns and promotions 6-8 weeks before low months. Staff up during peak periods. Consider seasonal promotions in ${lowMonth[0]} to smooth demand.`,
          impact: 'Smoothing seasonality improves resource utilization and staff scheduling efficiency.',
          dataPoints: { peakMonth: peakMonth[0], peakIndex: peakMonth[1], lowMonth: lowMonth[0], lowIndex: lowMonth[1] },
          createdAt: now,
        });
      }
    }
  }

  // Revenue per start analysis
  if (metrics.revenuePerStart < metrics.benchmarks.aaoMedianFee * 0.85) {
    insights.push({
      id: 'fee-below-market',
      type: 'financial',
      severity: 'warning',
      title: 'Average Fee Below AAO Median',
      description: `Your average revenue per start ($${metrics.revenuePerStart.toLocaleString()}) is ${((1 - metrics.revenuePerStart / metrics.benchmarks.aaoMedianFee) * 100).toFixed(0)}% below the AAO median fee of $${metrics.benchmarks.aaoMedianFee.toLocaleString()}.`,
      recommendation: 'Evaluate your fee schedule against local market rates. Consider value-based pricing that reflects your expertise and technology investment. Gradual fee increases of 3-5% annually are standard practice.',
      impact: `Reaching the median fee could increase annual revenue by $${Math.round((metrics.benchmarks.aaoMedianFee - metrics.revenuePerStart) * metrics.totalStarts).toLocaleString()}.`,
      dataPoints: { currentFee: metrics.revenuePerStart, aaoMedian: metrics.benchmarks.aaoMedianFee },
      createdAt: now,
    });
  }

  return insights;
}

export function evaluateGoalStatus(goal: OrthoStartsGoal): OrthoStartsGoal['status'] {
  const now = new Date();
  const monthsElapsed = now.getMonth() + 1;
  const expectedProgress = monthsElapsed / 12;
  const actualProgress = goal.currentStarts / goal.targetStarts;
  const progressRatio = actualProgress / expectedProgress;

  if (actualProgress >= 1) return 'exceeded';
  if (progressRatio >= 0.9) return 'on-track';
  if (progressRatio >= 0.75) return 'at-risk';
  return 'behind';
}

export function generateSampleMetrics(): AnnualOrthoStartsMetrics {
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const seasonalFactors = [0.8, 0.75, 0.9, 0.95, 1.1, 1.2, 1.3, 1.15, 1.05, 0.95, 0.85, 0.7];
  const baseMonthly = 24;

  const monthlyData: MonthlyStartData[] = monthNames.map((month, i) => {
    const starts = Math.round(baseMonthly * seasonalFactors[i] + (Math.random() - 0.5) * 6);
    const consultations = Math.round(starts / 0.72 + (Math.random() - 0.5) * 4);
    return {
      month,
      starts,
      consultations,
      conversionRate: Number(((starts / consultations) * 100).toFixed(1)),
    };
  });

  const totalStarts = monthlyData.reduce((s, m) => s + m.starts, 0);
  const previousYearStarts = 258;
  const revenuePerStart = 5850;

  const benchmarks: IndustryBenchmarks = {
    ...AAO_2025_BENCHMARKS,
    practicePercentile: calculatePercentile(totalStarts, AAO_2025_BENCHMARKS),
  };

  const startsByType: OrthoStartsByType = {
    comprehensive: Math.round(totalStarts * 0.45),
    phaseI: Math.round(totalStarts * 0.12),
    phaseII: Math.round(totalStarts * 0.10),
    limitedTreatment: Math.round(totalStarts * 0.08),
    aligner: Math.round(totalStarts * 0.20),
    surgical: Math.round(totalStarts * 0.05),
  };

  const phaseBreakdown: PhaseBreakdown = {
    phaseI: {
      starts: startsByType.phaseI,
      averageAge: 7.8,
      averageDuration: 14,
      conversionToPhaseII: 72,
    },
    phaseII: {
      starts: startsByType.phaseII,
      fromPhaseI: Math.round(startsByType.phaseII * 0.65),
      newPatients: Math.round(startsByType.phaseII * 0.35),
      averageAge: 12.4,
    },
  };

  return {
    totalStarts,
    previousYearStarts,
    growthRate: calculateGrowthRate(totalStarts, previousYearStarts),
    averageMonthlyStarts: Number((totalStarts / 12).toFixed(1)),
    projectedAnnualStarts: projectAnnualStarts(monthlyData),
    conversionRate: Number((monthlyData.reduce((s, m) => s + m.conversionRate, 0) / monthlyData.length).toFixed(1)),
    revenuePerStart,
    projectedRevenue: totalStarts * revenuePerStart,
    monthlyData,
    startsByType,
    startsBySource: [
      { source: 'General Dentist Referrals', count: Math.round(totalStarts * 0.35), percentage: 35, trend: 'stable' },
      { source: 'Pediatric Dentist Referrals', count: Math.round(totalStarts * 0.22), percentage: 22, trend: 'up' },
      { source: 'Patient Referrals', count: Math.round(totalStarts * 0.18), percentage: 18, trend: 'up' },
      { source: 'Google / Organic Search', count: Math.round(totalStarts * 0.12), percentage: 12, trend: 'up' },
      { source: 'Social Media', count: Math.round(totalStarts * 0.08), percentage: 8, trend: 'up' },
      { source: 'Insurance Directory', count: Math.round(totalStarts * 0.03), percentage: 3, trend: 'down' },
      { source: 'Other', count: Math.round(totalStarts * 0.02), percentage: 2, trend: 'stable' },
    ],
    benchmarks,
    phaseBreakdown,
  };
}
