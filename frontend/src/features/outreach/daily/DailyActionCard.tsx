import { useState } from "react";
import {
  MessageSquare,
  CheckCircle2,
  FastForward,
  PlayCircle,
  ExternalLink,
  ListOrdered,
  MessageSquareReply,
  Copy,
  Check,
  Building2,
  MapPin,
  Star,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { QueueItemWarnings } from "../review-queue/QueueItemWarnings";
import { SequencePanel } from "../sequences/SequencePanel";
import { QuickRescheduleMenu } from "./QuickRescheduleMenu";
import { RegisterResponseDialog } from "./RegisterResponseDialog";
import { useMarkSequenceStepSent } from "../sequences/hooks/useMarkSequenceStepSent";
import { saudacaoAtual } from "@/lib/saudacao";
import { safeExternalUrl, safeWhatsAppUrl } from "@/lib/safeExternalUrl";
import type { DailyActionItem } from "./types";

interface DailyActionCardProps {
  item: DailyActionItem;
  onActionSuccess?: () => void;
}

export function DailyActionCard({ item, onActionSuccess }: DailyActionCardProps) {
  const [copiado, setCopiado] = useState(false);
  const [isSequencePanelOpen, setIsSequencePanelOpen] = useState(false);
  const [isResponseDialogOpen, setIsResponseDialogOpen] = useState(false);

  const markSentMutation = useMarkSequenceStepSent();

  const { lead, sequence, step, landing_page: lp, warnings, priority } = item;

  const priorityLabel =
    priority === "overdue"
      ? "🚨 Follow-up Atrasado"
      : priority === "ready_today"
      ? "⚡ Pronto Hoje"
      : priority === "new_contacts"
      ? "✨ Novo Contato Aprovado"
      : priority === "paused"
      ? "⏸ Sequência Pausada"
      : priority === "upcoming"
      ? "🕒 Próximo Agendamento"
      : "💬 Cliente Respondeu";

  const priorityColor =
    priority === "overdue"
      ? "border-destructive/30 bg-destructive/10 text-destructive font-semibold"
      : priority === "ready_today"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold"
      : priority === "new_contacts"
      ? "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 font-semibold"
      : "border-muted bg-muted text-muted-foreground";

  const handleOpenWhatsApp = () => {
    let phoneClean = (lead.phone || "").replace(/\D/g, "");
    if (!phoneClean && lead.whatsapp_link) {
      const match = lead.whatsapp_link.match(/55\d+/);
      if (match) phoneClean = match[0];
    }

    if (!phoneClean) {
      toast.error("Número de WhatsApp indisponível para este lead.");
      return;
    }

    if (!phoneClean.startsWith("55") && phoneClean.length <= 11) {
      phoneClean = `55${phoneClean}`;
    }

    const rawMsg = step.message || "";
    const saudacao = saudacaoAtual();
    const msgComSaudacao = `${saudacao}! ${rawMsg.replace(/^(Oi|Olá|Bom dia|Boa tarde|Boa noite)[!.,]?\s*/i, "")}`;

    const waUrl = safeWhatsAppUrl(`https://wa.me/${phoneClean}`, msgComSaudacao);
    if (waUrl) window.open(waUrl, "_blank", "noopener,noreferrer");
    else toast.error("Número de WhatsApp inválido para este lead.");
  };

  const handleCopyText = () => {
    const saudacao = saudacaoAtual();
    const texto = `${saudacao}! ${step.message.replace(/^(Oi|Olá|Bom dia|Boa tarde|Boa noite)[!.,]?\s*/i, "")}`;
    navigator.clipboard.writeText(texto);
    setCopiado(true);
    toast.success("Texto copiado!");
    setTimeout(() => setCopiado(false), 2000);
  };

  const handleMarkSent = () => {
    if (!step.id) return;
    markSentMutation.mutate(
      { stepId: step.id },
      {
        onSuccess: () => {
          if (onActionSuccess) onActionSuccess();
        },
      }
    );
  };


  const handleSkip = () => {
    if (!step.id) return;
    import("@/services/outreach").then(({ pularEtapaSequencia }) => {
      pularEtapaSequencia(step.id).then(() => {
        toast.info("Etapa pulada.");
        if (onActionSuccess) onActionSuccess();
      });
    });
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs transition-all space-y-4 hover:shadow-md">
      {/* Header Row */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-foreground text-base leading-snug">{lead.name}</h3>
            <Badge variant="outline" className={`text-xs ${priorityColor}`}>
              {priorityLabel}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
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

        <div className="flex flex-col items-end gap-1.5">
          <Badge
            variant="outline"
            className={`font-bold text-xs ${
              lead.score >= 70
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "border-muted bg-muted text-muted-foreground"
            }`}
          >
            Score {lead.score}
          </Badge>
          <QueueItemWarnings warnings={warnings} />
        </div>
      </div>

      {/* Objective & Message Snapshot OR Inbound Response Box */}
      {priority === "replied_recently" && item.conversation ? (
        <div className="space-y-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="font-semibold text-primary">
              💬 Resposta recebida do lead
            </span>
            {item.conversation.last_inbound_at && (
              <span className="text-[11px]">
                {new Date(item.conversation.last_inbound_at).toLocaleString("pt-BR", {
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>

          {item.conversation.last_inbound_content ? (
            <p className="font-medium text-foreground whitespace-pre-wrap">
              “{item.conversation.last_inbound_content}”
            </p>
          ) : (
            <p className="italic text-muted-foreground">(Sem conteúdo gravado)</p>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-primary/10">
            {item.conversation.last_inbound_classification && (
              <Badge variant="outline" className="text-[10px] bg-background">
                Classificação: {item.conversation.last_inbound_classification}
              </Badge>
            )}
            {item.conversation.next_action_note && (
              <span className="text-[11px] font-semibold text-foreground">
                Próxima ação: {item.conversation.next_action_note}
              </span>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-foreground uppercase tracking-wider text-[10px]">
              {step.objective || "Objetivo da etapa"}
            </span>
            {step.scheduled_for && (
              <span className="text-muted-foreground text-[11px]">
                Data: {new Date(step.scheduled_for).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>

          <div className="rounded-lg border bg-muted/40 p-3 text-xs leading-relaxed text-foreground font-mono">
            {step.message || <span className="italic text-muted-foreground">(Mensagem indisponível)</span>}
          </div>
        </div>
      )}

      {/* Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {/* WhatsApp Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenWhatsApp}
            disabled={warnings.includes("missing_whatsapp")}
            className="h-8 gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
          >
            <MessageSquare className="size-3.5" />
            <span>Abrir WhatsApp</span>
          </Button>

          {/* Copy Message */}
          <Button variant="ghost" size="sm" onClick={handleCopyText} className="h-8 text-xs gap-1">
            {copiado ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            <span>{copiado ? "Copiado" : "Copiar"}</span>
          </Button>

          {/* Prototype Link */}
          {lp && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const url = safeExternalUrl(lp.public_url || lp.preview_url, { allowRelative: true });
                if (url) window.open(url, "_blank", "noopener,noreferrer");
                else toast.error("O link do protótipo não é válido.");
              }}
              className="h-8 gap-1.5 text-xs"
            >
              <ExternalLink className="size-3.5" />
              <span>Protótipo</span>
            </Button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {/* Item sequence step actions */}
          {item.action_type === "sequence_step" && sequence && (
            <>
              <QuickRescheduleMenu step={step} />

              <Button
                variant="ghost"
                size="sm"
                onClick={handleSkip}
                className="h-8 text-xs text-muted-foreground gap-1"
              >
                <FastForward className="size-3.5" />
                <span>Pular</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsResponseDialogOpen(true)}
                className="h-8 text-xs text-sky-600 dark:text-sky-400 border-sky-500/30 gap-1"
              >
                <MessageSquareReply className="size-3.5" />
                <span>Resposta</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsSequencePanelOpen(true)}
                className="h-8 text-xs gap-1"
              >
                <ListOrdered className="size-3.5" />
                <span>Sequência</span>
              </Button>

              {(step.status === "ready" || priority === "overdue" || priority === "ready_today") && (
                <Button
                  size="sm"
                  onClick={handleMarkSent}
                  disabled={markSentMutation.isPending}
                  className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                >
                  <CheckCircle2 className="size-3.5" />
                  <span>Marcar enviada</span>
                </Button>
              )}
            </>
          )}

          {/* Item new contact actions */}
          {item.action_type === "new_contact" && (
            <Button
              size="sm"
              onClick={() => {
                // start sequence using pack id
                if (item.sequence?.id) {
                  setIsSequencePanelOpen(true);
                } else {
                  toast.info("Iniciando sequência no backend...");
                  // trigger start sequence
                }
              }}
              className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
            >
              <PlayCircle className="size-3.5" />
              <span>Iniciar sequência</span>
            </Button>
          )}
        </div>
      </div>

      {/* Sub-modals */}
      {sequence && (
        <SequencePanel
          sequenceId={sequence.id}
          open={isSequencePanelOpen}
          onOpenChange={setIsSequencePanelOpen}
          leadName={lead.name}
          leadPhone={lead.phone}
          leadWhatsappLink={lead.whatsapp_link}
        />
      )}

      {sequence && (
        <RegisterResponseDialog
          sequenceId={sequence.id}
          open={isResponseDialogOpen}
          onOpenChange={setIsResponseDialogOpen}
          onSuccess={onActionSuccess}
        />
      )}
    </div>
  );
}
