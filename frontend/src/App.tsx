import React from 'react';
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { LayoutDashboard, Server, Box, BarChart2, Activity, Settings } from 'lucide-react';
import DashboardPage from './pages/DashboardPage';
import { ProvidersPage } from './pages/ProvidersPage';
import { ModelsPage } from './pages/ModelsPage';
import BenchmarksPage from './pages/BenchmarksPage';
import MonitoringPage from './pages/MonitoringPage';

const SidebarItem = ({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) => {
  const location = useLocation();
  const isActive = location.pathname === to;
  
  return (
    <Link
      to={to}
      className={`flex items-center space-x-3 px-4 py-3 rounded-md transition-colors ${
        isActive 
          ? 'bg-blue-900/20 text-blue-400 border-r-2 border-blue-500' 
          : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </Link>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-950 flex flex-col fixed h-full z-10">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center space-x-2">
            <Activity className="w-6 h-6 text-blue-500" />
            <span className="text-lg font-bold tracking-tight text-white">LLM Perf Mon</span>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <SidebarItem to="/dashboard" icon={<LayoutDashboard className="w-5 h-5" />} label="Dashboard" />
          <SidebarItem to="/providers" icon={<Server className="w-5 h-5" />} label="Providers" />
          <SidebarItem to="/models" icon={<Box className="w-5 h-5" />} label="Models" />
          <SidebarItem to="/benchmarks" icon={<BarChart2 className="w-5 h-5" />} label="Benchmarks" />
          <SidebarItem to="/monitoring" icon={<Activity className="w-5 h-5" />} label="Monitoring" />
        </nav>

        <div className="p-4 border-t border-gray-800">
          <SidebarItem to="/settings" icon={<Settings className="w-5 h-5" />} label="Settings" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 overflow-auto min-h-screen">
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/providers" element={<ProvidersPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/benchmarks" element={<BenchmarksPage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="*" element={<div className="p-8 text-gray-400">404 Not Found</div>} />
      </Routes>
    </Layout>
  );
}

export default App;
