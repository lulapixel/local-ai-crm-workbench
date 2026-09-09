import { useQuery } from "@tanstack/react-query";
import { obterCockpitDiario } from "@/services/outreach";
import type { DailyCockpitResponse, DailyFiltersState } from "../types";

export function useDailyOutreach(filters: DailyFiltersState) {
  return useQuery<DailyCockpitResponse, Error>({
    queryKey: ["outreach", "daily-cockpit", filters],
    queryFn: () =>
      obterCockpitDiario({
        date: filters.date,
        category: filters.category,
        search: filters.search,
        channel: filters.channel,
        min_score: filters.min_score,
        page: filters.page,
        page_size: filters.page_size,
      }),
    staleTime: 5000,
  });
}
