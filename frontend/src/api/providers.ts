import { apiGet, apiPost, apiPatch, apiDelete } from './client';
import { Provider, ProviderCreate, ProviderUpdate, ProviderTestResult } from '../types/provider';

interface ProviderListResponse {
  providers: BackendProviderResponse[];
  total: number;
}

export async function listProviders(): Promise<Provider[]> {
  const response = await apiGet<ProviderListResponse>('/providers');
  return response.providers.map(transformFromBackendFormat);
}

interface BackendProviderCreate {
  provider_type: string;
  display_name: string;
  credentials: Record<string, string>;
}

interface BackendProviderResponse {
  id: string;
  provider_type: string;
  display_name: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

function transformToBackendFormat(data: ProviderCreate): BackendProviderCreate {
  const credentials: Record<string, string> = {};
  if (data.api_key) credentials.api_key = data.api_key;
  if (data.base_url) credentials.base_url = data.base_url;
  if (data.organization_id) credentials.organization_id = data.organization_id;
  if (data.project_id) credentials.project_id = data.project_id;
  if (data.region) credentials.region = data.region;
  
  return {
    provider_type: data.provider_type,
    display_name: data.name,
    credentials,
  };
}

function transformFromBackendFormat(response: BackendProviderResponse): Provider {
  return {
    id: response.id,
    name: response.display_name,
    provider_type: response.provider_type as Provider['provider_type'],
    is_enabled: response.enabled,
    created_at: response.created_at,
    updated_at: response.updated_at,
  };
}

export async function createProvider(data: ProviderCreate): Promise<Provider> {
  const backendData = transformToBackendFormat(data);
  const response = await apiPost<BackendProviderResponse>('/providers', backendData);
  return transformFromBackendFormat(response);
}

export async function updateProvider(id: string, data: ProviderUpdate): Promise<Provider> {
  return apiPatch<Provider>(`/providers/${id}`, data);
}

export async function deleteProvider(id: string): Promise<void> {
  return apiDelete(`/providers/${id}`);
}

export async function testProvider(id: string): Promise<ProviderTestResult> {
  return apiPost<ProviderTestResult>(`/providers/${id}/test`);
}

export async function refreshModels(id: string): Promise<void> {
  return apiPost<void>(`/providers/${id}/refresh-models`);
}
