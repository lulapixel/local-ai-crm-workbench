import { useState } from "react";
import { XCircle, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useStopSequence } from "./hooks/useStopSequence";

interface StopSequenceDialogProps {
  sequenceId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultReason?: string;
}

export function StopSequenceDialog({
  sequenceId,
  open,
  onOpenChange,
  defaultReason = "replied",
}: StopSequenceDialogProps) {
  const [reason, setReason] = useState<string>(defaultReason);
  const stopMutation = useStopSequence();

  if (!sequenceId) return null;

  const handleConfirm = () => {
    stopMutation.mutate(
      { sequenceId, reason },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <XCircle className="size-5 text-destructive" />
            Interromper régua de abordagem
          </DialogTitle>
          <DialogDescription>
            Selecione o motivo da interrupção. As etapas pendentes serão canceladas e o histórico mantido.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="stop-reason">Motivo do encerramento</Label>
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger id="stop-reason">
                <SelectValue placeholder="Selecione o motivo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="replied">💬 O cliente respondeu à abordagem</SelectItem>
                <SelectItem value="declined">🛑 O cliente recusou a oferta</SelectItem>
                <SelectItem value="won">🎉 Negócio fechado (Venda realizada)</SelectItem>
                <SelectItem value="invalid_contact">⚠️ Contato inválido ou inexistente</SelectItem>
                <SelectItem value="manual">✋ Encerramento manual pelo operador</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={stopMutation.isPending}>
            Voltar
          </Button>
          <Button
            variant={reason === "replied" ? "default" : "destructive"}
            onClick={handleConfirm}
            disabled={stopMutation.isPending}
          >
            {stopMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Interrompendo...
              </>
            ) : (
              "Confirmar encerramento"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
