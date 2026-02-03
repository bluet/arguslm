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
  Legend,
  ResponsiveContainer 
} from 'recharts';
import { getDashboardData } from '../api/dashboard';
import { DashboardData } from '../types/dashboard';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

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
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950">
        <div className="text-red-500 flex items-center gap-2">
          <AlertCircle size={24} />
          <span>{error}</span>
          <button onClick={fetchData} className="underline ml-2">Retry</button>
        </div>
      </div>
    );
  }

  const modelNames = Array.from(new Set(
    data?.performanceHistory.flatMap(item => Object.keys(item).filter(k => k !== 'time')) || []
  ));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 transition-colors duration-200">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button 
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:bg-gray-950 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors shadow-sm"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Section 1: Status Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Total Models */}
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Models</p>
              <h3 className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{data?.stats.totalModels || 0}</h3>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 dark:text-blue-400">
              <Server size={24} />
            </div>
          </div>
        </div>

        {/* Models Status */}
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Model Health</p>
              <div className="flex gap-3 mt-2">
                <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                  <CheckCircle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsUp || 0}</span>
                </div>
                <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
                  <XCircle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsDown || 0}</span>
                </div>
                <div className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                  <AlertTriangle size={16} />
                  <span className="font-bold text-xl">{data?.stats.modelsDegraded || 0}</span>
                </div>
              </div>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-green-600 dark:text-green-400">
              <Activity size={24} />
            </div>
          </div>
        </div>

        {/* Last Check */}
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Check</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mt-2">
                {data?.stats.lastCheck ? formatRelativeTime(data.stats.lastCheck) : 'Never'}
              </h3>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
              <Clock size={24} />
            </div>
          </div>
        </div>

        {/* Alerts */}
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Alerts</p>
              <h3 className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{data?.stats.unacknowledgedAlerts || 0}</h3>
            </div>
            <div className={`p-3 rounded-lg ${(data?.stats.unacknowledgedAlerts || 0) > 0 ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400' : 'bg-gray-50 dark:bg-gray-950 text-gray-400 dark:text-gray-500'}`}>
              <AlertCircle size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Uptime Grid */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Model Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {data?.uptimeChecks.map((check) => (
            <div key={check.id} className="bg-white dark:bg-gray-900 p-4 rounded-lg shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-medium text-gray-900 dark:text-white truncate pr-2" title={check.model_name}>
                  {check.model_name}
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  check.status === 'up' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' :
                  check.status === 'down' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                  'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                }`}>
                  {check.status.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
                <span>Latency</span>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {check.latency_ms ? `${Math.round(check.latency_ms)}ms` : '-'}
                </span>
              </div>
              <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mt-1">
                <span>Checked</span>
                <span>{formatTime(check.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Performance Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Performance Trends</h2>
            <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
              {(['24h', '7d', '30d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    timeRange === range 
                      ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
          
          <div className="space-y-8">
            {/* Latency History Chart */}
            <div className="h-[400px]">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Latency History (ms)</h3>
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
                    wrapperStyle={{ zIndex: 1000 }}
                  />
                  <Legend />
                  {modelNames.map((modelName, index) => (
                    <Line 
                      key={modelName}
                      type="monotone" 
                      dataKey={modelName} 
                      stroke={COLORS[index % COLORS.length]} 
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Column: Latency Bar Chart & Recent Activity */}
        <div className="space-y-6">
          {/* Latency Comparison */}
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Latency by Model</h2>
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
                <div className="h-full flex items-center justify-center text-gray-400 dark:text-gray-500">
                  <p>No latency data available</p>
                </div>
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 flex-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h2>
            <div className="space-y-4">
              {data?.recentActivity.map((item) => (
                <div key={item.id} className="flex gap-3 items-start">
                  <div className={`mt-1 p-1.5 rounded-full flex-shrink-0 ${
                    item.status === 'success' ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' :
                    item.status === 'failure' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' :
                    item.status === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400' :
                    'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  }`}>
                    {item.type === 'benchmark' ? <TrendingUp size={14} /> :
                     item.type === 'alert' ? <AlertCircle size={14} /> :
                     <Activity size={14} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{item.message}</p>
                    <div className="flex justify-between items-center mt-0.5">
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{item.model_name}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap ml-2">
                        {formatRelativeTime(item.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {(!data?.recentActivity || data.recentActivity.length === 0) && (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No recent activity</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
