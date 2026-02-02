/**
 * Export API functions for downloading benchmark and uptime data
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Export benchmark results as JSON or CSV
 */
export async function exportBenchmark(runId: string, format: 'json' | 'csv'): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/benchmarks/${runId}/export?format=${format}`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
    const filename = filenameMatch ? filenameMatch[1] : `benchmark_${runId}.${format}`;
    
    // Download file
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Export failed:', error);
    throw error;
  }
}

/**
 * Export uptime history as JSON or CSV
 */
export async function exportUptimeHistory(
  format: 'json' | 'csv',
  filters?: {
    modelId?: string;
    startDate?: string;
    endDate?: string;
  }
): Promise<void> {
  const params = new URLSearchParams({ format });
  
  if (filters?.modelId) {
    params.append('model_id', filters.modelId);
  }
  if (filters?.startDate) {
    params.append('start_date', filters.startDate);
  }
  if (filters?.endDate) {
    params.append('end_date', filters.endDate);
  }
  
  const url = `${API_BASE_URL}/api/v1/monitoring/uptime/export?${params.toString()}`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
    const filename = filenameMatch ? filenameMatch[1] : `uptime_history.${format}`;
    
    // Download file
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Export failed:', error);
    throw error;
  }
}
