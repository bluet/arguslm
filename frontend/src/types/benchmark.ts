export interface BenchmarkRun {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  model_ids: string[];
  prompt_pack: string;
  triggered_by: 'user' | 'scheduled';
  started_at: string;
  completed_at: string | null;
  result_count: number;
}

export interface BenchmarkResult {
  id: string;
  model_id: string;
  model_name: string;
  ttft_ms: number;
  tps: number;
  tps_excluding_ttft: number;
  total_latency_ms: number;
  output_tokens: number;
  error: string | null;
}

export interface BenchmarkStatistics {
  ttft: { p50: number; p95: number; p99: number };
  tps: { p50: number; p95: number; p99: number };
}

export interface BenchmarkFilters {
  status?: 'pending' | 'running' | 'completed' | 'failed';
  limit?: number;
  offset?: number;
}

export interface CreateBenchmarkData {
  model_ids: string[];
  prompt_pack: string;
  num_runs?: number;
  name?: string;
}
