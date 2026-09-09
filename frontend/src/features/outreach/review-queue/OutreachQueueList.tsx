import { Loader2, AlertCircle, Inbox, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { OutreachQueueCard } from "./OutreachQueueCard";
import type { QueueItem, QueuePagination } from "./types";

interface OutreachQueueListProps {
  items: QueueItem[];
  pagination?: QueuePagination;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  selectedPlaceIds: string[];
  onToggleSelectAll: () => void;
  onToggleSelectOne: (placeId: string) => void;
  onPageChange: (newPage: number) => void;
  onApprove: (packId: number) => void;
  onArchive: (packId: number) => void;
  onOpenRegenerate: (item: QueueItem) => void;
  onOpenCopyModal: (item: QueueItem) => void;
  onOpenWhatsApp: (item: QueueItem) => void;
  onOpenPrototype: (item: QueueItem) => void;
  onRefetch: () => void;
}

export function OutreachQueueList({
  items,
  pagination,
  isLoading,
  isError,
  error,
  selectedPlaceIds,
  onToggleSelectAll,
  onToggleSelectOne,
  onPageChange,
  onApprove,
  onArchive,
  onOpenRegenerate,
  onOpenCopyModal,
  onOpenWhatsApp,
  onOpenPrototype,
  onRefetch,
}: OutreachQueueListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
        <Loader2 className="size-8 animate-spin text-primary" />
        <span className="text-sm font-medium">Carregando fila de abordagens...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-destructive gap-3 rounded-lg border border-destructive/20 bg-destructive/5 p-6">
        <AlertCircle className="size-8" />
        <p className="text-sm font-medium">{error?.message || "Erro ao carregar fila de abordagens."}</p>
        <Button variant="outline" size="sm" onClick={onRefetch} className="mt-2">
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3 rounded-lg border border-dashed p-8 text-center bg-card">
        <Inbox className="size-10 text-muted-foreground/60" />
        <h4 className="text-base font-semibold text-foreground">Nenhum item na fila</h4>
        <p className="max-w-md text-xs">
          Nenhum lead ou pacote corresponde aos filtros selecionados nesta guia. Tente ajustar os filtros acima.
        </p>
      </div>
    );
  }

  const allSelectedOnPage = items.length > 0 && items.every((i) => selectedPlaceIds.includes(i.lead.place_id));

  return (
    <div className="space-y-4">
      {/* Select All Page Bar */}
      <div className="flex items-center justify-between px-1 text-xs text-muted-foreground">
        <label className="flex items-center gap-2 font-medium cursor-pointer">
          <Checkbox
            checked={allSelectedOnPage}
            onCheckedChange={onToggleSelectAll}
            className="size-4"
          />
          <span>Selecionar todos os {items.length} itens desta página</span>
        </label>

        {pagination && (
          <span>
            Exibindo página {pagination.page} de {pagination.pages} ({pagination.total} total)
          </span>
        )}
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 gap-4">
        {items.map((item) => (
          <OutreachQueueCard
            key={item.lead.place_id}
            item={item}
            isSelected={selectedPlaceIds.includes(item.lead.place_id)}
            onToggleSelect={() => onToggleSelectOne(item.lead.place_id)}
            onApprove={onApprove}
            onArchive={onArchive}
            onOpenRegenerate={onOpenRegenerate}
            onOpenCopyModal={onOpenCopyModal}
            onOpenWhatsApp={onOpenWhatsApp}
            onOpenPrototype={onOpenPrototype}
          />
        ))}
      </div>

      {/* Pagination Controls */}
      {pagination && pagination.pages > 1 && (
        <div className="flex items-center justify-between border-t pt-4 text-xs">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={pagination.page <= 1}
            className="gap-1"
          >
            <ChevronLeft className="size-4" />
            Anterior
          </Button>

          <span className="text-muted-foreground font-medium">
            Página {pagination.page} de {pagination.pages}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={pagination.page >= pagination.pages}
            className="gap-1"
          >
            Próxima
            <ChevronRight className="size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
