import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { modelsApi } from '../api/models';
import { Model, CreateModelData } from '../types/model';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Toggle } from '../components/ui/Toggle';
import { Modal } from '../components/ui/Modal';
import { Search, Filter, Loader2, ChevronLeft, ChevronRight, Edit2, Check, X } from 'lucide-react';

export const ModelsPage = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const limit = 10;

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 500);
    return () => clearTimeout(timer);
  }, [search]);

  // Queries
  const { data: models, isLoading, isError } = useQuery({
    queryKey: ['models', debouncedSearch, providerFilter, page],
    queryFn: () => modelsApi.listModels({
      search: debouncedSearch,
      provider_id: providerFilter || undefined,
      limit,
      offset: (page - 1) * limit,
    }),
  });

  // Mutations
  const updateModelMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Model> }) => 
      modelsApi.updateModel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });

  const createModelMutation = useMutation({
    mutationFn: (data: CreateModelData) => modelsApi.createModel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      setIsAddModalOpen(false);
      setNewModelData({
        provider_account_id: '',
        model_id: '',
        custom_name: '',
        enabled_for_monitoring: false,
        enabled_for_benchmark: false,
      });
    },
  });

  // State for Add Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newModelData, setNewModelData] = useState<CreateModelData>({
    provider_account_id: '',
    model_id: '',
    custom_name: '',
    enabled_for_monitoring: false,
    enabled_for_benchmark: false,
  });

  // State for Inline Edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const startEditing = (model: Model) => {
    setEditingId(model.id);
    setEditName(model.custom_name || model.model_id);
  };

  const saveEdit = () => {
    if (editingId) {
      updateModelMutation.mutate({ id: editingId, data: { custom_name: editName } });
      setEditingId(null);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName('');
  };

  // Mock providers
  const providers = ['openai', 'anthropic', 'google', 'meta', 'mistral', 'cohere'];

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-50">Models</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage and monitor your LLM models</p>
        </div>
        <Button onClick={() => setIsAddModalOpen(true)}>Add Manual Model</Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500 dark:text-gray-400" />
          <Input
            placeholder="Search models..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="relative w-full sm:w-48">
          <Filter className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500 dark:text-gray-400" />
          <select
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="flex h-10 w-full rounded-md border border-gray-300 bg-transparent px-3 py-2 pl-9 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:text-gray-50 appearance-none"
          >
            <option value="">All Providers</option>
            {providers.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden bg-white dark:bg-gray-950 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400 font-medium border-b border-gray-200 dark:border-gray-800">
              <tr>
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Provider</th>
                <th className="px-6 py-3">Source</th>
                <th className="px-6 py-3 text-center">Monitoring</th>
                <th className="px-6 py-3 text-center">Benchmark</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600 mx-auto" />
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-red-500">
                    Failed to load models
                  </td>
                </tr>
              ) : models && models.length > 0 ? (
                models.map((model) => (
                  <tr key={model.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors">
                    <td className="px-6 py-4">
                      {editingId === model.id ? (
                        <div className="flex items-center space-x-2">
                          <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            className="h-8 w-48"
                            autoFocus
                          />
                          <Button size="icon" variant="ghost" className="h-8 w-8 text-green-600" onClick={saveEdit}>
                            <Check className="h-4 w-4" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-8 w-8 text-red-600" onClick={cancelEdit}>
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2 group">
                          <span className="font-medium text-gray-900 dark:text-gray-50">
                            {model.custom_name || model.model_id}
                          </span>
                          <button
                            onClick={() => startEditing(model)}
                            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity"
                          >
                            <Edit2 className="h-3 w-3" />
                          </button>
                        </div>
                      )}
                      <div className="text-xs text-gray-500 mt-0.5 font-mono">{model.model_id}</div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="outline">{model.provider_name || model.provider_account_id}</Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={model.source === 'manual' ? 'secondary' : 'outline'}>
                        {model.source}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex justify-center">
                        <Toggle
                          checked={model.enabled_for_monitoring}
                          onCheckedChange={(checked) => 
                            updateModelMutation.mutate({ id: model.id, data: { enabled_for_monitoring: checked } })
                          }
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex justify-center">
                        <Toggle
                          checked={model.enabled_for_benchmark}
                          onCheckedChange={(checked) => 
                            updateModelMutation.mutate({ id: model.id, data: { enabled_for_benchmark: checked } })
                          }
                        />
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    No models found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Page {page}
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={isLoading || (models && models.length < limit)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Add Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Manual Model"
        footer={
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createModelMutation.mutate(newModelData)}
              disabled={!newModelData.provider_account_id || !newModelData.model_id || createModelMutation.isPending}
            >
              {createModelMutation.isPending ? 'Adding...' : 'Add Model'}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Provider Account ID
            </label>
            <Input
              placeholder="e.g. openai-account-1"
              value={newModelData.provider_account_id}
              onChange={(e) => setNewModelData({ ...newModelData, provider_account_id: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Model ID
            </label>
            <Input
              placeholder="e.g. gpt-4-turbo"
              value={newModelData.model_id}
              onChange={(e) => setNewModelData({ ...newModelData, model_id: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Custom Name (Optional)
            </label>
            <Input
              placeholder="e.g. GPT-4 Turbo Production"
              value={newModelData.custom_name || ''}
              onChange={(e) => setNewModelData({ ...newModelData, custom_name: e.target.value })}
            />
          </div>
          <div className="flex items-center justify-between py-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable for Monitoring
            </label>
            <Toggle
              checked={newModelData.enabled_for_monitoring || false}
              onCheckedChange={(checked) => setNewModelData({ ...newModelData, enabled_for_monitoring: checked })}
            />
          </div>
          <div className="flex items-center justify-between py-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable for Benchmark
            </label>
            <Toggle
              checked={newModelData.enabled_for_benchmark || false}
              onCheckedChange={(checked) => setNewModelData({ ...newModelData, enabled_for_benchmark: checked })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
