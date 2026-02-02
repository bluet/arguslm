import { apiGet, apiPost } from './client';
import { 
  BenchmarkRun, 
  BenchmarkResult, 
  BenchmarkFilters, 
  CreateBenchmarkData 
} from '../types/benchmark';

export const benchmarksApi = {
  listBenchmarks: async (params: BenchmarkFilters = {}): Promise<BenchmarkRun[]> => {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.append('status', params.status);
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset) searchParams.append('offset', String(params.offset));

    const queryString = searchParams.toString();
    const path = queryString ? `/benchmarks?${queryString}` : '/benchmarks';
    
    return apiGet<BenchmarkRun[]>(path);
  },

  getBenchmark: async (id: string): Promise<BenchmarkRun> => {
    return apiGet<BenchmarkRun>(`/benchmarks/${id}`);
  },

  getBenchmarkResults: async (id: string): Promise<BenchmarkResult[]> => {
    return apiGet<BenchmarkResult[]>(`/benchmarks/${id}/results`);
  },

  createBenchmark: async (data: CreateBenchmarkData): Promise<BenchmarkRun> => {
    return apiPost<BenchmarkRun>('/benchmarks', data);
  }
};
