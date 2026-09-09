import { CheckCircle2, Sparkles, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DailyActionCard } from "./DailyActionCard";
import type { DailyActionItem } from "./types";

interface DailyActionListProps {
  items: DailyActionItem[];
  isLoading: boolean;
  onRefresh?: () => void;
  onClearFilters?: () => void;
}

export function DailyActionList({ items, isLoading, onRefresh, onClearFilters }: DailyActionListProps) {
  if (isLoading) {
    return (
      <div className="space-y-4 py-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 rounded-xl border border-border bg-card p-5 animate-pulse" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 py-16 px-4 text-center space-y-4">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-7" />
        </div>
        <div className="space-y-1 max-w-md">
          <h3 className="text-lg font-bold text-foreground">Tudo em dia por hoje! 🎉</h3>
          <p className="text-xs text-muted-foreground">
            Não há tarefas de prospecção pendentes para os filtros selecionados. Você pode iniciar novas abordagens na Central de Abordagens.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-2">
          {onClearFilters && (
            <Button variant="outline" size="sm" onClick={onClearFilters} className="h-8 text-xs gap-1.5">
              <Filter className="size-3.5" />
              <span>Limpar filtros</span>
            </Button>
          )}
          {onRefresh && (
            <Button size="sm" onClick={onRefresh} className="h-8 text-xs gap-1.5">
              <Sparkles className="size-3.5" />
              <span>Atualizar lista</span>
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item, idx) => (
        <DailyActionCard key={`${item.lead.place_id}-${idx}`} item={item} onActionSuccess={onRefresh} />
      ))}
    </div>
  );
}
