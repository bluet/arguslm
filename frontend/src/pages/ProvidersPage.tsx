import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Plus, 
  RefreshCw, 
  Trash2, 
  CheckCircle2, 
  XCircle, 
  Server, 
  Globe, 
  Activity,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { 
  listProviders, 
  createProvider, 
  updateProvider, 
  deleteProvider, 
  testProvider, 
  refreshModels 
} from '../api/providers';
import { Provider, ProviderCreate, ProviderType } from '../types/provider';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Modal } from '../components/ui/Modal';
import { Toggle } from '../components/ui/Toggle';
import { Card } from '../components/ui/Card';

const PROVIDER_TYPES: { value: ProviderType; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'google_vertex', label: 'Google Vertex AI' },
  { value: 'google_gemini', label: 'Google Gemini' },
  { value: 'aws_bedrock', label: 'AWS Bedrock' },
  { value: 'azure_openai', label: 'Azure OpenAI' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'lm_studio', label: 'LM Studio' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'together_ai', label: 'Together AI' },
  { value: 'groq', label: 'Groq' },
  { value: 'mistral', label: 'Mistral AI' },
  { value: 'custom_openai_compatible', label: 'Custom OpenAI Compatible' },
];

type ProviderFieldConfig = {
  requiresApiKey: boolean;
  requiresBaseUrl: boolean;
  showOrgFields: boolean;
  apiKeyLabel?: string;
  baseUrlLabel?: string;
};

const PROVIDER_FIELD_CONFIG: Record<ProviderType, ProviderFieldConfig> = {
  openai: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: true },
  anthropic: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  google_vertex: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  google_gemini: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  aws_bedrock: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  azure_openai: { requiresApiKey: true, requiresBaseUrl: true, showOrgFields: false },
  ollama: { requiresApiKey: false, requiresBaseUrl: true, showOrgFields: false, baseUrlLabel: 'Base URL' },
  lm_studio: { requiresApiKey: false, requiresBaseUrl: true, showOrgFields: false, baseUrlLabel: 'Base URL' },
  openrouter: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  together_ai: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  groq: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  mistral: { requiresApiKey: true, requiresBaseUrl: false, showOrgFields: false },
  custom_openai_compatible: { requiresApiKey: true, requiresBaseUrl: true, showOrgFields: false },
};

