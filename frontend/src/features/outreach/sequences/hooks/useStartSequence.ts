import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { iniciarSequenciaPacote } from "@/services/outreach";

export function useStartSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ packId, channel }: { packId: number; channel?: string }) =>
      iniciarSequenciaPacote(packId, channel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Régua de abordagem iniciada com sucesso!");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao iniciar sequência");
    },
  });
}
