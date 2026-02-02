import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { modelsApi } from '../api/models';

import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Badge } from './ui/Badge';
import { Search, Filter, Check, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';

interface ModelSelectorProps {
  selectedIds: string[];
  onChange: (selectedIds: string[]) => void;
  filterByMonitoring?: boolean;
  filterByBenchmark?: boolean;
  className?: string;
}

export const ModelSelector = ({
  selectedIds,
  onChange,
  filterByMonitoring,
  filterByBenchmark,
  className = '',
}: ModelSelectorProps) => {
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

  const { data: models, isLoading, isError } = useQuery({
    queryKey: ['models', debouncedSearch, providerFilter, page, filterByMonitoring, filterByBenchmark],
    queryFn: () => modelsApi.listModels({
      search: debouncedSearch,
      provider_id: providerFilter || undefined,
      enabled_for_monitoring: filterByMonitoring,
      enabled_for_benchmark: filterByBenchmark,
      limit,
      offset: (page - 1) * limit,
    }),
  });

  // Mock providers for now since we don't have a providers API
  // In a real app, we would fetch this list
  const providers = ['openai', 'anthropic', 'google', 'meta', 'mistral', 'cohere'];

  const handleToggle = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((modelId) => modelId !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  return (
    <div className={`flex flex-col space-y-4 ${className}`}>
      <div className="flex flex-col sm:flex-row gap-4">
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

      <div className="rounded-md border border-gray-200 dark:border-gray-800 overflow-hidden">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          </div>
        ) : isError ? (
          <div className="flex h-40 items-center justify-center text-red-500">
            Failed to load models
          </div>
        ) : models && models.length > 0 ? (
          <div className="divide-y divide-gray-200 dark:divide-gray-800">
            {models.map((model) => {
              const isSelected = selectedIds.includes(model.id);
              return (
                <div
                  key={model.id}
                  onClick={() => handleToggle(model.id)}
                  className={`flex items-center justify-between p-4 cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-900 ${
                    isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        isSelected
                          ? 'border-blue-600 bg-blue-600 text-white'
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      {isSelected && <Check className="h-3.5 w-3.5" />}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-50">
                        {model.custom_name || model.model_id}
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5">
                          {model.provider_account_id}
                        </Badge>
                        {model.source === 'manual' && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5">
                            Manual
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {model.enabled_for_monitoring && (
                      <Badge variant="success" className="text-[10px]">
                        Monitored
                      </Badge>
                    )}
                    {model.enabled_for_benchmark && (
                      <Badge variant="default" className="text-[10px]">
                        Benchmark
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex h-40 items-center justify-center text-gray-500">
            No models found
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
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
    </div>
  );
};
