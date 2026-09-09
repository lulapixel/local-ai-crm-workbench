import { MessageSquare, CheckCircle2, FastForward, Calendar, Copy, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { SequenceStatusBadge } from "./SequenceStatusBadge";
import { saudacaoAtual } from "@/lib/saudacao";
import { safeWhatsAppUrl } from "@/lib/safeExternalUrl";
import type { SequenceStep } from "./types";

interface SequenceStepCardProps {
  step: SequenceStep;
  leadName?: string;
  leadPhone?: string;
  leadWhatsappLink?: string;
  isSequenceActive: boolean;
  onMarkSent: (stepId: number) => void;
  onSkip: (stepId: number) => void;
  onOpenReschedule: (step: SequenceStep) => void;
  isMarkingSent?: boolean;
}

export function SequenceStepCard({
  step,
  leadPhone,
  leadWhatsappLink,
  isSequenceActive,
  onMarkSent,
  onSkip,
  onOpenReschedule,
  isMarkingSent,
}: SequenceStepCardProps) {
  const [copiado, setCopiado] = useState(false);

  const stepTitle =
    step.step_order === 0
      ? "Abordagem inicial"
      : `Follow-up ${step.step_order} (+${step.delay_days} dias)`;

  const formatarData = (isoStr?: string | null) => {
    if (!isoStr) return "";
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  };

  const handleOpenWhatsApp = () => {
    let phoneClean = (leadPhone || "").replace(/\D/g, "");
    if (!phoneClean && leadWhatsappLink) {
      const match = leadWhatsappLink.match(/55\d+/);
      if (match) phoneClean = match[0];
    }

    if (!phoneClean) {
      toast.error("Número de WhatsApp indisponível para este lead.");
      return;
    }

    if (!phoneClean.startsWith("55") && phoneClean.length <= 11) {
      phoneClean = `55${phoneClean}`;
    }

    const rawMsg = step.message;
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

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-xs transition-all space-y-3">
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2.5">
        <div className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
            {step.step_order}
          </span>
          <h4 className="text-sm font-semibold text-foreground">{stepTitle}</h4>
        </div>
        <SequenceStatusBadge status={step.status} type="step" />
      </div>

      {/* Objective & Dates */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        {step.objective && <span className="font-medium text-foreground">{step.objective}</span>}
        {step.status === "sent" && step.sent_at && (
          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
            Enviado em {formatarData(step.sent_at)}
          </span>
        )}
        {step.status === "skipped" && step.skipped_at && (
          <span className="text-muted-foreground italic">Pulado em {formatarData(step.skipped_at)}</span>
        )}
        {step.status === "pending" && step.scheduled_for && (
          <span>Programado para {formatarData(step.scheduled_for)}</span>
        )}
        {step.status === "ready" && (
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
            Vencido/Pronto para disparo
          </span>
        )}
      </div>

      {/* Message Snapshot Display */}
      <div className="rounded-lg bg-muted/40 p-3 text-xs leading-relaxed font-mono border border-border/50 text-foreground">
        {step.message}
      </div>

      {/* Action Buttons Toolbar */}
      {isSequenceActive && (step.status === "ready" || step.status === "pending") && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t">
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenWhatsApp}
              className="h-8 gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
            >
              <MessageSquare className="size-3.5" />
              <span>Abrir WhatsApp</span>
            </Button>

            <Button variant="ghost" size="sm" onClick={handleCopyText} className="h-8 text-xs gap-1">
              {copiado ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              <span>{copiado ? "Copiado" : "Copiar"}</span>
            </Button>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenReschedule(step)}
              className="h-8 text-xs text-muted-foreground gap-1"
            >
              <Calendar className="size-3.5" />
              <span>Reagendar</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => onSkip(step.id)}
              className="h-8 text-xs text-muted-foreground gap-1"
            >
              <FastForward className="size-3.5" />
              <span>Pular</span>
            </Button>

            {step.status === "ready" && (
              <Button
                size="sm"
                onClick={() => onMarkSent(step.id)}
                disabled={isMarkingSent}
                className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
              >
                <CheckCircle2 className="size-3.5" />
                <span>Marcar enviada</span>
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
