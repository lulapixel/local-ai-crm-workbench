import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { retomarSequencia } from "@/services/outreach";

export function useResumeSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sequenceId: number) => retomarSequencia(sequenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Sequência retomada! Etapas futuras foram deslocadas.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao retomar sequência");
    },
  });
}
