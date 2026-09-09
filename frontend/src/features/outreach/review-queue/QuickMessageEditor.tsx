import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { atualizarPacoteConversao } from "@/services/outreach";
import type { QueueItem } from "./types";

interface QuickMessageEditorProps {
  item: QueueItem;
  isEditing: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

export function QuickMessageEditor({ item, isEditing, onCancel, onSuccess }: QuickMessageEditorProps) {
  const pack = item.conversion_pack;
  const initialText = pack?.initial_message || "";
  const [mensagem, setMensagem] = useState(initialText);

  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: async (novoTexto: string) => {
      if (!pack) throw new Error("Pacote de conversão não encontrado.");
      return atualizarPacoteConversao(pack.id, {
        messages: {
          initial: novoTexto,
        } as any,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Mensagem inicial atualizada!");
      onSuccess();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao atualizar mensagem");
    },
  });

  if (!pack) return null;

  if (!isEditing) {
    return (
      <div className="space-y-1">
        <span className="font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">
          Mensagem inicial
        </span>
        <div className="rounded-lg border bg-background p-3 text-xs leading-relaxed text-foreground font-mono">
          {pack.initial_message || <span className="italic text-muted-foreground">(Mensagem vazia)</span>}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-primary/30 bg-primary/5 p-3.5 transition-all">
      <div className="flex items-center justify-between text-xs font-semibold text-foreground">
        <span>Editar mensagem inicial</span>
        <span className="text-muted-foreground">{mensagem.length} caracteres</span>
      </div>

      <Textarea
        value={mensagem}
        onChange={(e) => setMensagem(e.target.value)}
        rows={4}
        placeholder="Digite a mensagem inicial..."
        className="resize-y text-sm bg-background/80"
        autoFocus
      />

      <div className="flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={updateMutation.isPending}>
          <X className="mr-1.5 size-3.5" />
          Cancelar
        </Button>
        <Button
          size="sm"
          onClick={() => updateMutation.mutate(mensagem)}
          disabled={updateMutation.isPending || mensagem === initialText}
        >
          {updateMutation.isPending ? (
            <Loader2 className="mr-1.5 size-3.5 animate-spin" />
          ) : (
            <Check className="mr-1.5 size-3.5" />
          )}
          Salvar alteração
        </Button>
      </div>
    </div>
  );
}
