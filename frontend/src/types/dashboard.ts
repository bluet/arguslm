import { UptimeCheck } from './monitoring';

export interface Alert {
  id: string;
  model_id: string;
  model_name: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  acknowledged: boolean;
  created_at: string;
}

export interface DashboardStats {
  totalModels: number;
  modelsUp: number;
  modelsDown: number;
  modelsDegraded: number;
  lastCheck: string | null;
  unacknowledgedAlerts: number;
}

export interface PerformanceMetric {
  time: string;
  ttft: number;
  tps: number;
}

export interface LatencyMetric {
  model_name: string;
  latency: number;
}

export interface RecentActivityItem {
  id: string;
  type: 'benchmark' | 'alert' | 'uptime';
  message: string;
  model_name: string;
  timestamp: string;
  status?: 'success' | 'failure' | 'warning' | 'info';
}

export interface DashboardData {
  stats: DashboardStats;
  uptimeChecks: UptimeCheck[];
  performanceHistory: PerformanceMetric[];
  latencyComparison: LatencyMetric[];
  recentActivity: RecentActivityItem[];
}
