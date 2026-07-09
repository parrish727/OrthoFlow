export interface MonthlyStartData {
  month: string;
  starts: number;
  consultations: number;
  conversionRate: number;
}

export interface AnnualOrthoStartsMetrics {
  totalStarts: number;
  previousYearStarts: number;
  growthRate: number;
  averageMonthlyStarts: number;
  projectedAnnualStarts: number;
  conversionRate: number;
  revenuePerStart: number;
  projectedRevenue: number;
  monthlyData: MonthlyStartData[];
  startsByType: OrthoStartsByType;
  startsBySource: OrthoStartsBySource[];
  benchmarks: IndustryBenchmarks;
  phaseBreakdown: PhaseBreakdown;
}

export interface OrthoStartsByType {
  comprehensive: number;
  phaseI: number;
  phaseII: number;
  limitedTreatment: number;
  aligner: number;
  surgical: number;
}

export interface OrthoStartsBySource {
  source: string;
  count: number;
  percentage: number;
  trend: 'up' | 'down' | 'stable';
}

export interface IndustryBenchmarks {
  aaoMedianStarts: number;
  aaoTopQuartileStarts: number;
  practicePercentile: number;
  aaoMedianFee: number;
  aaoAverageGrowthRate: number;
  nationalAverageConversion: number;
}

export interface PhaseBreakdown {
  phaseI: {
    starts: number;
    averageAge: number;
    averageDuration: number;
    conversionToPhaseII: number;
  };
  phaseII: {
    starts: number;
    fromPhaseI: number;
    newPatients: number;
    averageAge: number;
  };
}

export interface OrthoStartsGoal {
  id: string;
  year: number;
  targetStarts: number;
  currentStarts: number;
  targetRevenue: number;
  targetConversionRate: number;
  strategies: string[];
  status: 'on-track' | 'at-risk' | 'behind' | 'exceeded';
}

export interface OrthoStartsInsight {
  id: string;
  type: 'growth' | 'financial' | 'marketing' | 'operational' | 'benchmark';
  severity: 'positive' | 'neutral' | 'warning' | 'critical';
  title: string;
  description: string;
  recommendation: string;
  impact: string;
  dataPoints: Record<string, number | string>;
  createdAt: string;
}
