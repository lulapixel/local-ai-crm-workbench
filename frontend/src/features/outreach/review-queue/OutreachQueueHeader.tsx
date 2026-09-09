import { RefreshCw, Sparkles, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { QueueCounts } from "./types";

interface OutreachQueueHeaderProps {
  counts?: QueueCounts;
  selectedCount: number;
  onRefresh: () => void;
  onGenerateSelected: () => void;
  isGenerating?: boolean;
}

export function OutreachQueueHeader({
  counts,
  selectedCount,
  onRefresh,
  onGenerateSelected,
  isGenerating,
}: OutreachQueueHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Send className="size-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Central de Abordagens
            </h1>
            <p className="text-xs text-muted-foreground">
              Fila operacional para transformar leads qualificados em abordagens comerciais de alta conversão.
            </p>
          </div>
        </div>

        {counts && (
          <div className="flex items-center gap-2 pt-2 text-xs">
            <Badge variant="outline" className="gap-1 border-muted bg-muted/40 font-normal">
              <span className="font-semibold text-foreground">{counts.not_generated}</span> para preparar
            </Badge>
            <span className="text-muted-foreground">•</span>
            <Badge variant="outline" className="gap-1 border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 font-normal">
              <span className="font-semibold">{counts.draft}</span> em revisão
            </Badge>
            <span className="text-muted-foreground">•</span>
            <Badge variant="outline" className="gap-1 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-normal">
              <span className="font-semibold">{counts.approved}</span> aprovados
            </Badge>
            {counts.archived > 0 && (
              <>
                <span className="text-muted-foreground">•</span>
                <Badge variant="outline" className="gap-1 border-muted text-muted-foreground font-normal">
                  <span className="font-semibold">{counts.archived}</span> arquivados
                </Badge>
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onRefresh} className="gap-1.5">
          <RefreshCw className="size-3.5" />
          <span>Atualizar fila</span>
        </Button>

        {selectedCount > 0 && (
          <Button size="sm" onClick={onGenerateSelected} disabled={isGenerating} className="gap-1.5 bg-primary">
            <Sparkles className="size-3.5" />
            <span>Gerar selecionados ({selectedCount})</span>
          </Button>
        )}
      </div>
    </div>
  );
}
