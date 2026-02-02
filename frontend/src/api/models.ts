import { Model, ModelFilters, CreateModelData, UpdateModelData } from '../types/model';

const API_BASE_URL = 'http://localhost:8000/api/v1';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export const modelsApi = {
  listModels: async (params: ModelFilters = {}): Promise<Model[]> => {
    const searchParams = new URLSearchParams();
    if (params.provider_id) searchParams.append('provider_id', params.provider_id);
    if (params.enabled_for_monitoring !== undefined) searchParams.append('enabled_for_monitoring', String(params.enabled_for_monitoring));
    if (params.enabled_for_benchmark !== undefined) searchParams.append('enabled_for_benchmark', String(params.enabled_for_benchmark));
    if (params.search) searchParams.append('search', params.search);
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset) searchParams.append('offset', String(params.offset));

    const response = await fetch(`${API_BASE_URL}/models?${searchParams.toString()}`);
    return handleResponse<Model[]>(response);
  },

  getModel: async (id: string): Promise<Model> => {
    const response = await fetch(`${API_BASE_URL}/models/${id}`);
    return handleResponse<Model>(response);
  },

  createModel: async (data: CreateModelData): Promise<Model> => {
    const response = await fetch(`${API_BASE_URL}/models`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return handleResponse<Model>(response);
  },

  updateModel: async (id: string, data: UpdateModelData): Promise<Model> => {
    const response = await fetch(`${API_BASE_URL}/models/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return handleResponse<Model>(response);
  },
};
