import { apiGet, apiPost, apiPatch, apiDelete } from './client';
import { Provider, ProviderCreate, ProviderUpdate, ProviderTestResult } from '../types/provider';

export async function listProviders(): Promise<Provider[]> {
  return apiGet<Provider[]>('/providers');
}

export async function createProvider(data: ProviderCreate): Promise<Provider> {
  return apiPost<Provider>('/providers', data);
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
