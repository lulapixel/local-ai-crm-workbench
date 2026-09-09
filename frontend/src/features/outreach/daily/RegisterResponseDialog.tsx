import { useState } from "react";
import { MessageSquareReply, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useStopSequence } from "../sequences/hooks/useStopSequence";

interface RegisterResponseDialogProps {
  sequenceId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const opcoes: Array<{ value: string; label: string; reason: string; destructive?: boolean; muted?: boolean }> = [
  { value: "interesse", label: "💬 Demonstrou interesse (Aguardando reunião / proposta)", reason: "replied" },
  { value: "informacoes", label: "ℹ️ Pediu mais informações / tirou dúvida", reason: "replied" },
  { value: "depois", label: "🕒 Pediu para retornar mais tarde", reason: "replied" },
  { value: "recusou", label: "🛑 Recusou a oferta / Não tem interesse", reason: "declined", destructive: true },
  { value: "invalido", label: "⚠️ Contato ou número de WhatsApp inválido", reason: "invalid_contact", muted: true },
];

export function RegisterResponseDialog({
  sequenceId,
  open,
  onOpenChange,
  onSuccess,
}: RegisterResponseDialogProps) {
  const [opcao, setOpcao] = useState<string>("interesse");
  const stopMutation = useStopSequence();

  if (!sequenceId) return null;

  const handleConfirm = () => {
    const selected = opcoes.find((o) => o.value === opcao);
    const reason = selected?.reason || "replied";

    stopMutation.mutate(
      { sequenceId, reason },
      {
        onSuccess: () => {
          onOpenChange(false);
          if (onSuccess) onSuccess();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquareReply className="size-5 text-sky-500" />
            Registrar resposta do lead
          </DialogTitle>
          <DialogDescription>
            Como o cliente respondeu ao contato? A sequência será encerrada com base na resposta.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-2">
          {opcoes.map((o) => (
            <label
              key={o.value}
              className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-all hover:bg-accent/40 ${
                opcao === o.value ? "border-primary bg-primary/5 ring-1 ring-primary" : "border-border"
              }`}
            >
              <input
                type="radio"
                name="resposta"
                value={o.value}
                checked={opcao === o.value}
                onChange={() => setOpcao(o.value)}
                className="accent-primary size-4"
              />
              <span
                className={`font-medium text-xs ${
                  o.destructive ? "text-destructive" : o.muted ? "text-muted-foreground" : "text-foreground"
                }`}
              >
                {o.label}
              </span>
            </label>
          ))}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={stopMutation.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={stopMutation.isPending}>
            {stopMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Registrando...
              </>
            ) : (
              "Confirmar resposta"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
