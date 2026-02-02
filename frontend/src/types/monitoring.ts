export interface MonitoringConfig {
  id: string;
  interval_minutes: number;
  prompt_pack: string;
  enabled: boolean;
  last_run_at: string | null;
  created_at: string;
}

export interface UptimeCheck {
  id: string;
  model_id: string;
  model_name: string;
  status: 'up' | 'down' | 'degraded';
  latency_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface MonitoringModelConfig {
  model_id: string;
  provider: string;
  model_name: string;
  enabled: boolean;
}

export interface MonitoringConfigUpdate {
  interval_minutes?: number;
  prompt_pack?: string;
  enabled?: boolean;
  models?: string[]; // List of enabled model IDs
}
