import { apiGet, apiPatch, apiPost } from './client';
import { MonitoringConfig, MonitoringConfigUpdate, UptimeCheck, MonitoringModelConfig } from '../types/monitoring';

export const getConfig = async (): Promise<MonitoringConfig> => {
  return apiGet<MonitoringConfig>('/monitoring/config');
};

export const updateConfig = async (data: MonitoringConfigUpdate): Promise<MonitoringConfig> => {
  return apiPatch<MonitoringConfig>('/monitoring/config', data);
};

export const triggerRun = async (): Promise<{ message: string; run_id: string }> => {
  return apiPost<{ message: string; run_id: string }>('/monitoring/run');
};

export const getUptimeHistory = async (params?: {
  limit?: number;
  status?: string;
  model_id?: string;
}): Promise<UptimeCheck[]> => {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.status && params.status !== 'all') queryParams.append('status', params.status);
  if (params?.model_id) queryParams.append('model_id', params.model_id);
  
  const queryString = queryParams.toString();
  const path = `/monitoring/uptime${queryString ? `?${queryString}` : ''}`;
  
  return apiGet<UptimeCheck[]>(path);
};

export const getMonitoredModels = async (): Promise<MonitoringModelConfig[]> => {
  return apiGet<MonitoringModelConfig[]>('/monitoring/models');
};

export const updateMonitoredModels = async (modelIds: string[]): Promise<MonitoringModelConfig[]> => {
  return apiPost<MonitoringModelConfig[]>('/monitoring/models', { model_ids: modelIds });
};
