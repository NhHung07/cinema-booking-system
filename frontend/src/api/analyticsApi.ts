import api from "./axios";
import type { AnalyticsOverviewResponse } from "../types/analytics";

export async function getAnalyticsOverview(days?: number): Promise<AnalyticsOverviewResponse> {
  const params: Record<string, number> = {};
  if (days !== undefined) {
    params.days = days;
  }
  const response = await api.get<AnalyticsOverviewResponse>("/admin/analytics/overview", {
    params,
  });
  return response.data;
}

