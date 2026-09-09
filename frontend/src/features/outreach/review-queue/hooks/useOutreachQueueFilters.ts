import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { QueueFiltersState, QueueStatusTab } from "../types";

export function useOutreachQueueFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: QueueFiltersState = useMemo(() => {
    const rawStatus = searchParams.get("status");
    const status: QueueStatusTab =
      rawStatus === "not_generated" || rawStatus === "approved" || rawStatus === "archived"
        ? rawStatus
        : "draft";

    return {
      status,
      search: searchParams.get("search") || "",
      niche: searchParams.get("niche") || "",
      city: searchParams.get("city") || "",
      min_score: searchParams.get("min_score") || "",
      channel: searchParams.get("channel") || "",
      has_landing_page: searchParams.get("has_landing_page") || "",
      landing_page_published: searchParams.get("landing_page_published") || "",
      confidence: searchParams.get("confidence") || "",
      sort: searchParams.get("sort") || "score",
      page: parseInt(searchParams.get("page") || "1", 10) || 1,
      page_size: parseInt(searchParams.get("page_size") || "20", 10) || 20,
    };
  }, [searchParams]);

  const updateFilters = (newFilters: Partial<QueueFiltersState>) => {
    const updated = { ...filters, ...newFilters };
    // Reset to page 1 if any filter except page changed
    if (!("page" in newFilters) && ("search" in newFilters || "status" in newFilters || "niche" in newFilters || "city" in newFilters || "min_score" in newFilters || "channel" in newFilters || "sort" in newFilters || "confidence" in newFilters)) {
      updated.page = 1;
    }

    const params = new URLSearchParams();
    if (updated.status) params.set("status", updated.status);
    if (updated.search) params.set("search", updated.search);
    if (updated.niche) params.set("niche", updated.niche);
    if (updated.city) params.set("city", updated.city);
    if (updated.min_score) params.set("min_score", updated.min_score);
    if (updated.channel) params.set("channel", updated.channel);
    if (updated.has_landing_page) params.set("has_landing_page", updated.has_landing_page);
    if (updated.landing_page_published) params.set("landing_page_published", updated.landing_page_published);
    if (updated.confidence) params.set("confidence", updated.confidence);
    if (updated.sort && updated.sort !== "score") params.set("sort", updated.sort);
    if (updated.page > 1) params.set("page", String(updated.page));
    if (updated.page_size !== 20) params.set("page_size", String(updated.page_size));

    setSearchParams(params, { replace: true });
  };

  const resetFilters = () => {
    const params = new URLSearchParams();
    params.set("status", filters.status);
    setSearchParams(params, { replace: true });
  };

  return {
    filters,
    updateFilters,
    resetFilters,
  };
}
