import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { gerarPacotesEmLote } from "@/services/outreach";

export function useBulkGeneratePacks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ placeIds, approach }: { placeIds: string[]; approach?: string }) =>
      gerarPacotesEmLote(placeIds, { approach }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      if (data.failed === 0) {
        toast.success(`${data.succeeded} pacote(s) gerado(s) com sucesso!`);
      } else {
        toast.warning(
          `${data.succeeded} pacote(s) gerado(s). ${data.failed} falharam e permanecem selecionados.`
        );
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao gerar pacotes em lote");
    },
  });
}
