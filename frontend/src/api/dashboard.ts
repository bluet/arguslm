import { apiGet } from './client';
import { UptimeCheck } from '../types/monitoring';
import { BenchmarkRun } from '../types/benchmark';
import { Alert, DashboardStats, PerformanceMetric, LatencyMetric, RecentActivityItem, DashboardData, FailureEvent } from '../types/dashboard';

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

export async function getUptimeChecks(enabledOnly: boolean = true): Promise<UptimeCheck[]> {
  const response = await apiGet<UptimeListResponse>(`/monitoring/uptime?enabled_only=${enabledOnly}`);
  return response.items;
}

export async function getUptimeHistory(days: number = 1): Promise<UptimeCheck[]> {
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
  return fetchAllUptimePages(since);
}

export async function getUptimeHistoryByMinutes(minutes: number): Promise<UptimeCheck[]> {
  const since = new Date(Date.now() - minutes * 60 * 1000).toISOString();
  return fetchAllUptimePages(since);
}

const PAGE_SIZE = 5000;

async function fetchAllUptimePages(since: string): Promise<UptimeCheck[]> {
  const first = await apiGet<UptimeListResponse>(
    `/monitoring/uptime?limit=${PAGE_SIZE}&since=${since}`
  );
  if (first.total <= first.items.length) return first.items;

  const allItems = [...first.items];
  const remaining = first.total - first.items.length;
  const pages = Math.ceil(remaining / PAGE_SIZE);

  const pagePromises = Array.from({ length: pages }, (_, i) =>
    apiGet<UptimeListResponse>(
      `/monitoring/uptime?limit=${PAGE_SIZE}&offset=${(i + 1) * PAGE_SIZE}&since=${since}`
    )
  );
  const results = await Promise.all(pagePromises);
  for (const page of results) {
    allItems.push(...page.items);
  }
  return allItems;
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
 * Processes uptime checks into time-series data for charting.
 * Groups checks by minute and model to create multi-line chart data.
 */
function processUptimeHistory(checks: UptimeCheck[], metric: 'latency_ms' | 'ttft_ms' | 'tps' = 'latency_ms'): PerformanceMetric[] {
  const groupedByTime = new Map<string, Record<string, number>>();
  
  checks.forEach(check => {
    const value = check[metric];
    if (value === null || value === undefined) return;
    
    // Round to nearest minute to align points
    const date = new Date(check.created_at);
    date.setSeconds(0, 0);
    const timeKey = date.toISOString();
    
    if (!groupedByTime.has(timeKey)) {
      groupedByTime.set(timeKey, {});
    }
    
    groupedByTime.get(timeKey)![check.model_name] = value;
  });
  
  return Array.from(groupedByTime.entries())
    .map(([time, models]) => ({
      time,
      ...models
    }))
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

function formatDisplayName(name: string, providerType?: string | null): string {
  if (providerType) {
    return `${providerType}\n${name}`;
  }
  const parts = name.split('/');
  if (parts.length >= 2) {
    const provider = parts.slice(0, -1).join('/');
    const model = parts[parts.length - 1];
    return `${provider}\n${model}`;
  }
  return name;
}

export function processLatencyComparison(uptimeChecks: UptimeCheck[]): LatencyMetric[] {
  return uptimeChecks
    .filter(c => c.latency_ms !== null)
    .map(c => ({
      model_name: c.model_name,
      display_name: formatDisplayName(c.model_name, c.provider_type),
      latency: c.latency_ms!,
      ttft: c.ttft_ms ?? 0,
      tps: c.tps ?? 0,
      tps_scaled: (c.tps ?? 0) * 10
    }))
    .sort((a, b) => {
      const provA = a.display_name.split('\n')[0];
      const provB = b.display_name.split('\n')[0];
      if (provA !== provB) return provA.localeCompare(provB);
      return a.model_name.localeCompare(b.model_name);
    });
}

function processAvailabilityHistory(checks: UptimeCheck[], bucketMinutes: number = 5): PerformanceMetric[] {
  const bucketMs = bucketMinutes * 60 * 1000;
  const buckets = new Map<number, Map<string, { up: number; total: number }>>();
  const allModelNames = new Set<string>();

  checks.forEach(check => {
    allModelNames.add(check.model_name);
    const time = new Date(check.created_at).getTime();
    const bucketTime = Math.floor(time / bucketMs) * bucketMs;

    if (!buckets.has(bucketTime)) {
      buckets.set(bucketTime, new Map());
    }

    const modelStats = buckets.get(bucketTime)!;
    if (!modelStats.has(check.model_name)) {
      modelStats.set(check.model_name, { up: 0, total: 0 });
    }

    const stats = modelStats.get(check.model_name)!;
    stats.total += 1;
    if (check.status === 'up') {
      stats.up += 1;
    }
  });

  return Array.from(buckets.entries())
    .map(([bucketTime, modelStats]) => {
      const result: PerformanceMetric = { time: new Date(bucketTime).toISOString() };
      allModelNames.forEach(modelName => {
        const stats = modelStats.get(modelName);
        result[modelName] = stats ? Math.round((stats.up / stats.total) * 100) : null;
      });
      return result;
    })
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

function extractFailureEvents(checks: UptimeCheck[]): FailureEvent[] {
  return checks
    .filter(c => c.status !== 'up')
    .map(c => ({
      time: c.created_at,
      model_name: c.model_name,
      status: c.status,
      error: c.error ?? undefined
    }))
    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
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

export async function getDashboardData(timeRange: '5m' | '1h' | '24h' | '7d' | '30d' = '1h'): Promise<DashboardData> {
  const minutes = timeRange === '5m' ? 5 : timeRange === '1h' ? 60 : timeRange === '24h' ? 1440 : timeRange === '7d' ? 10080 : 43200;
  const bucketMinutes = timeRange === '5m' ? 1 : timeRange === '1h' ? 5 : timeRange === '24h' ? 30 : timeRange === '7d' ? 180 : 720;
  
  const [rawUptimeChecks, benchmarks, rawUptimeHistory, alerts, modelCount] = await Promise.all([
    getUptimeChecks(),
    getLatestBenchmarks(10),
    getUptimeHistoryByMinutes(minutes),
    getAlerts(true),
    getModelCount()
  ]);

  // Defense-in-depth: discard any data points outside the requested time window
  const cutoff = Date.now() - minutes * 60 * 1000;
  const uptimeHistory = rawUptimeHistory.filter(
    check => new Date(check.created_at).getTime() >= cutoff
  );

  const uptimeChecks = aggregateByModel(rawUptimeChecks);

  const stats = calculateStats(uptimeChecks, alerts, modelCount);
  const performanceHistory = processUptimeHistory(uptimeHistory, 'latency_ms');
  const ttftHistory = processUptimeHistory(uptimeHistory, 'ttft_ms');
  const tpsHistory = processUptimeHistory(uptimeHistory, 'tps');
  const availabilityHistory = processAvailabilityHistory(uptimeHistory, bucketMinutes);
  const failureEvents = extractFailureEvents(uptimeHistory);
  const latencyComparison = processLatencyComparison(uptimeChecks);
  const recentActivity = generateRecentActivity(benchmarks, alerts, uptimeChecks);

  return {
    stats,
    uptimeChecks,
    performanceHistory,
    ttftHistory,
    tpsHistory,
    availabilityHistory,
    failureEvents,
    latencyComparison,
    recentActivity
  };
}
