import type { ConversionPack } from "@/types/outreach";
import { fetchWithCsrf as fetch } from "@/services/httpClient";

export async function obterPacoteConversao(placeId: string): Promise<ConversionPack | null> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/conversion-pack`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Erro ao buscar pacote de conversão");
  return res.json();
}

export async function gerarPacoteConversao(
  placeId: string,
  options?: { forceRegenerate?: boolean; approach?: string; instruction?: string }
): Promise<ConversionPack> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/conversion-pack`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      force_regenerate: options?.forceRegenerate ?? false,
      approach: options?.approach ?? "consultative",
      instruction: options?.instruction,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao gerar pacote de conversão");
  }
  return res.json();
}

export async function atualizarPacoteConversao(
  packId: number,
  payload: Partial<ConversionPack>
): Promise<ConversionPack> {
  const res = await fetch(`/api/conversion-packs/${packId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao atualizar pacote de conversão");
  }
  return res.json();
}

export async function regenerarSecoesPacote(
  packId: number,
  sections: string[],
  instruction?: string
): Promise<ConversionPack> {
  const res = await fetch(`/api/conversion-packs/${packId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sections, instruction }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao regenerar seções do pacote");
  }
  return res.json();
}

export async function aprovarPacoteConversao(packId: number): Promise<ConversionPack> {
  const res = await fetch(`/api/conversion-packs/${packId}/approve`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Erro ao aprovar pacote de conversão");
  return res.json();
}

export async function arquivarPacoteConversao(packId: number): Promise<ConversionPack> {
  const res = await fetch(`/api/conversion-packs/${packId}/archive`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Erro ao arquivar pacote de conversão");
  return res.json();
}

export async function obterFilaAbordagem(paramsRecord: Record<string, string>): Promise<any> {
  const query = new URLSearchParams();
  Object.entries(paramsRecord).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") {
      query.append(key, val);
    }
  });

  const res = await fetch(`/api/outreach/review-queue?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao consultar fila de abordagens");
  }
  return res.json();
}

export async function gerarPacotesEmLote(
  placeIds: string[],
  options?: { approach?: string; forceRegenerate?: boolean }
): Promise<{ requested: number; succeeded: number; failed: number; results: Array<{ place_id: string; success: boolean; conversion_pack_id?: number; error?: string }> }> {
  const res = await fetch("/api/outreach/conversion-packs/bulk-generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      place_ids: placeIds,
      approach: options?.approach || "consultative",
      force_regenerate: options?.forceRegenerate ?? false,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao gerar pacotes em lote");
  }
  return res.json();
}

export async function aprovarPacotesEmLote(
  conversionPackIds: number[]
): Promise<{ requested: number; succeeded: number; failed: number; results: Array<{ conversion_pack_id: number; success: boolean; error?: string }> }> {
  const res = await fetch("/api/outreach/conversion-packs/bulk-approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversion_pack_ids: conversionPackIds,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao aprovar pacotes em lote");
  }
  return res.json();
}

export async function arquivarPacotesEmLote(
  conversionPackIds: number[]
): Promise<{ requested: number; succeeded: number; failed: number; results: Array<{ conversion_pack_id: number; success: boolean; error?: string }> }> {
  const res = await fetch("/api/outreach/conversion-packs/bulk-archive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversion_pack_ids: conversionPackIds,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao arquivar pacotes em lote");
  }
  return res.json();
}

export async function iniciarSequenciaPacote(packId: number, channel: string = "whatsapp"): Promise<any> {
  const res = await fetch(`/api/conversion-packs/${packId}/sequence/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao iniciar sequência de abordagem");
  }
  return res.json();
}

