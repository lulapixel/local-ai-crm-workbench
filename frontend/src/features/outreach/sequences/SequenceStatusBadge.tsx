import { Badge } from "@/components/ui/badge";
import type { SequenceStatus, StepStatus } from "./types";

interface SequenceStatusBadgeProps {
  status: SequenceStatus | StepStatus;
  type?: "sequence" | "step";
}

export function SequenceStatusBadge({ status, type = "sequence" }: SequenceStatusBadgeProps) {
  if (type === "sequence") {
    switch (status) {
      case "active":
        return (
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium text-xs">
            ● Sequência ativa
          </Badge>
        );
      case "paused":
        return (
          <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 font-medium text-xs">
            ⏸ Sequência pausada
          </Badge>
        );
      case "replied":
        return (
          <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 font-medium text-xs">
            💬 Cliente respondeu
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium text-xs">
            ✓ Concluída
          </Badge>
        );
      case "cancelled":
        return (
          <Badge variant="outline" className="border-muted bg-muted text-muted-foreground font-medium text-xs">
            ✕ Interrompida
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  }

  // Step Status Badges
  switch (status) {
    case "ready":
      return (
        <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold text-[11px] animate-pulse">
          ⚡ Pronto para envio
        </Badge>
      );
    case "sent":
      return (
        <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium text-[11px]">
          ✓ Enviado
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 font-medium text-[11px]">
          🕒 Agendado
        </Badge>
      );
    case "skipped":
      return (
        <Badge variant="outline" className="border-muted bg-muted text-muted-foreground font-medium text-[11px]">
          ↷ Pulado
        </Badge>
      );
    case "cancelled":
      return (
        <Badge variant="outline" className="border-muted bg-muted text-muted-foreground font-medium text-[11px]">
          ✕ Cancelado
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}
