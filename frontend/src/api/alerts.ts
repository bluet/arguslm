/**
 * API functions for alert notifications.
 */

import { apiGet, apiPatch } from './client';
import {
  Alert,
  UnreadCountResponse,
  RecentAlertsResponse,
  AlertListResponse,
} from '../types/alert';

/**
 * Get count of unacknowledged alerts for notification badge.
 */
export const getUnreadCount = async (): Promise<UnreadCountResponse> => {
  return apiGet<UnreadCountResponse>('/alerts/unread-count');
};

/**
 * Get recent alerts for notification dropdown.
 * @param limit Maximum number of alerts to return (default 10)
 */
export const getRecentAlerts = async (limit = 10): Promise<RecentAlertsResponse> => {
  return apiGet<RecentAlertsResponse>(`/alerts/recent?limit=${limit}`);
};

/**
 * Acknowledge an alert by ID.
 * @param alertId Alert ID to acknowledge
 */
export const acknowledgeAlert = async (alertId: string): Promise<Alert> => {
  return apiPatch<Alert>(`/alerts/${alertId}/acknowledge`, {});
};

/**
 * Get paginated list of alerts with optional filters.
 */
export const listAlerts = async (params?: {
  rule_id?: string;
  acknowledged?: boolean;
  limit?: number;
  offset?: number;
}): Promise<AlertListResponse> => {
  const queryParams = new URLSearchParams();
  if (params?.rule_id) queryParams.append('rule_id', params.rule_id);
  if (params?.acknowledged !== undefined) {
    queryParams.append('acknowledged', params.acknowledged.toString());
  }
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const queryString = queryParams.toString();
  const path = `/alerts${queryString ? `?${queryString}` : ''}`;
  return apiGet<AlertListResponse>(path);
};
