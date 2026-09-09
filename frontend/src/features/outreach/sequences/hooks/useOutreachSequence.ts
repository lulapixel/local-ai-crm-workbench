import { useQuery } from "@tanstack/react-query";
import { obterSequenciaPacote, obterSequenciaPorId } from "@/services/outreach";
import type { SequenceDetails } from "../types";

export function useOutreachSequence(options: { sequenceId?: number; packId?: number }) {
  const { sequenceId, packId } = options;

  return useQuery<SequenceDetails | null, Error>({
    queryKey: sequenceId
      ? ["outreach", "sequence", sequenceId]
      : ["outreach", "pack-sequence", packId],
    queryFn: () => {
      if (sequenceId) {
        return obterSequenciaPorId(sequenceId);
      }
      if (packId) {
        return obterSequenciaPacote(packId);
      }
      return Promise.resolve(null);
    },
    enabled: Boolean(sequenceId || packId),
    staleTime: 5000,
  });
}
