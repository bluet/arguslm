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

interface ModelCountResponse {
  items: unknown[];
  total: number;
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

export async function getModelCount(): Promise<number> {
  const response = await apiGet<ModelCountResponse>('/models?limit=1');
  return response.total;
}

// Aggregation Helpers

function aggregateByModel(checks: UptimeCheck[]): UptimeCheck[] {
  const latestByModel = new Map<string, UptimeCheck>();
  for (const check of checks) {
    const existing = latestByModel.get(check.model_name);
    if (!existing || new Date(check.created_at) > new Date(existing.created_at)) {
      latestByModel.set(check.model_name, check);
    }
  }
  return Array.from(latestByModel.values());
}

export function calculateStats(uptimeChecks: UptimeCheck[], alerts: Alert[], totalModels: number): DashboardStats {
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

/**
 * Fetches real performance data from completed benchmark runs.
 * Retrieves TTFT and TPS from individual benchmark results, averages multiple results per run,
 * and returns sorted time-series data for charting.
 */
async function fetchBenchmarkPerformanceData(runs: BenchmarkRun[]): Promise<PerformanceMetric[]> {
  // Only process completed runs that have results
  const completedRuns = runs.filter(r => r.status === 'completed' && r.result_count > 0);
  
  // Limit to last 10 runs for performance
  const recentRuns = completedRuns.slice(0, 10);
  
  const results = await Promise.all(
    recentRuns.map(async (run) => {
      try {
        const response = await apiGet<{results: Array<{ttft_ms: number, tps: number}>}>(`/benchmarks/${run.id}/results`);
        if (response.results.length > 0) {
          // Average if multiple results per run
          const avgTtft = response.results.reduce((sum, r) => sum + r.ttft_ms, 0) / response.results.length;
          const avgTps = response.results.reduce((sum, r) => sum + r.tps, 0) / response.results.length;
          return {
            time: run.completed_at || run.started_at,
            ttft: avgTtft,
            tps: avgTps
          };
        }
        return null;
      } catch {
        // Skip failed fetches gracefully
        return null;
      }
    })
  );
  
  return results
    .filter((r): r is PerformanceMetric => r !== null)
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
  
  const [rawUptimeChecks, benchmarks, history, alerts, modelCount] = await Promise.all([
    getUptimeChecks(),
    getLatestBenchmarks(10),
    getBenchmarkHistory(days),
    getAlerts(true),
    getModelCount()
  ]);

  const uptimeChecks = aggregateByModel(rawUptimeChecks);

  const stats = calculateStats(uptimeChecks, alerts, modelCount);
  const performanceHistory = await fetchBenchmarkPerformanceData(history);
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
