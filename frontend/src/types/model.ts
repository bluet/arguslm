export interface Model {
  id: string;
  provider_account_id: string;
  provider_name: string | null;
  model_id: string;
  custom_name: string | null;
  source: 'discovered' | 'manual';
  enabled_for_monitoring: boolean;
  enabled_for_benchmark: boolean;
  model_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ModelFilters {
  provider_id?: string;
  enabled_for_monitoring?: boolean;
  enabled_for_benchmark?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CreateModelData {
  provider_account_id: string;
  model_id: string;
  custom_name?: string;
  enabled_for_monitoring?: boolean;
  enabled_for_benchmark?: boolean;
  model_metadata?: Record<string, unknown>;
}

export interface UpdateModelData {
  custom_name?: string | null;
  enabled_for_monitoring?: boolean;
  enabled_for_benchmark?: boolean;
  model_metadata?: Record<string, unknown>;
}
