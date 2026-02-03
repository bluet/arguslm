import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Bell, Check, AlertTriangle, X } from 'lucide-react';
import { getRecentAlerts, acknowledgeAlert } from '../api/alerts';
import { Alert, RecentAlertsResponse } from '../types/alert';

const POLL_INTERVAL_MS = 30000; // 30 seconds

/**
 * Notification bell component with badge and dropdown.
 * Polls for unread alerts every 30 seconds.
 */
export const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setError(null);
      const response: RecentAlertsResponse = await getRecentAlerts(10);
      setAlerts(response.items);
      setUnreadCount(response.total_unread);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
      setError('Failed to load alerts');
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchAlerts();
    const intervalId = setInterval(fetchAlerts, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [fetchAlerts]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAcknowledge = async (alertId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setIsLoading(true);
    try {
      await acknowledgeAlert(alertId);
      // Refresh alerts after acknowledgment
      await fetchAlerts();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      setError('Failed to acknowledge');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button with badge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-md text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-bold text-white bg-red-600 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-[450px] max-h-96 overflow-y-auto bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <h3 className="text-sm font-semibold text-gray-100">Notifications</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-gray-400 hover:text-gray-200 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content */}
          <div className="divide-y divide-gray-800">
            {error && (
              <div className="px-4 py-3 text-sm text-red-400">{error}</div>
            )}

            {!error && alerts.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-500">
                <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No notifications</p>
              </div>
            )}

            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`px-4 py-3 transition-colors ${
                  alert.acknowledged
                    ? 'bg-gray-900 opacity-60'
                    : 'bg-gray-850 hover:bg-gray-800'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <AlertTriangle
                      className={`w-4 h-4 ${
                        alert.acknowledged ? 'text-gray-500' : 'text-yellow-500'
                      }`}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm whitespace-pre-wrap break-all ${
                        alert.acknowledged ? 'text-gray-400' : 'text-gray-200'
                      }`}
                    >
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatTime(alert.created_at)}
                    </p>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={(e) => handleAcknowledge(alert.id, e)}
                      disabled={isLoading}
                      className="flex-shrink-0 p-1.5 text-gray-400 hover:text-green-400 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
                      title="Acknowledge"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          {alerts.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-700 bg-gray-900/50">
              <p className="text-xs text-gray-500 text-center">
                {unreadCount > 0
                  ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}`
                  : 'All caught up!'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
