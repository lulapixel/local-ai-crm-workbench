import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { aprovarPacotesEmLote } from "@/services/outreach";

export function useBulkApprovePacks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (packIds: number[]) => aprovarPacotesEmLote(packIds),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      if (data.failed === 0) {
        toast.success(`${data.succeeded} pacote(s) aprovado(s) com sucesso!`);
      } else {
        toast.warning(
          `${data.succeeded} pacote(s) aprovado(s). ${data.failed} falharam.`
        );
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao aprovar pacotes em lote");
    },
  });
}
