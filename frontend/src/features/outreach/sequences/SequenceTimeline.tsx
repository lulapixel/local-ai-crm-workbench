import { SequenceStepCard } from "./SequenceStepCard";
import type { SequenceStep } from "./types";

interface SequenceTimelineProps {
  steps: SequenceStep[];
  leadName?: string;
  leadPhone?: string;
  leadWhatsappLink?: string;
  isSequenceActive: boolean;
  onMarkSent: (stepId: number) => void;
  onSkip: (stepId: number) => void;
  onOpenReschedule: (step: SequenceStep) => void;
  isMarkingSent?: boolean;
}

export function SequenceTimeline({
  steps,
  leadName,
  leadPhone,
  leadWhatsappLink,
  isSequenceActive,
  onMarkSent,
  onSkip,
  onOpenReschedule,
  isMarkingSent,
}: SequenceTimelineProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className="py-8 text-center text-xs text-muted-foreground">
        Nenhuma etapa cadastrada nesta sequência.
      </div>
    );
  }

  return (
    <div className="relative space-y-4 before:absolute before:left-3.5 before:top-4 before:bottom-4 before:w-0.5 before:bg-border/60">
      {steps.map((step) => (
        <div key={step.id} className="relative pl-7">
          {/* Bullet dot */}
          <div
            className={`absolute left-2.5 top-5 size-2.5 -translate-x-1/2 rounded-full border border-background ${
              step.status === "sent"
                ? "bg-emerald-500 ring-2 ring-emerald-500/20"
                : step.status === "ready"
                ? "bg-emerald-500 animate-ping ring-2 ring-emerald-500/40"
                : step.status === "skipped"
                ? "bg-muted-foreground/40"
                : "bg-sky-500"
            }`}
          />
          <SequenceStepCard
            step={step}
            leadName={leadName}
            leadPhone={leadPhone}
            leadWhatsappLink={leadWhatsappLink}
            isSequenceActive={isSequenceActive}
            onMarkSent={onMarkSent}
            onSkip={onSkip}
            onOpenReschedule={onOpenReschedule}
            isMarkingSent={isMarkingSent}
          />
        </div>
      ))}
    </div>
  );
}
