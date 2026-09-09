import { ChevronLeft, ChevronRight, X, Play, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DailyActionCard } from "./DailyActionCard";
import type { DailyActionItem } from "./types";

interface DailyExecutionModeProps {
  items: DailyActionItem[];
  currentIndex: number;
  totalCount: number;
  completedCount: number;
  onNext: () => void;
  onPrevious: () => void;
  onExit: () => void;
  onActionSuccess?: () => void;
}

export function DailyExecutionMode({
  items,
  currentIndex,
  totalCount,
  completedCount,
  onNext,
  onPrevious,
  onExit,
  onActionSuccess,
}: DailyExecutionModeProps) {
  const currentItem = items[currentIndex];

  if (!currentItem) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border bg-card p-12 text-center space-y-4">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500">
          <Trophy className="size-7" />
        </div>
        <h3 className="text-xl font-bold text-foreground">Sessão concluída!</h3>
        <p className="text-xs text-muted-foreground max-w-sm">
          Você passou por todas as ações programadas nesta sessão. Parabéns pelo foco!
        </p>
        <Button onClick={onExit} size="sm">
          Voltar ao Cockpit
        </Button>
      </div>
    );
  }

  const progressoPercent = Math.round(((currentIndex + 1) / totalCount) * 100);

  return (
    <div className="space-y-4 rounded-2xl border border-primary/30 bg-card p-4 sm:p-6 shadow-md">
      {/* Session Progress Bar Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xs">
            <Play className="size-4 fill-primary-foreground" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground">Modo Sessão de Prospecção</h3>
            <p className="text-xs text-muted-foreground">
              Ação {currentIndex + 1} de {totalCount} • {completedCount} concluídas nesta sessão
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onPrevious} disabled={currentIndex === 0} className="h-8 text-xs gap-1">
            <ChevronLeft className="size-4" />
            <span className="hidden sm:inline">Anterior</span>
          </Button>

          <Button variant="outline" size="sm" onClick={onNext} disabled={currentIndex >= totalCount - 1} className="h-8 text-xs gap-1">
            <span className="hidden sm:inline">Próxima</span>
            <ChevronRight className="size-4" />
          </Button>

          <Button variant="ghost" size="icon" onClick={onExit} className="size-8 text-muted-foreground">
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Visual Progress Line */}
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progressoPercent}%` }} />
      </div>

      {/* Active Focus Card */}
      <DailyActionCard item={currentItem} onActionSuccess={onActionSuccess} />
    </div>
  );
}
