import { useSearchParams } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { DailyOutreachHeader } from "./DailyOutreachHeader";
import { DailyOutreachSummary } from "./DailyOutreachSummary";
import { DailyOutreachFilters } from "./DailyOutreachFilters";
import { DailyActionList } from "./DailyActionList";
import { DailyExecutionMode } from "./DailyExecutionMode";
import { useDailyOutreach } from "./hooks/useDailyOutreach";
import { useDailyExecution } from "./hooks/useDailyExecution";
import type { DailyCategoryTab, DailyFiltersState } from "./types";

export function DailyOutreachPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: DailyFiltersState = {
    category: (searchParams.get("category") as DailyCategoryTab) || "all",
    search: searchParams.get("search") || "",
    niche: searchParams.get("niche") || "",
    city: searchParams.get("city") || "",
    min_score: searchParams.get("min_score") || "",
    channel: searchParams.get("channel") || "all",
    date: searchParams.get("date") || new Date().toISOString().split("T")[0],
    page: parseInt(searchParams.get("page") || "1", 10),
    page_size: parseInt(searchParams.get("page_size") || "20", 10),
  };

  const updateFilters = (key: keyof DailyFiltersState, value: any) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      if (!value || value === "all" || value === 1) {
        p.delete(key);
      } else {
        p.set(key, String(value));
      }
      return p;
    });
  };

  const clearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  const { data, isLoading, refetch, isRefetching } = useDailyOutreach(filters);

  const items = data?.items || [];
  const counts = data?.counts || {
    overdue: 0,
    ready_today: 0,
    new_contacts: 0,
    paused: 0,
    replied_recently: 0,
    upcoming: 0,
  };

  const execution = useDailyExecution(items);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <DailyOutreachHeader
          onRefresh={refetch}
          onStartSession={execution.startSession}
          isRefreshing={isRefetching}
        />

        <DailyOutreachSummary
          counts={counts}
          selectedCategory={filters.category}
          onSelectCategory={(cat) => updateFilters("category", cat)}
        />

        <DailyOutreachFilters
          filters={filters}
          onFilterChange={updateFilters}
          onClearFilters={clearFilters}
        />

        {execution.isSessionActive ? (
          <DailyExecutionMode
            items={items}
            currentIndex={execution.currentIndex}
            totalCount={execution.totalCount}
            completedCount={execution.completedCount}
            onNext={execution.nextAction}
            onPrevious={execution.previousAction}
            onExit={execution.endSession}
            onActionSuccess={() => {
              refetch();
              execution.markCurrentCompleted();
            }}
          />
        ) : (
          <DailyActionList
            items={items}
            isLoading={isLoading}
            onRefresh={refetch}
            onClearFilters={clearFilters}
          />
        )}
      </main>
    </div>
  );
}
