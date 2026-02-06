import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Play, Clock, Check, ChevronDown, ChevronUp, Activity, AlertCircle, Download, Search } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { benchmarksApi } from '../api/benchmarks';
import { modelsApi } from '../api/models';
import { exportBenchmark } from '../api/export';
import { getPromptPacks, PromptPack } from '../api/monitoring';
import { BenchmarkRun, BenchmarkResult } from '../types/benchmark';
import { Model } from '../types/model';

// --- Components ---

const ProgressBar = ({ completed, total }: { completed: number; total: number }) => {
  const percentage = total > 0 ? Math.min(100, Math.max(0, (completed / total) * 100)) : 0;
  return (
    <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 overflow-hidden">
      <div 
        className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out" 
        style={{ width: `${percentage}%` }}
      ></div>
    </div>
  );
};

const StatusBadge = ({ status }: { status: string }) => {
  const styles = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  };
  const style = styles[status as keyof typeof styles] || 'bg-gray-100 text-gray-800';
  
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// --- Main Page ---

export default function BenchmarksPage() {
  // Data State
  const [models, setModels] = useState<Model[]>([]);
  const [history, setHistory] = useState<BenchmarkRun[]>([]);
  const [historyResults, setHistoryResults] = useState<Record<string, BenchmarkResult[]>>({});
  const [promptPacks, setPromptPacks] = useState<PromptPack[]>([]);
  
  // Form State
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [promptPack, setPromptPack] = useState<string>('synthetic_short');
  const [numRuns, setNumRuns] = useState<number>(3);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [modelSearch, setModelSearch] = useState('');
  
  // Execution State
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ completed: number; total: number }>({ completed: 0, total: 0 });
  const [liveResults, setLiveResults] = useState<BenchmarkResult[]>([]);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  
  // Refs
  const wsRef = useRef<WebSocket | null>(null);

  // Load Initial Data
  useEffect(() => {
    loadModels();
    loadHistory();
    loadPromptPacks();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

   const loadModels = async () => {
     try {
       const data = await modelsApi.listAllModels({ enabled_for_benchmark: true });
       setModels(data);
       
       if (data.length > 0) {
         const providers = Array.from(new Set(data.map(m => m.provider_account_id)));
         if (providers.length > 0) {
           setSelectedProvider(providers[0]);
         }
       }
     } catch (error) {
       console.error('Failed to load models:', error);
     }
   };

  const loadHistory = async () => {
    try {
      const data = await benchmarksApi.listBenchmarks({ limit: 20 });
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const loadPromptPacks = async () => {
    try {
      const data = await getPromptPacks();
      setPromptPacks(data);
    } catch (error) {
      console.error('Failed to load prompt packs:', error);
    }
  };

  // WebSocket Handler
  useEffect(() => {
    if (!isRunning || !currentRunId) return;

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/v1/benchmarks/${currentRunId}/stream`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        if (msg.type === 'progress') {
          setProgress({ completed: msg.completed, total: msg.total });
        } else if (msg.type === 'result') {
          if (msg.data?.model_name) {
            setLiveResults(prev => [...prev, msg.data]);
          } else {
            console.error('Invalid result message - missing model_name:', msg);
          }
        } else if (msg.type === 'complete') {
          setIsRunning(false);
          loadHistory();
          ws.close();
        } else if (msg.type === 'error') {
          console.error('Benchmark error:', msg.error);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsRunning(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [currentRunId, isRunning]);

  const handleRunBenchmark = async () => {
    if (selectedModelIds.length === 0) {
      alert('Please select at least one model');
      return;
    }

    setIsRunning(true);
    setLiveResults([]);
    setProgress({ completed: 0, total: selectedModelIds.length * numRuns });

    try {
      const run = await benchmarksApi.createBenchmark({
        model_ids: selectedModelIds,
        prompt_pack: promptPack,
        num_runs: numRuns,
        name: `Benchmark ${new Date().toLocaleString()}`
      });
      
      setCurrentRunId(run.id);
      // WebSocket effect will trigger now
    } catch (error) {
      console.error('Failed to start benchmark:', error);
      setIsRunning(false);
      alert('Failed to start benchmark');
    }
  };

  const toggleHistoryRow = async (runId: string) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
    } else {
      setExpandedRunId(runId);
      if (!historyResults[runId]) {
        try {
          const results = await benchmarksApi.getBenchmarkResults(runId);
          setHistoryResults(prev => ({ ...prev, [runId]: results }));
        } catch (error) {
          console.error('Failed to load results:', error);
        }
      }
    }
  };

  const toggleModelSelection = (modelId: string) => {
    setSelectedModelIds(prev => 
      prev.includes(modelId) 
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    );
  };

  const providerMap = useMemo(() => {
    const map = new Map<string, string>();
    models.forEach(m => {
      if (m.provider_account_id && !map.has(m.provider_account_id)) {
        map.set(m.provider_account_id, m.provider_name || m.provider_account_id);
      }
    });
    return map;
  }, [models]);

  const providers = useMemo(() => {
    return Array.from(providerMap.keys()).sort((a, b) => {
      const nameA = providerMap.get(a) || a;
      const nameB = providerMap.get(b) || b;
      return nameA.localeCompare(nameB);
    });
  }, [providerMap]);

  const filteredModels = useMemo(() => {
    return models.filter(m => 
      m.provider_account_id === selectedProvider &&
      (m.custom_name || m.model_id).toLowerCase().includes(modelSearch.toLowerCase())
    );
  }, [models, selectedProvider, modelSearch]);

  return (
    <div className="container mx-auto p-6 space-y-8 max-w-7xl">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Benchmark Runner</h1>
      </div>

      {/* Section 1: Run New Benchmark */}
      <Card className="border-l-4 border-l-blue-500 shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-500" />
            Run New Benchmark
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Model Selector */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Select Models</label>
                <div className="relative w-48">
                  <Search className="w-3 h-3 absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search..."
                    value={modelSearch}
                    onChange={(e) => setModelSearch(e.target.value)}
                    className="pl-7 pr-2 py-1 text-xs border border-gray-300 rounded-md w-full focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700"
                  />
                </div>
              </div>
              
              {providers.length > 0 && (
                <div className="border-b border-gray-200 dark:border-gray-700 mb-2">
                  <nav className="-mb-px flex space-x-4 overflow-x-auto pb-1">
                    {providers.map((providerId) => (
                      <button
                        key={providerId}
                        onClick={() => setSelectedProvider(providerId)}
                        className={`
                          whitespace-nowrap pb-2 px-1 border-b-2 font-medium text-xs transition-colors
                          ${selectedProvider === providerId
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}
                        `}
                      >
                        {providerMap.get(providerId) || providerId}
                      </button>
                    ))}
                  </nav>
                </div>
              )}

              <div className="border rounded-md p-3 h-48 overflow-y-auto bg-gray-50 dark:bg-gray-900 dark:border-gray-700">
                {filteredModels.length === 0 ? (
                  <p className="text-sm text-gray-500 p-2">No models found.</p>
                ) : (
                  filteredModels.map(model => (
                    <div key={model.id} className="flex items-center space-x-2 mb-2 last:mb-0">
                      <input
                        type="checkbox"
                        id={`model-${model.id}`}
                        checked={selectedModelIds.includes(model.id)}
                        onChange={() => toggleModelSelection(model.id)}
                        disabled={isRunning}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <label htmlFor={`model-${model.id}`} className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none truncate">
                        {model.custom_name || model.model_id}
                      </label>
                    </div>
                  ))
                )}
              </div>
              <div className="text-xs text-gray-500 text-right">
                {selectedModelIds.length} selected
              </div>
            </div>

            {/* Configuration */}
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Prompt Pack</label>
                <select
                  value={promptPack}
                  onChange={(e) => setPromptPack(e.target.value)}
                  disabled={isRunning}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100"
                >
                  {promptPacks.map(pack => (
                    <option key={pack.id} value={pack.id}>
                      {pack.name} ({pack.expected_tokens} tokens)
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Runs per Model</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={numRuns}
                  onChange={(e) => setNumRuns(parseInt(e.target.value) || 1)}
                  disabled={isRunning}
                />
              </div>
            </div>

            {/* Action & Status */}
            <div className="flex flex-col justify-end space-y-4">
              <Button 
                onClick={handleRunBenchmark} 
                disabled={isRunning || selectedModelIds.length === 0}
                className="w-full h-12 text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
              >
                {isRunning ? (
                  <>
                    <Clock className="mr-2 h-5 w-5 animate-spin" />
                    Running Benchmark...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-5 w-5" />
                    Start Benchmark
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Live Progress */}
          {isRunning && (
            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800 animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="flex justify-between text-sm mb-2 font-medium text-blue-900 dark:text-blue-100">
                <span>Progress</span>
                <span>{progress.completed} / {progress.total} runs</span>
              </div>
              <ProgressBar completed={progress.completed} total={progress.total} />
              
              {/* Live Results Preview */}
              {liveResults.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Latest Results</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-2">
                    {liveResults.slice().reverse().map((res, idx) => (
                      <div key={idx} className="flex items-center justify-between text-sm p-2 bg-white dark:bg-gray-800 rounded shadow-sm border border-gray-100 dark:border-gray-700">
                        <span className="font-medium truncate max-w-[200px]">{res.model_name}</span>
                        <div className="flex space-x-4 text-gray-600 dark:text-gray-400 text-xs">
                          <span>TTFT: {res.ttft_ms?.toFixed(0) ?? '-'}ms</span>
                          <span>TPS: {res.tps?.toFixed(1) ?? '-'}</span>
                          <span className={res.error ? "text-red-500" : "text-green-500"}>
                            {res.error ? "Failed" : "Success"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Benchmark History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" />
            Benchmark History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400 uppercase text-xs font-semibold">
                <tr>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3">Models</th>
                  <th className="px-6 py-3">Prompt Pack</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                      No benchmarks run yet.
                    </td>
                  </tr>
                ) : (
                  history.map((run) => (
                    <React.Fragment key={run.id}>
                      <tr 
                        className={`bg-white dark:bg-gray-950 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer ${expandedRunId === run.id ? 'bg-gray-50 dark:bg-gray-900' : ''}`}
                        onClick={() => toggleHistoryRow(run.id)}
                      >
                        <td className="px-6 py-4">
                          <StatusBadge status={run.status} />
                        </td>
                        <td className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">
                          {run.name}
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          {new Date(run.started_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          {run.model_ids.length} models
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          <span className="font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                            {run.prompt_pack}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            {expandedRunId === run.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </td>
                      </tr>
                      
                      {/* Expanded Details */}
                      {expandedRunId === run.id && (
                        <tr>
                          <td colSpan={6} className="px-0 py-0 bg-gray-50 dark:bg-gray-900/50">
                            <div className="p-6 border-t border-b border-gray-200 dark:border-gray-700 animate-in slide-in-from-top-2 duration-200">
                              <div className="flex items-center justify-between mb-4">
                                <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Run Results</h4>
                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      exportBenchmark(run.id, 'json').catch(err => console.error('Export failed:', err));
                                    }}
                                    className="flex items-center gap-1"
                                  >
                                    <Download className="h-3 w-3" />
                                    JSON
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      exportBenchmark(run.id, 'csv').catch(err => console.error('Export failed:', err));
                                    }}
                                    className="flex items-center gap-1"
                                  >
                                    <Download className="h-3 w-3" />
                                    CSV
                                  </Button>
                                </div>
                              </div>
                              
                              {!historyResults[run.id] ? (
                                <div className="flex justify-center py-4">
                                  <Clock className="h-5 w-5 animate-spin text-gray-400" />
                                </div>
                              ) : (
                                <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                                  <table className="w-full text-sm">
                                    <thead className="bg-gray-100 dark:bg-gray-800 text-xs uppercase text-gray-500">
                                      <tr>
                                        <th className="px-4 py-2 text-left">Model</th>
                                        <th className="px-4 py-2 text-right">TTFT (ms)</th>
                                        <th className="px-4 py-2 text-right">TPS</th>
                                        <th className="px-4 py-2 text-right">Latency (ms)</th>
                                        <th className="px-4 py-2 text-right">Tokens</th>
                                        <th className="px-4 py-2 text-center">Status</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-950">
                                      {historyResults[run.id].map((result) => (
                                        <tr key={result.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                                          <td className="px-4 py-2 font-medium">{result.model_name}</td>
                                          <td className="px-4 py-2 text-right font-mono">{result.ttft_ms?.toFixed(0) || '-'}</td>
                                          <td className="px-4 py-2 text-right font-mono">{result.tps?.toFixed(2) || '-'}</td>
                                          <td className="px-4 py-2 text-right font-mono">{result.total_latency_ms?.toFixed(0) || '-'}</td>
                                          <td className="px-4 py-2 text-right font-mono">{result.output_tokens || '-'}</td>
                                          <td className="px-4 py-2 text-center">
                                            {result.error ? (
                                              <span className="text-red-500 flex items-center justify-center gap-1" title={result.error}>
                                                <AlertCircle className="h-3 w-3" /> Error
                                              </span>
                                            ) : (
                                              <span className="text-green-500 flex items-center justify-center gap-1">
                                                <Check className="h-3 w-3" /> Success
                                              </span>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
