import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { pausarSequencia } from "@/services/outreach";

export function usePauseSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sequenceId: number) => pausarSequencia(sequenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.info("Sequência pausada.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao pausar sequência");
    },
  });
}
