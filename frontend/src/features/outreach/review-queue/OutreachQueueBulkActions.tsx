import { Sparkles, CheckCheck, Archive, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { QueueStatusTab } from "./types";

interface OutreachQueueBulkActionsProps {
  selectedCount: number;
  activeTab: QueueStatusTab;
  onClearSelection: () => void;
  onBulkGenerate: () => void;
  onBulkApprove: () => void;
  onBulkArchive: () => void;
  isGenerating?: boolean;
  isApproving?: boolean;
}

export function OutreachQueueBulkActions({
  selectedCount,
  activeTab,
  onClearSelection,
  onBulkGenerate,
  onBulkApprove,
  onBulkArchive,
  isGenerating,
  isApproving,
}: OutreachQueueBulkActionsProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-xl border border-primary/20 bg-background/95 p-3 shadow-2xl backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:p-4">
      <div className="flex items-center gap-3 sm:gap-6">
        <div className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {selectedCount}
          </span>
          <span className="text-sm font-semibold text-foreground">selecionado(s)</span>
          <Button variant="ghost" size="icon" onClick={onClearSelection} className="size-6 text-muted-foreground hover:text-foreground">
            <X className="size-3.5" />
          </Button>
        </div>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-2">
          {activeTab === "not_generated" && (
            <Button size="sm" onClick={onBulkGenerate} disabled={isGenerating} className="gap-1.5 bg-primary">
              <Sparkles className="size-3.5" />
              <span>Gerar pacotes ({selectedCount})</span>
            </Button>
          )}

          {activeTab === "draft" && (
            <Button size="sm" onClick={onBulkApprove} disabled={isApproving} className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white">
              <CheckCheck className="size-3.5" />
              <span>Aprovar selecionados</span>
            </Button>
          )}

          {(activeTab === "draft" || activeTab === "approved") && (
            <Button variant="outline" size="sm" onClick={onBulkArchive} className="gap-1.5 text-muted-foreground hover:text-foreground">
              <Archive className="size-3.5" />
              <span>Arquivar</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
