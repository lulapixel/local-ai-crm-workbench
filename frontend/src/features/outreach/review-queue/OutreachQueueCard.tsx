import { useState } from "react";
import {
  MoreHorizontal,
  Edit2,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Copy,
  Archive,
  Star,
  MapPin,
  Building2,
  PlayCircle,
  ListOrdered,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { QueueItemWarnings } from "./QueueItemWarnings";
import { QuickMessageEditor } from "./QuickMessageEditor";
import { SequencePanel } from "../sequences/SequencePanel";
import { useStartSequence } from "../sequences/hooks/useStartSequence";
import type { QueueItem } from "./types";

interface OutreachQueueCardProps {
  item: QueueItem;
  isSelected: boolean;
  onToggleSelect: () => void;
  onApprove: (packId: number) => void;
  onArchive: (packId: number) => void;
  onOpenRegenerate: (item: QueueItem) => void;
  onOpenCopyModal: (item: QueueItem) => void;
  onOpenWhatsApp: (item: QueueItem) => void;
  onOpenPrototype: (item: QueueItem) => void;
}

export function OutreachQueueCard({
  item,
  isSelected,
  onToggleSelect,
  onApprove,
  onArchive,
  onOpenRegenerate,
  onOpenCopyModal,
  onOpenWhatsApp,
  onOpenPrototype,
}: OutreachQueueCardProps) {
  const [isEditingInline, setIsEditingInline] = useState(false);
  const [isSequencePanelOpen, setIsSequencePanelOpen] = useState(false);

  const startSequenceMutation = useStartSequence();

  const { lead, conversion_pack: pack, warnings, sequence } = item;

  const handleStartSequence = () => {
    if (!pack) return;
    startSequenceMutation.mutate({ packId: pack.id });
  };

  return (
    <div
      className={`group relative rounded-xl border bg-card p-4 transition-all hover:shadow-md ${
        isSelected ? "border-primary bg-primary/5 ring-1 ring-primary" : "border-border"
      }`}
    >
      {/* Top Header Row */}
      <div className="flex items-start justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={isSelected}
            onCheckedChange={onToggleSelect}
            className="mt-0.5"
            aria-label={`Selecionar ${lead.name}`}
          />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-foreground text-base leading-snug">{lead.name}</h3>
              {item.queue_status === "approved" && sequence && (
                <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs">
                  {sequence.status === "active" && "● Sequência Ativa"}
                  {sequence.status === "paused" && "⏸ Sequência Pausada"}
                  {sequence.status === "replied" && "💬 Cliente Respondeu"}
                  {sequence.status === "completed" && "✓ Sequência Concluída"}
                  {sequence.status === "cancelled" && "✕ Sequência Interrompida"}
                </Badge>
              )}
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {lead.niche && (
                <span className="flex items-center gap-1">
                  <Building2 className="size-3" />
                  {lead.niche}
                </span>
              )}
              {lead.city && (
                <span className="flex items-center gap-1">
                  <MapPin className="size-3" />
                  {lead.city}
                </span>
              )}
              {lead.rating > 0 && (
                <span className="flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400">
                  <Star className="size-3 fill-amber-400 text-amber-400" />
                  {lead.rating.toFixed(1)} ({lead.review_count})
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Lead Score & Warnings */}
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground">Score:</span>
            <Badge
              variant="outline"
              className={`font-bold ${
                lead.score >= 70
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : lead.score >= 50
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "border-muted bg-muted text-muted-foreground"
              }`}
            >
              {lead.score} pts
            </Badge>
          </div>
          <QueueItemWarnings warnings={warnings} />
        </div>
      </div>

      {/* Main Content Body */}
      <div className="mt-3 space-y-3">
        {/* Strategy Opportunity */}
        {pack?.strategy?.opportunity && (
          <div className="rounded-lg bg-muted/30 p-2.5 text-xs">
            <span className="font-semibold text-foreground">Oportunidade: </span>
            <span className="text-muted-foreground">{pack.strategy.opportunity}</span>
          </div>
        )}

        {/* Quick Message Editor / Display */}
        {pack && (
          <QuickMessageEditor
            item={item}
            isEditing={isEditingInline}
            onCancel={() => setIsEditingInline(false)}
            onSuccess={() => setIsEditingInline(false)}
          />
        )}
      </div>

      {/* Sequence Banner on Approved Cards */}
      {item.queue_status === "approved" && sequence && (
        <div className="mt-3 rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ListOrdered className="size-4 text-primary" />
            <span className="font-medium">
              {sequence.status === "active" && sequence.next_step
                ? `Próxima ação: ${sequence.next_step.objective || `Etapa #${sequence.next_step.step_order}`}`
                : sequence.status === "paused"
                ? "Sequência pausada pelo operador"
                : sequence.status === "replied"
                ? "Sequência encerrada após resposta do cliente"
                : "Régua cadastrada"}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSequencePanelOpen(true)}
            className="h-7 text-[11px] gap-1 border-primary/30"
          >
            Ver sequência
          </Button>
        </div>
      )}

      {/* Action Buttons Toolbar */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {pack && item.queue_status === "draft" && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditingInline(!isEditingInline)}
                className="h-8 gap-1.5 text-xs"
              >
                <Edit2 className="size-3.5" />
                <span>Editar</span>
              </Button>

              <Button
                size="sm"
                onClick={() => onApprove(pack.id)}
                disabled={warnings.includes("empty_initial_message")}
                className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <CheckCircle2 className="size-3.5" />
                <span>Aprovar</span>
              </Button>
            </>
          )}

          {/* Start Sequence button on Approved packs without active sequence */}
          {pack && item.queue_status === "approved" && !sequence && (
            <Button
              size="sm"
              onClick={handleStartSequence}
              disabled={startSequenceMutation.isPending}
              className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
            >
              <PlayCircle className="size-3.5" />
              <span>Iniciar sequência</span>
            </Button>
          )}

          {/* View Sequence button on Approved packs with active sequence */}
          {pack && item.queue_status === "approved" && sequence && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsSequencePanelOpen(true)}
              className="h-8 gap-1.5 text-xs border-primary/40 text-primary hover:bg-primary/10"
            >
              <ListOrdered className="size-3.5" />
              <span>Ver sequência</span>
            </Button>
          )}

          {/* Prototype Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenPrototype(item)}
            className="h-8 gap-1.5 text-xs"
          >
            <ExternalLink className="size-3.5" />
            <span>Protótipo</span>
          </Button>

          {/* WhatsApp Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenWhatsApp(item)}
            disabled={warnings.includes("missing_whatsapp")}
            className="h-8 gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
          >
            <MessageSquare className="size-3.5" />
            <span>WhatsApp</span>
          </Button>
        </div>

        {/* Dropdown Menu for Secondary Actions */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-8 text-muted-foreground">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {pack && (
              <>
                <DropdownMenuItem onClick={() => onOpenRegenerate(item)}>
                  <Sparkles className="mr-2 size-4 text-amber-500" />
                  <span>Regenerar seções</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onOpenCopyModal(item)}>
                  <Copy className="mr-2 size-4" />
                  <span>Copiar mensagem</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}

            {pack && item.queue_status !== "archived" && (
              <DropdownMenuItem
                onClick={() => onArchive(pack.id)}
                className="text-destructive focus:text-destructive"
              >
                <Archive className="mr-2 size-4" />
                <span>Arquivar item</span>
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Sequence Panel Modal */}
      {pack && (
        <SequencePanel
          packId={pack.id}
          sequenceId={sequence?.id}
          open={isSequencePanelOpen}
          onOpenChange={setIsSequencePanelOpen}
          leadName={lead.name}
          leadPhone={lead.phone}
          leadWhatsappLink={lead.whatsapp_link}
        />
      )}
    </div>
  );
}
