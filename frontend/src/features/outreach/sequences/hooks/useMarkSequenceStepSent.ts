import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { marcarEtapaEnviada } from "@/services/outreach";

export function useMarkSequenceStepSent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ stepId, sentAt, channel }: { stepId: number; sentAt?: string; channel?: string }) =>
      marcarEtapaEnviada(stepId, sentAt, channel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Envio da etapa confirmado!");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao confirmar envio da etapa");
    },
  });
}
