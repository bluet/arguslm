export type ProviderType = 
  | 'openai'
  | 'anthropic'
  | 'google_vertex'
  | 'google_ai_studio'
  | 'aws_bedrock'
  | 'azure_openai'
  | 'ollama'
  | 'lm_studio'
  | 'openrouter'
  | 'together_ai'
  | 'groq'
  | 'mistral'
  | 'custom_openai_compatible';

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