export async function obterSequenciaPacote(packId: number): Promise<any | null> {
  const res = await fetch(`/api/conversion-packs/${packId}/sequence`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Erro ao buscar sequência do pacote");
  return res.json();
}

export async function obterSequenciaPorId(sequenceId: number): Promise<any> {
  const res = await fetch(`/api/outreach/sequences/${sequenceId}`);
  if (!res.ok) throw new Error("Erro ao buscar detalhes da sequência");
  return res.json();
}

export async function marcarEtapaEnviada(stepId: number, sentAt?: string, channel: string = "whatsapp"): Promise<any> {
  const res = await fetch(`/api/outreach/sequence-steps/${stepId}/mark-sent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sent_at: sentAt, channel }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao confirmar envio da etapa");
  }
  return res.json();
}

export async function pularEtapaSequencia(stepId: number, reason?: string): Promise<any> {
  const res = await fetch(`/api/outreach/sequence-steps/${stepId}/skip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao pular etapa");
  }
  return res.json();
}

export async function reagendarEtapaSequencia(stepId: number, scheduledFor: string): Promise<any> {
  const res = await fetch(`/api/outreach/sequence-steps/${stepId}/reschedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scheduled_for: scheduledFor }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao reagendar etapa");
  }
  return res.json();
}

export async function pausarSequencia(sequenceId: number): Promise<any> {
  const res = await fetch(`/api/outreach/sequences/${sequenceId}/pause`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao pausar sequência");
  }
  return res.json();
}

export async function retomarSequencia(sequenceId: number): Promise<any> {
  const res = await fetch(`/api/outreach/sequences/${sequenceId}/resume`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao retomar sequência");
  }
  return res.json();
}

export async function interromperSequencia(sequenceId: number, reason: string = "replied"): Promise<any> {
  const res = await fetch(`/api/outreach/sequences/${sequenceId}/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao interromper sequência");
  }
  return res.json();
}

export async function obterCockpitDiario(params: {
  date?: string;
  category?: string;
  search?: string;
  channel?: string;
  min_score?: string;
  page?: number;
  page_size?: number;
}): Promise<any> {
  const searchParams = new URLSearchParams();
  if (params.date) searchParams.set("date", params.date);
  if (params.category && params.category !== "all") searchParams.set("category", params.category);
  if (params.search) searchParams.set("search", params.search);
  if (params.channel && params.channel !== "all") searchParams.set("channel", params.channel);
  if (params.min_score) searchParams.set("min_score", params.min_score);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));

  const res = await fetch(`/api/outreach/daily-cockpit?${searchParams.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao consultar cockpit diário de prospecção");
  }
  return res.json();
}

export async function obterConversaLead(placeId: string): Promise<any> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/outreach/conversation`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao consultar conversa do lead");
  }
  return res.json();
}

export async function registrarRespostaLead(
  placeId: string,
  payload: {
    classification: string;
    content?: string;
    channel?: string;
    occurred_at?: string | null;
    note?: string;
  }
): Promise<any> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/outreach/responses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao registrar resposta do lead");
  }
  return res.json();
}

export async function registrarNotaLead(placeId: string, content: string, channel: string = "whatsapp"): Promise<any> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/outreach/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, channel }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao registrar nota interna");
  }
  return res.json();
}

export async function registrarLigacaoLead(
  placeId: string,
  payload: { content?: string; classification?: string; objection_type?: string; channel?: string }
): Promise<any> {
  const res = await fetch(`/api/leads/${encodeURIComponent(placeId)}/outreach/calls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao registrar ligação");
  }
  return res.json();
}

export async function atualizarInteracao(
  interactionId: number,
  payload: { classification?: string; content?: string; objection_type?: string }
): Promise<any> {
  const res = await fetch(`/api/outreach/interactions/${interactionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao atualizar interação");
  }
  return res.json();
}

export async function excluirInteracao(interactionId: number): Promise<any> {
  const res = await fetch(`/api/outreach/interactions/${interactionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao excluir interação");
  }
  return res.json();
}

export async function sugerirRespostaIA(interactionId: number): Promise<{
  interaction_id: number;
  place_id: string;
  received_response: string;
  classification: string;
  suggested_reply: string;
}> {
  const res = await fetch(`/api/outreach/interactions/${interactionId}/suggest-reply`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || "Erro ao gerar sugestão de resposta");
  }
  return res.json();
}
