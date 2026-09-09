import { useState } from "react";
import {
  AlertTriangle,
  Play,
  Pause,
  MessageSquareReply,
  XCircle,
  Loader2,
  ListOrdered,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { SequenceStatusBadge } from "./SequenceStatusBadge";
import { SequenceTimeline } from "./SequenceTimeline";
import { RescheduleStepDialog } from "./RescheduleStepDialog";
import { StopSequenceDialog } from "./StopSequenceDialog";
import { useOutreachSequence } from "./hooks/useOutreachSequence";
import { useMarkSequenceStepSent } from "./hooks/useMarkSequenceStepSent";
import { usePauseSequence } from "./hooks/usePauseSequence";
import { useResumeSequence } from "./hooks/useResumeSequence";
import type { SequenceStep } from "./types";

interface SequencePanelProps {
  sequenceId?: number;
  packId?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadName?: string;
  leadPhone?: string;
  leadWhatsappLink?: string;
}

export function SequencePanel({
  sequenceId,
  packId,
  open,
  onOpenChange,
  leadName = "Lead",
  leadPhone,
  leadWhatsappLink,
}: SequencePanelProps) {
  const { data: sequence, isLoading, error } = useOutreachSequence({ sequenceId, packId });

  const markSentMutation = useMarkSequenceStepSent();
  const pauseMutation = usePauseSequence();
  const resumeMutation = useResumeSequence();

  const [rescheduleStep, setRescheduleStep] = useState<SequenceStep | null>(null);
  const [isRescheduleOpen, setIsRescheduleOpen] = useState(false);

  const [isStopOpen, setIsStopOpen] = useState(false);
  const [stopReason, setStopReason] = useState<string>("replied");

  const handleMarkSent = (stepId: number) => {
    markSentMutation.mutate({ stepId });
  };

  const handleSkip = (stepId: number) => {
    // Calling mark-sent or skip service
    import("@/services/outreach").then(({ pularEtapaSequencia }) => {
      pularEtapaSequencia(stepId).then(() => {
        // invalidate handled by queryClient if needed
      });
    });
  };

  const handleOpenReschedule = (step: SequenceStep) => {
    setRescheduleStep(step);
    setIsRescheduleOpen(true);
  };

  const handlePause = () => {
    if (sequence) pauseMutation.mutate(sequence.id);
  };

  const handleResume = () => {
    if (sequence) resumeMutation.mutate(sequence.id);
  };

  const handleOpenStop = (reason: string) => {
    setStopReason(reason);
    setIsStopOpen(true);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
              <div className="flex items-center gap-2">
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <ListOrdered className="size-5" />
                </div>
                <div>
                  <DialogTitle className="text-base font-semibold">
                    Régua de Abordagem — {leadName}
                  </DialogTitle>
                  <DialogDescription className="text-xs">
                    {sequence
                      ? `Sequência #${sequence.id} • Versão ${sequence.conversion_pack_version} do pacote`
                      : "Carregando régua..."}
                  </DialogDescription>
                </div>
              </div>
              {sequence && <SequenceStatusBadge status={sequence.status} />}
            </div>
          </DialogHeader>

          {/* Loading state */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Carregando régua de abordagem...</p>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="py-8 text-center text-sm text-destructive">
              {error.message || "Erro ao carregar detalhes da sequência."}
            </div>
          )}

          {sequence && (
            <div className="space-y-5 pt-2">
              {/* Outdated Version Warning Banner */}
              {sequence.version_outdated && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-700 dark:text-amber-300 space-y-1">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertTriangle className="size-4 text-amber-600" />
                    <span>Esta sequência usa a versão {sequence.conversion_pack_version} do pacote</span>
                  </div>
                  <p className="pl-6 text-muted-foreground">
                    O Pacote de Conversão atual foi alterado posteriormente e retornou a draft. A sequência ativa continua usando o snapshot aprovado originalmente.
                  </p>
                </div>
              )}

              {/* General Sequence Control Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-muted/20 p-3">
                <span className="text-xs font-semibold text-foreground">Ações da sequência:</span>
                <div className="flex flex-wrap items-center gap-2">
                  {sequence.status === "active" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePause}
                      disabled={pauseMutation.isPending}
                      className="h-8 text-xs gap-1.5"
                    >
                      <Pause className="size-3.5" />
                      <span>Pausar</span>
                    </Button>
                  )}

                  {sequence.status === "paused" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleResume}
                      disabled={resumeMutation.isPending}
                      className="h-8 text-xs gap-1.5 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                    >
                      <Play className="size-3.5" />
                      <span>Retomar</span>
                    </Button>
                  )}

                  {(sequence.status === "active" || sequence.status === "paused") && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenStop("replied")}
                        className="h-8 text-xs gap-1.5 text-sky-600 dark:text-sky-400 border-sky-500/30 hover:bg-sky-500/10"
                      >
                        <MessageSquareReply className="size-3.5" />
                        <span>Registrar resposta</span>
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenStop("manual")}
                        className="h-8 text-xs gap-1 text-destructive hover:bg-destructive/10"
                      >
                        <XCircle className="size-3.5" />
                        <span>Cancelar</span>
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Steps Vertical Timeline */}
              <SequenceTimeline
                steps={sequence.steps}
                leadName={leadName}
                leadPhone={leadPhone}
                leadWhatsappLink={leadWhatsappLink}
                isSequenceActive={sequence.status === "active"}
                onMarkSent={handleMarkSent}
                onSkip={handleSkip}
                onOpenReschedule={handleOpenReschedule}
                isMarkingSent={markSentMutation.isPending}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Sub-Dialogs */}
      <RescheduleStepDialog
        step={rescheduleStep}
        open={isRescheduleOpen}
        onOpenChange={setIsRescheduleOpen}
      />

      <StopSequenceDialog
        sequenceId={sequence?.id || null}
        open={isStopOpen}
        onOpenChange={setIsStopOpen}
        defaultReason={stopReason}
      />
    </>
  );
}
