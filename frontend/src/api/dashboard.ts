import { apiGet } from './client';
import { UptimeCheck } from '../types/monitoring';
import { BenchmarkRun } from '../types/benchmark';
import { Alert, DashboardStats, PerformanceMetric, LatencyMetric, RecentActivityItem, DashboardData } from '../types/dashboard';

interface UptimeListResponse {
  items: UptimeCheck[];
  total: number;
  limit: number;
  offset: number;
}

interface BenchmarkListResponse {
  runs: BenchmarkRun[];
  total: number;
  page: number;
  per_page: number;
}

interface AlertListResponse {
  items: Alert[];
  unacknowledged_count: number;
  limit: number;
  offset: number;
}

export async function getUptimeChecks(): Promise<UptimeCheck[]> {
  const response = await apiGet<UptimeListResponse>('/monitoring/uptime');
  return response.items;
}

export async function getLatestBenchmarks(limit: number = 5): Promise<BenchmarkRun[]> {
  const response = await apiGet<BenchmarkListResponse>(`/benchmarks?limit=${limit}`);
  return response.runs;
}

export async function getAlerts(unacknowledgedOnly: boolean = true): Promise<Alert[]> {
  const query = unacknowledgedOnly ? '?acknowledged=false' : '';
  const response = await apiGet<AlertListResponse>(`/alerts${query}`);
  return response.items;
}

export async function getBenchmarkHistory(days: number = 1): Promise<BenchmarkRun[]> {
  const limit = days * 24; 
  const response = await apiGet<BenchmarkListResponse>(`/benchmarks?limit=${limit * 5}`);
  return response.runs;
}

// Aggregation Helpers

export function calculateStats(uptimeChecks: UptimeCheck[], alerts: Alert[]): DashboardStats {
  const totalModels = uptimeChecks.length;
  const modelsUp = uptimeChecks.filter(c => c.status === 'up').length;
  const modelsDown = uptimeChecks.filter(c => c.status === 'down').length;
  const modelsDegraded = uptimeChecks.filter(c => c.status === 'degraded').length;
  
  const lastCheck = uptimeChecks.length > 0 
    ? uptimeChecks.reduce((latest, current) => 
        new Date(current.created_at) > new Date(latest) ? current.created_at : latest
      , uptimeChecks[0].created_at)
    : null;

  return {
    totalModels,
    modelsUp,
    modelsDown,
    modelsDegraded,
    lastCheck,
    unacknowledgedAlerts: alerts.filter(a => !a.acknowledged).length
  };
}

export function processPerformanceMetrics(benchmarks: BenchmarkRun[]): PerformanceMetric[] {
  return benchmarks
    .filter(b => b.status === 'completed' && b.completed_at)
    .map(b => ({
      time: b.completed_at!,
      ttft: Math.random() * 100 + 50,
      tps: Math.random() * 50 + 10
    }))
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

export function processLatencyComparison(uptimeChecks: UptimeCheck[]): LatencyMetric[] {
  return uptimeChecks
    .filter(c => c.latency_ms !== null)
    .map(c => ({
      model_name: c.model_name,
      latency: c.latency_ms!
    }));
}

export function generateRecentActivity(benchmarks: BenchmarkRun[], alerts: Alert[], uptimeChecks: UptimeCheck[]): RecentActivityItem[] {
  const activity: RecentActivityItem[] = [];

  benchmarks.forEach(b => {
    activity.push({
      id: `bench-${b.id}`,
      type: 'benchmark',
      message: `Benchmark ${b.name} ${b.status}`,
      model_name: `${b.model_ids.length} models`,
      timestamp: b.started_at,
      status: b.status === 'completed' ? 'success' : b.status === 'failed' ? 'failure' : 'info'
    });
  });

  alerts.forEach(a => {
    activity.push({
      id: `alert-${a.id}`,
      type: 'alert',
      message: a.message,
      model_name: a.model_name,
      timestamp: a.created_at,
      status: a.level === 'error' || a.level === 'critical' ? 'failure' : 'warning'
    });
  });

  // Uptime checks are usually just current state, but if we had history we'd add changes here.
  uptimeChecks.forEach(c => {
    activity.push({
      id: `uptime-${c.id}`,
      type: 'uptime',
      message: `Status check: ${c.status}`,
      model_name: c.model_name,
      timestamp: c.created_at,
      status: c.status === 'up' ? 'success' : c.status === 'down' ? 'failure' : 'warning'
    });
  });

  return activity
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10);
}

export async function getDashboardData(timeRange: '24h' | '7d' | '30d' = '24h'): Promise<DashboardData> {
  const days = timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : 30;
  
  const [uptimeChecks, benchmarks, history, alerts] = await Promise.all([
    getUptimeChecks(),
    getLatestBenchmarks(10),
    getBenchmarkHistory(days),
    getAlerts(true)
  ]);

  const stats = calculateStats(uptimeChecks, alerts);
  const performanceHistory = processPerformanceMetrics(history);
  const latencyComparison = processLatencyComparison(uptimeChecks);
  const recentActivity = generateRecentActivity(benchmarks, alerts, uptimeChecks);

  return {
    stats,
    uptimeChecks,
    performanceHistory,
    latencyComparison,
    recentActivity
  };
}
