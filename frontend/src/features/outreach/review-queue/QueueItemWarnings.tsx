import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { WarningCode } from "./types";

interface QueueItemWarningsProps {
  warnings: WarningCode[];
}

const WARNING_CONFIG: Record<
  WarningCode,
  { label: string; description: string; variant: "warning" | "destructive" | "secondary" }
> = {
  missing_contact_channel: {
    label: "Sem canal de contato",
    description: "Lead sem telefone, WhatsApp ou e-mail cadastrado.",
    variant: "destructive",
  },
  missing_whatsapp: {
    label: "WhatsApp indisponível",
    description: "Sem número de WhatsApp válido para envio direto.",
    variant: "warning",
  },
  missing_landing_page: {
    label: "Sem protótipo",
    description: "Nenhuma Landing Page foi vinculada a este lead.",
    variant: "secondary",
  },
  landing_page_not_published: {
    label: "Protótipo ainda não publicado",
    description: "A LP está em rascunho. O pré-visualizador funcionará, mas não o link público.",
    variant: "warning",
  },
  empty_initial_message: {
    label: "Mensagem inicial vazia",
    description: "Não é possível aprovar pacotes sem mensagem inicial.",
    variant: "destructive",
  },
  low_confidence: {
    label: "Baixa confiança",
    description: "A estratégia comercial foi gerada com base em evidências limitadas.",
    variant: "warning",
  },
  prototype_without_public_url: {
    label: "Sem URL pública",
    description: "A LP está publicada mas ainda não tem URL pública atribuída.",
    variant: "warning",
  },
  pack_archived: {
    label: "Arquivado",
    description: "Este item foi arquivado e retirado da fila ativa.",
    variant: "secondary",
  },
};

export function QueueItemWarnings({ warnings }: QueueItemWarningsProps) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {warnings.map((code) => {
        const config = WARNING_CONFIG[code];
        if (!config) return null;

        const badgeClass =
          config.variant === "destructive"
            ? "border-destructive/30 bg-destructive/10 text-destructive dark:bg-destructive/20"
            : config.variant === "warning"
            ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
            : "border-muted-foreground/30 bg-muted text-muted-foreground";

        return (
          <Tooltip key={code}>
            <TooltipTrigger asChild>
              <Badge variant="outline" className={`cursor-help text-xs font-normal gap-1 ${badgeClass}`}>
                <AlertTriangle className="size-3 shrink-0" />
                <span>{config.label}</span>
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs text-xs">
              {config.description}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
