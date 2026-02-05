export type ProviderType = string;

export interface ProviderSpec {
  id: string;
  label: string;
  tested: boolean;
  requires_api_key: boolean;
  requires_base_url: boolean;
  requires_region: boolean;
  show_org_fields: boolean;
  default_base_url: string | null;
  api_key_label: string | null;
  base_url_label: string | null;
  region_options: [string, string][];
}

export interface Provider {
  id: string;
  name: string;
  provider_type: ProviderType;
  base_url?: string;
  api_key?: string; // Will be masked from backend usually
  organization_id?: string;
  project_id?: string;
  region?: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  name: string;
  provider_type: ProviderType;
  base_url?: string;
  api_key?: string;
  organization_id?: string;
  project_id?: string;
  region?: string;
  is_enabled?: boolean;
}

export interface ProviderUpdate {
  name?: string;
  base_url?: string;
  api_key?: string;
  organization_id?: string;
  project_id?: string;
  region?: string;
  is_enabled?: boolean;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
  latency_ms?: number;
}
