import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { QueueCounts, QueueStatusTab } from "./types";

interface OutreachQueueTabsProps {
  activeTab: QueueStatusTab;
  onTabChange: (tab: QueueStatusTab) => void;
  counts?: QueueCounts;
}

const TABS_CONFIG: Array<{ id: QueueStatusTab; label: string; countKey: keyof QueueCounts }> = [
  { id: "not_generated", label: "Para preparar", countKey: "not_generated" },
  { id: "draft", label: "Em revisão", countKey: "draft" },
  { id: "approved", label: "Aprovados", countKey: "approved" },
  { id: "archived", label: "Arquivados", countKey: "archived" },
];

export function OutreachQueueTabs({ activeTab, onTabChange, counts }: OutreachQueueTabsProps) {
  return (
    <div className="flex border-b border-border">
      <nav className="-mb-px flex space-x-4 sm:space-x-8 overflow-x-auto" aria-label="Tabs">
        {TABS_CONFIG.map((tab) => {
          const isActive = activeTab === tab.id;
          const count = counts ? counts[tab.countKey] : 0;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                "inline-flex items-center gap-2 whitespace-nowrap border-b-2 py-3 px-1 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:border-muted-foreground/30 hover:text-foreground"
              )}
            >
              <span>{tab.label}</span>
              <Badge
                variant={isActive ? "default" : "secondary"}
                className={cn(
                  "ml-1 text-xs font-semibold px-2 py-0.5",
                  isActive ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}
              >
                {count}
              </Badge>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
