import { useState } from "react";
import { Calendar as CalendarIcon, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRescheduleStep } from "./hooks/useRescheduleStep";
import type { SequenceStep } from "./types";

interface RescheduleStepDialogProps {
  step: SequenceStep | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RescheduleStepDialog({ step, open, onOpenChange }: RescheduleStepDialogProps) {
  const [dataHora, setDataHora] = useState<string>("");
  const rescheduleMutation = useRescheduleStep();

  if (!step) return null;

  const handleReschedule = () => {
    if (!dataHora) return;
    const isoDate = new Date(dataHora).toISOString();
    rescheduleMutation.mutate(
      { stepId: step.id, scheduledFor: isoDate },
      {
        onSuccess: () => {
          onOpenChange(false);
          setDataHora("");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarIcon className="size-5 text-primary" />
            Reagendar etapa da cadência
          </DialogTitle>
          <DialogDescription>
            Escolha uma nova data e horário para o envio de: <strong>{step.objective || `Etapa #${step.step_order}`}</strong>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="datetime-picker">Nova data e hora</Label>
            <Input
              id="datetime-picker"
              type="datetime-local"
              value={dataHora}
              onChange={(e) => setDataHora(e.target.value)}
              className="text-sm"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Se a nova data escolhida for no passado ou agora, a etapa ficará pronta para envio imediatamente.
          </p>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={rescheduleMutation.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleReschedule} disabled={!dataHora || rescheduleMutation.isPending}>
            {rescheduleMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Reagendando...
              </>
            ) : (
              "Confirmar reagendamento"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
