import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { regenerarSecoesPacote } from "@/services/outreach";
import type { QueueItem } from "./types";

interface RegeneratePackModalProps {
  item: QueueItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RegeneratePackModal({ item, open, onOpenChange }: RegeneratePackModalProps) {
  const [section, setSection] = useState<string>("messages.initial");
  const [instruction, setInstruction] = useState<string>("");

  const queryClient = useQueryClient();

  const pack = item?.conversion_pack;

  const regenMutation = useMutation({
    mutationFn: async () => {
      if (!pack) throw new Error("Pacote não encontrado.");
      return regenerarSecoesPacote(pack.id, [section], instruction || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Seção regenerada com sucesso via IA!");
      onOpenChange(false);
      setInstruction("");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao regenerar seção");
    },
  });

  if (!item || !pack) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-5 text-amber-500" />
            Regenerar Seção via IA
          </DialogTitle>
          <DialogDescription>
            Escolha qual parte do Pacote de Conversão da empresa <strong>{item.lead.name}</strong> você deseja refazer.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="section-select">Seção a regenerar</Label>
            <Select value={section} onValueChange={setSection}>
              <SelectTrigger id="section-select">
                <SelectValue placeholder="Selecione a seção" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="messages.initial">Mensagem inicial</SelectItem>
                <SelectItem value="messages.followups">Sequência de follow-ups</SelectItem>
                <SelectItem value="objections">Matriz de objeções</SelectItem>
                <SelectItem value="prototype">Diretrizes do protótipo (LP)</SelectItem>
                <SelectItem value="messages.all">Todas as mensagens</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="instruction-input">Orientação adicional para a IA (opcional)</Label>
            <Textarea
              id="instruction-input"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Ex: Use um tom mais informal e foque na dor de agendamento online..."
              rows={3}
              className="text-sm"
            />
          </div>

          <p className="text-xs text-muted-foreground bg-muted/50 p-2.5 rounded border">
            ⚠️ Alterações manuais feitas nesta seção específica serão substituídas pela nova versão da IA.
          </p>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={regenMutation.isPending}>
            Cancelar
          </Button>
          <Button onClick={() => regenMutation.mutate()} disabled={regenMutation.isPending}>
            {regenMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Regenerando...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 size-4" />
                Regenerar agora
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
