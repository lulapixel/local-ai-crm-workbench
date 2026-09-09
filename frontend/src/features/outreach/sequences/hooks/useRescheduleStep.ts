import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { reagendarEtapaSequencia } from "@/services/outreach";

export function useRescheduleStep() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ stepId, scheduledFor }: { stepId: number; scheduledFor: string }) =>
      reagendarEtapaSequencia(stepId, scheduledFor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Etapa reagendada com sucesso!");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao reagendar etapa");
    },
  });
}
