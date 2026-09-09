import { useQuery } from "@tanstack/react-query";
import { obterFilaAbordagem } from "@/services/outreach";
import type { QueueFiltersState, ReviewQueueResponse } from "../types";

export function useOutreachQueue(filters: QueueFiltersState) {
  const queryRecord: Record<string, string> = {
    status: filters.status,
    search: filters.search,
    niche: filters.niche,
    city: filters.city,
    min_score: filters.min_score,
    channel: filters.channel,
    has_landing_page: filters.has_landing_page,
    landing_page_published: filters.landing_page_published,
    confidence: filters.confidence,
    sort: filters.sort,
    page: String(filters.page),
    page_size: String(filters.page_size),
  };

  return useQuery<ReviewQueueResponse, Error>({
    queryKey: ["outreach", "review-queue", queryRecord],
    queryFn: () => obterFilaAbordagem(queryRecord),
    staleTime: 10_000,
  });
}
