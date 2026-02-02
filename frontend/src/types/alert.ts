/**
 * Alert notification types for the frontend.
 */

export interface Alert {
  id: string;
  rule_id: string;
  model_id: string | null;
  message: string;
  acknowledged: boolean;
  created_at: string;
}

export interface AlertRule {
  id: string;
  name: string;
  rule_type: 'any_model_down' | 'specific_model_down' | 'model_unavailable_everywhere' | 'performance_degradation';
  enabled: boolean;
  target_model_id: string | null;
  target_model_name: string | null;
  threshold_config: Record<string, unknown> | null;
  notify_in_app: boolean;
  notify_email: boolean;
  notify_webhook: boolean;
  webhook_url: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

export interface RecentAlertsResponse {
  items: Alert[];
  total_unread: number;
}

export interface AlertListResponse {
  items: Alert[];
  unacknowledged_count: number;
  limit: number;
  offset: number;
}
