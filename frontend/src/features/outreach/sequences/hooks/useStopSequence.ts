import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { interromperSequencia } from "@/services/outreach";

export function useStopSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sequenceId, reason }: { sequenceId: number; reason?: string }) =>
      interromperSequencia(sequenceId, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      if (variables.reason === "replied") {
        toast.success("Resposta registrada! Sequência encerrada.");
      } else {
        toast.info("Sequência interrompida.");
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao interromper sequência");
    },
  });
}
