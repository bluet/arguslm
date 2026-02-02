import React, { useState, useEffect, useMemo } from 'react';
import { Settings, Clock, RefreshCw, Check, X, AlertTriangle, Play, Save, Search, Activity, Download } from 'lucide-react';
import { getConfig, updateConfig, triggerRun, getUptimeHistory } from '../api/monitoring';
import { modelsApi } from '../api/models';
import { exportUptimeHistory } from '../api/export';
import { MonitoringConfig, UptimeCheck } from '../types/monitoring';
import { Model } from '../types/model';

const MonitoringPage: React.FC = () => {
  // State
  const [config, setConfig] = useState<MonitoringConfig | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [uptimeHistory, setUptimeHistory] = useState<UptimeCheck[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [historyFilter, setHistoryFilter] = useState<'all' | 'up' | 'down'>('all');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [modelSearch, setModelSearch] = useState('');
  
  // Form state for config
  const [formConfig, setFormConfig] = useState<{
    enabled: boolean;
    interval_minutes: number;
    prompt_pack: string;
  }>({
    enabled: false,
    interval_minutes: 60,
    prompt_pack: 'synthetic_short'
  });

  // Fetch initial data
  const fetchData = async () => {
    try {
      const [configData, modelsData, historyData] = await Promise.all([
        getConfig(),
        modelsApi.listModels({ limit: 1000 }), // Fetch all models
        getUptimeHistory({ limit: 50 })
      ]);

      setConfig(configData);
      setFormConfig({
        enabled: configData.enabled,
        interval_minutes: configData.interval_minutes,
        prompt_pack: configData.prompt_pack
      });
      setModels(modelsData);
      setUptimeHistory(historyData);
      
      // Set initial selected provider
      if (modelsData.length > 0) {
        const providers = Array.from(new Set(modelsData.map(m => m.provider_account_id)));
        if (providers.length > 0) {
          setSelectedProvider(providers[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Auto-refresh history
  useEffect(() => {
    if (!config?.enabled) return;

    const interval = setInterval(async () => {
      try {
        const history = await getUptimeHistory({ limit: 50 });
        setUptimeHistory(history);
      } catch (error) {
        console.error('Failed to refresh history:', error);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [config?.enabled]);

  // Handlers
  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      const updated = await updateConfig(formConfig);
      setConfig(updated);
      // Show success message or toast here if available
    } catch (error) {
      console.error('Failed to update config:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    try {
      await triggerRun();
      // Refresh history after a short delay to show the new run
      setTimeout(async () => {
        const history = await getUptimeHistory({ limit: 50 });
        setUptimeHistory(history);
        const newConfig = await getConfig();
        setConfig(newConfig);
      }, 2000);
    } catch (error) {
      console.error('Failed to trigger run:', error);
    } finally {
      setRunning(false);
    }
  };

  const handleToggleModel = async (modelId: string, enabled: boolean) => {
    // Optimistic update
    setModels(prev => prev.map(m => 
      m.id === modelId ? { ...m, enabled_for_monitoring: enabled } : m
    ));

    try {
      await modelsApi.updateModel(modelId, { enabled_for_monitoring: enabled });
    } catch (error) {
      console.error('Failed to update model:', error);
      // Revert on failure
      setModels(prev => prev.map(m => 
        m.id === modelId ? { ...m, enabled_for_monitoring: !enabled } : m
      ));
    }
  };

  const handleEnableAll = async (providerId: string, enable: boolean) => {
    const modelsToUpdate = models.filter(m => m.provider_account_id === providerId);
    
    // Optimistic update
    setModels(prev => prev.map(m => 
      m.provider_account_id === providerId ? { ...m, enabled_for_monitoring: enable } : m
    ));

    try {
      await Promise.all(modelsToUpdate.map(m => 
        modelsApi.updateModel(m.id, { enabled_for_monitoring: enable })
      ));
    } catch (error) {
      console.error('Failed to bulk update models:', error);
      // Revert is complex here, simpler to just refetch
      const modelsData = await modelsApi.listModels({ limit: 1000 });
      setModels(modelsData);
    }
  };

  // Derived state
  const providers = useMemo(() => {
    return Array.from(new Set(models.map(m => m.provider_account_id))).sort();
  }, [models]);

  const filteredModels = useMemo(() => {
    return models.filter(m => 
      m.provider_account_id === selectedProvider &&
      (m.custom_name || m.model_id).toLowerCase().includes(modelSearch.toLowerCase())
    );
  }, [models, selectedProvider, modelSearch]);

  const filteredHistory = useMemo(() => {
    if (historyFilter === 'all') return uptimeHistory;
    return uptimeHistory.filter(check => check.status === historyFilter);
  }, [uptimeHistory, historyFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-500">
        <RefreshCw className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-600" />
          Monitoring Configuration
        </h1>
        {config?.last_run_at && (
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Last run: {new Date(config.last_run_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Section 1: Global Configuration */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="w-5 h-5 text-gray-500" />
          <h2 className="text-xl font-semibold text-gray-800">Global Settings</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-end">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Monitoring Status</label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setFormConfig(prev => ({ ...prev, enabled: !prev.enabled }))}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  formConfig.enabled ? 'bg-green-500' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    formConfig.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className={`text-sm font-medium ${formConfig.enabled ? 'text-green-600' : 'text-gray-500'}`}>
                {formConfig.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Check Interval</label>
            <select
              value={formConfig.interval_minutes}
              onChange={(e) => setFormConfig(prev => ({ ...prev, interval_minutes: Number(e.target.value) }))}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
            >
              <option value={1}>Every 1 minute</option>
              <option value={5}>Every 5 minutes</option>
              <option value={15}>Every 15 minutes</option>
              <option value={30}>Every 30 minutes</option>
              <option value={60}>Every 60 minutes</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Prompt Pack</label>
            <select
              value={formConfig.prompt_pack}
              onChange={(e) => setFormConfig(prev => ({ ...prev, prompt_pack: e.target.value }))}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
            >
              <option value="shakespeare">Shakespeare</option>
              <option value="synthetic_short">Synthetic Short</option>
              <option value="synthetic_medium">Synthetic Medium</option>
              <option value="synthetic_long">Synthetic Long</option>
            </select>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleSaveConfig}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Config
            </button>
            <button
              onClick={handleRunNow}
              disabled={running}
              className="flex-1 flex items-center justify-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run Now
            </button>
          </div>
        </div>
      </section>

      {/* Section 2: Model Selection */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Check className="w-5 h-5 text-gray-500" />
            <h2 className="text-xl font-semibold text-gray-800">Model Selection</h2>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search models..."
              value={modelSearch}
              onChange={(e) => setModelSearch(e.target.value)}
              className="pl-9 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {providers.length > 0 ? (
          <>
            <div className="border-b border-gray-200 mb-6">
              <nav className="-mb-px flex space-x-8 overflow-x-auto">
                {providers.map((provider) => (
                  <button
                    key={provider}
                    onClick={() => setSelectedProvider(provider)}
                    className={`
                      whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors
                      ${selectedProvider === provider
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                    `}
                  >
                    {provider}
                  </button>
                ))}
              </nav>
            </div>

            <div className="space-y-4">
              <div className="flex justify-end gap-2 mb-4">
                <button
                  onClick={() => handleEnableAll(selectedProvider, true)}
                  className="text-xs font-medium text-blue-600 hover:text-blue-800"
                >
                  Enable All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => handleEnableAll(selectedProvider, false)}
                  className="text-xs font-medium text-gray-500 hover:text-gray-700"
                >
                  Disable All
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredModels.map((model) => (
                  <div
                    key={model.id}
                    className={`
                      flex items-center justify-between p-4 rounded-lg border transition-all
                      ${model.enabled_for_monitoring
                        ? 'border-blue-200 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'}
                    `}
                  >
                    <div className="min-w-0 flex-1 mr-4">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {model.custom_name || model.model_id}
                      </p>
                      <p className="text-xs text-gray-500 truncate">{model.model_id}</p>
                    </div>
                    <button
                      onClick={() => handleToggleModel(model.id, !model.enabled_for_monitoring)}
                      className={`
                        relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                        ${model.enabled_for_monitoring ? 'bg-blue-600' : 'bg-gray-200'}
                      `}
                    >
                      <span
                        className={`
                          inline-block h-3 w-3 transform rounded-full bg-white transition-transform
                          ${model.enabled_for_monitoring ? 'translate-x-5' : 'translate-x-1'}
                        `}
                      />
                    </button>
                  </div>
                ))}
                {filteredModels.length === 0 && (
                  <div className="col-span-full text-center py-8 text-gray-500">
                    No models found matching your search.
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No models available. Add models in the Models configuration page.
          </div>
        )}
      </section>

      {/* Section 3: Recent Uptime History */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-500" />
            <h2 className="text-xl font-semibold text-gray-800">Recent Uptime History</h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
              {(['all', 'up', 'down'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setHistoryFilter(filter)}
                  className={`
                    px-3 py-1.5 text-sm font-medium rounded-md capitalize transition-all
                    ${historyFilter === filter
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'}
                  `}
                >
                  {filter}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => exportUptimeHistory('json').catch(err => console.error('Export failed:', err))}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                JSON
              </button>
              <button
                onClick={() => exportUptimeHistory('csv').catch(err => console.error('Export failed:', err))}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                CSV
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latency</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredHistory.map((check) => (
                <tr key={check.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(check.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {check.model_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`
                      inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                      ${check.status === 'up' ? 'bg-green-100 text-green-800' : 
                        check.status === 'down' ? 'bg-red-100 text-red-800' : 
                        'bg-yellow-100 text-yellow-800'}
                    `}>
                      {check.status === 'up' && <Check className="w-3 h-3 mr-1" />}
                      {check.status === 'down' && <X className="w-3 h-3 mr-1" />}
                      {check.status === 'degraded' && <AlertTriangle className="w-3 h-3 mr-1" />}
                      {check.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {check.latency_ms ? `${check.latency_ms}ms` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-red-600 max-w-xs truncate" title={check.error || ''}>
                    {check.error || '-'}
                  </td>
                </tr>
              ))}
              {filteredHistory.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No history records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default MonitoringPage;