export const ProvidersPage = () => {
  const queryClient = useQueryClient();
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [expandedProviderId, setExpandedProviderId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; latency?: number }>>({});

  // Form state for new provider
  const [newProvider, setNewProvider] = useState<ProviderCreate>({
    name: '',
    provider_type: 'openai',
    api_key: '',
    base_url: '',
    organization_id: '',
    project_id: '',
    region: '',
    is_enabled: true,
  });

  const { data: providers, isLoading, error } = useQuery({
    queryKey: ['providers'],
    queryFn: listProviders,
  });

  const createMutation = useMutation({
    mutationFn: createProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setIsAddModalOpen(false);
      setNewProvider({
        name: '',
        provider_type: 'openai',
        api_key: '',
        base_url: '',
        organization_id: '',
        project_id: '',
        region: '',
        is_enabled: true,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Provider> }) => 
      updateProvider(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });

  const testMutation = useMutation({
    mutationFn: testProvider,
    onSuccess: (data, variables) => {
      setTestResults(prev => ({
        ...prev,
        [variables]: { success: data.success, message: data.message, latency: data.latency_ms }
      }));
    },
    onError: (error, variables) => {
      setTestResults(prev => ({
        ...prev,
        [variables]: { success: false, message: error instanceof Error ? error.message : 'Test failed' }
      }));
    }
  });

  const refreshModelsMutation = useMutation({
    mutationFn: refreshModels,
    onSuccess: () => {
      // Maybe show a toast?
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(newProvider);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this provider? This action cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  const toggleExpanded = (id: string) => {
    setExpandedProviderId(expandedProviderId === id ? null : id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-400">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="font-mono text-sm tracking-wider">INITIALIZING SYSTEM...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-red-500">
        <div className="text-center space-y-4">
          <Activity className="w-16 h-16 mx-auto opacity-50" />
          <h2 className="text-xl font-bold tracking-tight">SYSTEM ERROR</h2>
          <p className="font-mono text-sm">{(error as Error).message}</p>
          <Button onClick={() => window.location.reload()} variant="secondary">RETRY CONNECTION</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between border-b border-gray-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Provider Management</h1>
            <p className="text-gray-400">Configure and monitor LLM service providers.</p>
          </div>
          <Button onClick={() => setIsAddModalOpen(true)} icon={<Plus className="w-4 h-4" />}>
            Add Provider
          </Button>
        </div>

        <div className="grid gap-4">
          {providers?.map((provider) => (
            <Card key={provider.id} className={`transition-all duration-200 ${expandedProviderId === provider.id ? 'ring-1 ring-blue-900 shadow-lg shadow-blue-900/10' : ''}`}>
              <div className="p-6 flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className={`p-2 rounded-md ${provider.is_enabled ? 'bg-blue-900/20 text-blue-400' : 'bg-gray-800 text-gray-500'}`}>
                    <Server className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      {provider.name}
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-900 text-gray-500 border border-gray-800">
                        {provider.provider_type}
                      </span>
                    </h3>
                    <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        {provider.is_enabled ? 'Active' : 'Disabled'}
                      </span>
                      {provider.base_url && (
                        <span className="flex items-center gap-1 font-mono text-xs truncate max-w-[200px]">
                          <Globe className="w-3 h-3" />
                          {provider.base_url}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 mr-4">
                    <span className="text-sm text-gray-500 uppercase text-xs font-bold tracking-wider">Status</span>
                    <Toggle 
                      checked={provider.is_enabled} 
                      onCheckedChange={(checked) => updateMutation.mutate({ id: provider.id, data: { is_enabled: checked } })} 
                    />
                  </div>
                  
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => toggleExpanded(provider.id)}
                  >
                    {expandedProviderId === provider.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </Button>
                </div>
              </div>

              {expandedProviderId === provider.id && (
                <div className="px-6 pb-6 pt-0 border-t border-gray-800/50 animate-in slide-in-from-top-2 duration-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Configuration</h4>
                      <Input 
                        label="Display Name" 
                        defaultValue={provider.name}
                        onBlur={(e) => updateMutation.mutate({ id: provider.id, data: { name: e.target.value } })}
                      />
                      <Input 
                        label="API Key" 
                        type="password" 
                        placeholder="••••••••••••••••"
                        defaultValue={provider.api_key ? '••••••••' : ''}
                        onChange={(e) => {
                          // Only update if value is not empty and not the mask
                          if (e.target.value && e.target.value !== '••••••••') {
                             updateMutation.mutate({ id: provider.id, data: { api_key: e.target.value } });
                          }
                        }}
                      />
                      <Input 
                        label="Base URL" 
                        defaultValue={provider.base_url}
                        placeholder="https://api.example.com/v1"
                        onBlur={(e) => updateMutation.mutate({ id: provider.id, data: { base_url: e.target.value } })}
                      />
                    </div>
                    
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Actions</h4>
                      
                      <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-800 space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-300">Connection Test</span>
                          <Button 
                            size="sm" 
                            variant="secondary" 
                            onClick={() => testMutation.mutate(provider.id)}
                            isLoading={testMutation.isPending && testMutation.variables === provider.id}
                          >
                            Run Test
                          </Button>
                        </div>
                        {testResults[provider.id] && (
                          <div className={`text-xs p-2 rounded border ${testResults[provider.id].success ? 'bg-green-900/20 border-green-900 text-green-400' : 'bg-red-900/20 border-red-900 text-red-400'}`}>
                            <div className="flex items-center gap-2 font-bold">
                              {testResults[provider.id].success ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                              {testResults[provider.id].success ? 'CONNECTION SUCCESSFUL' : 'CONNECTION FAILED'}
                            </div>
                            <div className="mt-1 font-mono opacity-80">
                              {testResults[provider.id].message}
                              {testResults[provider.id].latency && ` (${testResults[provider.id].latency}ms)`}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-800 flex items-center justify-between">
                        <span className="text-sm text-gray-300">Model Catalog</span>
                        <Button 
                          size="sm" 
                          variant="secondary"
                          icon={<RefreshCw className="w-3 h-3" />}
                          onClick={() => refreshModelsMutation.mutate(provider.id)}
                          isLoading={refreshModelsMutation.isPending && refreshModelsMutation.variables === provider.id}
                        >
                          Refresh Models
                        </Button>
                      </div>

                      <div className="pt-4 border-t border-gray-800 flex justify-end">
                        <Button 
                          variant="danger" 
                          size="sm" 
                          icon={<Trash2 className="w-3 h-3" />}
                          onClick={() => handleDelete(provider.id)}
                          isLoading={deleteMutation.isPending && deleteMutation.variables === provider.id}
                        >
                          Delete Provider
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          ))}

          {providers?.length === 0 && (
            <div className="text-center py-20 border-2 border-dashed border-gray-800 rounded-lg bg-gray-900/20">
              <Server className="w-12 h-12 mx-auto text-gray-700 mb-4" />
              <h3 className="text-lg font-medium text-gray-300">No Providers Configured</h3>
              <p className="text-gray-500 mt-2 mb-6 max-w-sm mx-auto">Add your first LLM provider to start monitoring performance and costs.</p>
              <Button onClick={() => setIsAddModalOpen(true)} icon={<Plus className="w-4 h-4" />}>
                Add Provider
              </Button>
            </div>
          )}
        </div>
      </div>

      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add New Provider"
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} isLoading={createMutation.isPending}>Create Provider</Button>
          </>
        }
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Display Name"
            placeholder="e.g. Production OpenAI"
            value={newProvider.name}
            onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
            required
          />
          
          <Select
            label="Provider Type"
            options={PROVIDER_TYPES}
            value={newProvider.provider_type}
            onChange={(e) => setNewProvider({ ...newProvider, provider_type: e.target.value as ProviderType })}
          />

          {PROVIDER_FIELD_CONFIG[newProvider.provider_type].requiresApiKey && (
            <Input
              label={PROVIDER_FIELD_CONFIG[newProvider.provider_type].apiKeyLabel || "API Key"}
              type="password"
              placeholder="sk-..."
              value={newProvider.api_key}
              onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
              required={PROVIDER_FIELD_CONFIG[newProvider.provider_type].requiresApiKey}
            />
          )}

          <Input
            label={PROVIDER_FIELD_CONFIG[newProvider.provider_type].baseUrlLabel || (PROVIDER_FIELD_CONFIG[newProvider.provider_type].requiresBaseUrl ? "Base URL" : "Base URL (Optional)")}
            placeholder="https://api.example.com/v1"
            value={newProvider.base_url}
            onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
            required={PROVIDER_FIELD_CONFIG[newProvider.provider_type].requiresBaseUrl}
          />

          {PROVIDER_FIELD_CONFIG[newProvider.provider_type].showOrgFields && (
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Organization ID (Optional)"
                placeholder="org-..."
                value={newProvider.organization_id}
                onChange={(e) => setNewProvider({ ...newProvider, organization_id: e.target.value })}
              />
              <Input
                label="Project ID (Optional)"
                placeholder="my-project-id"
                value={newProvider.project_id}
                onChange={(e) => setNewProvider({ ...newProvider, project_id: e.target.value })}
              />
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
};
