import { AlertTriangle, Zap, Sparkles, Pause, MessageSquare, Clock } from "lucide-react";
import type { DailyCategoryTab, DailyCounts } from "./types";

interface DailyOutreachSummaryProps {
  counts: DailyCounts;
  selectedCategory: DailyCategoryTab;
  onSelectCategory: (cat: DailyCategoryTab) => void;
}

export function DailyOutreachSummary({ counts, selectedCategory, onSelectCategory }: DailyOutreachSummaryProps) {
  const cards = [
    {
      id: "overdue" as DailyCategoryTab,
      label: "Atrasados",
      count: counts.overdue,
      icon: <AlertTriangle className="size-4 text-destructive" />,
      badgeColor: "border-destructive/30 bg-destructive/10 text-destructive",
    },
    {
      id: "today" as DailyCategoryTab,
      label: "Prontos Hoje",
      count: counts.ready_today,
      icon: <Zap className="size-4 text-emerald-500" />,
      badgeColor: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    },
    {
      id: "new" as DailyCategoryTab,
      label: "Novos Contatos",
      count: counts.new_contacts,
      icon: <Sparkles className="size-4 text-sky-500" />,
      badgeColor: "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    },
    {
      id: "paused" as DailyCategoryTab,
      label: "Pausados",
      count: counts.paused,
      icon: <Pause className="size-4 text-amber-500" />,
      badgeColor: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    },
    {
      id: "replied" as DailyCategoryTab,
      label: "Respostas pendentes",
      count: counts.replied_recently,
      icon: <MessageSquare className="size-4 text-primary" />,
      badgeColor: "border-primary/30 bg-primary/10 text-primary",
    },
    {
      id: "upcoming" as DailyCategoryTab,
      label: "Próximos",
      count: counts.upcoming,
      icon: <Clock className="size-4 text-muted-foreground" />,
      badgeColor: "border-muted bg-muted text-muted-foreground",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((c) => {
        const isSelected = selectedCategory === c.id;
        return (
          <button
            key={c.id}
            onClick={() => onSelectCategory(c.id)}
            className={`flex flex-col justify-between rounded-xl border p-3.5 text-left transition-all hover:shadow-sm ${
              isSelected
                ? "border-primary bg-primary/5 ring-1 ring-primary shadow-xs"
                : "border-border bg-card"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">{c.label}</span>
              {c.icon}
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold tracking-tight text-foreground">{c.count}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
