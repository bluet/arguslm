import React from 'react';
import { useTheme } from 'next-themes';
import { Sun, Moon } from 'lucide-react';

const SettingsPage: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 transition-colors duration-200">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Manage your application preferences
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden transition-colors duration-200">
          <div className="p-6 border-b border-gray-100 dark:border-gray-800">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Appearance</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Customize how ArgusLM looks on your device
            </p>
          </div>
          
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-300">
                  {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Theme Mode</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Switch between light and dark themes
                  </p>
                </div>
              </div>
              
              <div className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    theme === 'light' 
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                  }`}
                >
                  <Sun size={16} />
                  Light
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    theme === 'dark' 
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                  }`}
                >
                  <Moon size={16} />
                  Dark
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
