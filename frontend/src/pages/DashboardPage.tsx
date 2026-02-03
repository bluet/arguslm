import React, { useEffect, useState } from 'react';
import { 
  Activity, 
  Clock, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  TrendingUp, 
  Server,
  AlertTriangle
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { getDashboardData } from '../api/dashboard';
import { DashboardData } from '../types/dashboard';

const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');

  const fetchData = async () => {
    try {
      setLoading(true);
      const dashboardData = await getDashboardData(timeRange);
      setData(dashboardData);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError('Failed to fetch dashboard data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [timeRange]);

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-red-500 flex items-center gap-2">
          <AlertCircle size={24} />
          <span>{error}</span>
          <button onClick={fetchData} className="underline ml-2">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button 
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors shadow-sm"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Section 1: Status Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Total Models */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Models</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">{data?.stats.totalModels || 0}</h3>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-blue-600">
              <Server size={24} />
            </div>
          </div>
        </div>

        {/* Models Status */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500">Model Health</p>
              <div className="flex gap-3 mt-2">
                <div className="flex items-center gap-1 text-green-600">
                  <CheckCircle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsUp || 0}</span>
                </div>
                <div className="flex items-center gap-1 text-red-600">
                  <XCircle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsDown || 0}</span>
                </div>
                <div className="flex items-center gap-1 text-yellow-600">
                  <AlertTriangle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsDegraded || 0}</span>
                </div>
              </div>
            </div>
            <div className="p-3 bg-green-50 rounded-lg text-green-600">
              <Activity size={24} />
            </div>
          </div>
        </div>

        {/* Last Check */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500">Last Check</p>
              <h3 className="text-xl font-bold text-gray-900 mt-2">
                {data?.stats.lastCheck ? formatRelativeTime(data.stats.lastCheck) : 'Never'}
              </h3>
            </div>
            <div className="p-3 bg-purple-50 rounded-lg text-purple-600">
              <Clock size={24} />
            </div>
          </div>
        </div>

        {/* Alerts */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500">Active Alerts</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">{data?.stats.unacknowledgedAlerts || 0}</h3>
            </div>
            <div className={`p-3 rounded-lg ${(data?.stats.unacknowledgedAlerts || 0) > 0 ? 'bg-red-50 text-red-600' : 'bg-gray-50 text-gray-400'}`}>
              <AlertCircle size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Uptime Grid */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {data?.uptimeChecks.map((check) => (
            <div key={check.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-medium text-gray-900 truncate pr-2" title={check.model_name}>
                  {check.model_name}
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  check.status === 'up' ? 'bg-green-100 text-green-700' :
                  check.status === 'down' ? 'bg-red-100 text-red-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>
                  {check.status.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between text-sm text-gray-500">
                <span>Latency</span>
                <span className="font-medium text-gray-700">
                  {check.latency_ms ? `${Math.round(check.latency_ms)}ms` : '-'}
                </span>
              </div>
              <div className="flex justify-between text-sm text-gray-500 mt-1">
                <span>Checked</span>
                <span>{formatTime(check.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Performance Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Performance Trends</h2>
            <div className="flex bg-gray-100 rounded-lg p-1">
              {(['24h', '7d', '30d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    timeRange === range 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
          
          <div className="space-y-8">
            {/* TTFT Chart */}
            <div className="h-[250px]">
              <h3 className="text-sm font-medium text-gray-500 mb-4">Time to First Token (ms)</h3>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data?.performanceHistory}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="time" 
                    tickFormatter={(time) => new Date(time).toLocaleTimeString([], { hour: '2-digit' })}
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="ttft" 
                    stroke="#8B5CF6" 
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* TPS Chart */}
            <div className="h-[250px]">
              <h3 className="text-sm font-medium text-gray-500 mb-4">Tokens Per Second</h3>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data?.performanceHistory}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="time" 
                    tickFormatter={(time) => new Date(time).toLocaleTimeString([], { hour: '2-digit' })}
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="tps" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Column: Latency Bar Chart & Recent Activity */}
        <div className="space-y-6">
          {/* Latency Comparison */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Latency by Model</h2>
            <div className="h-[300px]">
              {data?.latencyComparison && data.latencyComparison.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.latencyComparison} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#E5E7EB" />
                    <XAxis 
                      type="number" 
                      domain={[0, 'auto']}
                      tick={{ fontSize: 12, fill: '#6B7280' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `${value}ms`}
                    />
                    <YAxis 
                      dataKey="model_name" 
                      type="category" 
                      width={100}
                      tick={{ fontSize: 12, fill: '#6B7280' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip 
                      cursor={{ fill: '#F3F4F6' }}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(value: number | undefined) => [`${Math.round(Number(value || 0))}ms`, 'Latency']}
                    />
                    <Bar dataKey="latency" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  <p>No latency data available</p>
                </div>
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex-1">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
            <div className="space-y-4">
              {data?.recentActivity.map((item) => (
                <div key={item.id} className="flex gap-3 items-start">
                  <div className={`mt-1 p-1.5 rounded-full flex-shrink-0 ${
                    item.status === 'success' ? 'bg-green-100 text-green-600' :
                    item.status === 'failure' ? 'bg-red-100 text-red-600' :
                    item.status === 'warning' ? 'bg-yellow-100 text-yellow-600' :
                    'bg-blue-100 text-blue-600'
                  }`}>
                    {item.type === 'benchmark' ? <TrendingUp size={14} /> :
                     item.type === 'alert' ? <AlertCircle size={14} /> :
                     <Activity size={14} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.message}</p>
                    <div className="flex justify-between items-center mt-0.5">
                      <p className="text-xs text-gray-500 truncate">{item.model_name}</p>
                      <p className="text-xs text-gray-400 whitespace-nowrap ml-2">
                        {formatRelativeTime(item.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {(!data?.recentActivity || data.recentActivity.length === 0) && (
                <p className="text-sm text-gray-500 text-center py-4">No recent activity</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
