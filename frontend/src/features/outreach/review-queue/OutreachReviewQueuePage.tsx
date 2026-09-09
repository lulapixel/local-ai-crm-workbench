import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Header } from "@/components/layout/Header";
import { aprovarPacoteConversao, arquivarPacoteConversao, arquivarPacotesEmLote } from "@/services/outreach";
import { useOutreachQueueFilters } from "./hooks/useOutreachQueueFilters";
import { useOutreachQueue } from "./hooks/useOutreachQueue";
import { useBulkGeneratePacks } from "./hooks/useBulkGeneratePacks";
import { useBulkApprovePacks } from "./hooks/useBulkApprovePacks";
import { OutreachQueueHeader } from "./OutreachQueueHeader";
import { OutreachQueueTabs } from "./OutreachQueueTabs";
import { OutreachQueueFilters } from "./OutreachQueueFilters";
import { OutreachQueueList } from "./OutreachQueueList";
import { OutreachQueueBulkActions } from "./OutreachQueueBulkActions";
import { RegeneratePackModal } from "./RegeneratePackModal";
import { CopyMessageModal } from "./CopyMessageModal";
import { saudacaoAtual } from "@/lib/saudacao";
import { safeExternalUrl, safeWhatsAppUrl } from "@/lib/safeExternalUrl";
import type { QueueItem } from "./types";

export function OutreachReviewQueuePage() {
  const queryClient = useQueryClient();
  const { filters, updateFilters, resetFilters } = useOutreachQueueFilters();
  const { data, isLoading, isError, error, refetch } = useOutreachQueue(filters);

  // Selection state (place_ids)
  const [selectedPlaceIds, setSelectedPlaceIds] = useState<string[]>([]);

  // Modals state
  const [regenerateItem, setRegenerateItem] = useState<QueueItem | null>(null);
  const [copyItem, setCopyItem] = useState<QueueItem | null>(null);

  // Bulk Hooks
  const bulkGenerate = useBulkGeneratePacks();
  const bulkApprove = useBulkApprovePacks();

  // Single Approve Mutation
  const approveMutation = useMutation({
    mutationFn: (packId: number) => aprovarPacoteConversao(packId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Pacote aprovado com sucesso!");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao aprovar pacote");
    },
  });

  // Single Archive Mutation
  const archiveMutation = useMutation({
    mutationFn: (packId: number) => arquivarPacoteConversao(packId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outreach"] });
      toast.success("Item arquivado da fila");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao arquivar item");
    },
  });

  const items = data?.items || [];

  // Toggle selection
  const handleToggleSelectOne = (placeId: string) => {
    setSelectedPlaceIds((prev) =>
      prev.includes(placeId) ? prev.filter((id) => id !== placeId) : [...prev, placeId]
    );
  };

  const handleToggleSelectAll = () => {
    const currentPageIds = items.map((i) => i.lead.place_id);
    const allSelected = currentPageIds.every((id) => selectedPlaceIds.includes(id));

    if (allSelected) {
      setSelectedPlaceIds((prev) => prev.filter((id) => !currentPageIds.includes(id)));
    } else {
      setSelectedPlaceIds((prev) => Array.from(new Set([...prev, ...currentPageIds])));
    }
  };

  const handleClearSelection = () => {
    setSelectedPlaceIds([]);
  };

  // Trigger Bulk Generate
  const handleBulkGenerate = () => {
    if (selectedPlaceIds.length === 0) return;
    bulkGenerate.mutate(
      { placeIds: selectedPlaceIds },
      {
        onSuccess: (res) => {
          // If all succeeded, clear selection. If partial failures, keep failed items selected
          const failedIds = res.results.filter((r) => !r.success).map((r) => r.place_id);
          setSelectedPlaceIds(failedIds);
        },
      }
    );
  };

  // Trigger Bulk Approve
  const handleBulkApprove = () => {
    const selectedPacks = items
      .filter((i) => selectedPlaceIds.includes(i.lead.place_id) && i.conversion_pack)
      .map((i) => i.conversion_pack!.id);

    if (selectedPacks.length === 0) {
      toast.error("Nenhum pacote elegível selecionado para aprovação.");
      return;
    }

    bulkApprove.mutate(selectedPacks, {
      onSuccess: () => {
        setSelectedPlaceIds([]);
      },
    });
  };

  // Trigger Bulk Archive
  const handleBulkArchive = () => {
    const selectedPacks = items
      .filter((i) => selectedPlaceIds.includes(i.lead.place_id) && i.conversion_pack)
      .map((i) => i.conversion_pack!.id);

    if (selectedPacks.length === 0) return;

    arquivarPacotesEmLote(selectedPacks)
      .then((data) => {
        queryClient.invalidateQueries({ queryKey: ["outreach"] });
        if (data.failed === 0) {
          toast.success(`${data.succeeded} pacote(s) arquivado(s) com sucesso!`);
        } else {
          toast.warning(`${data.succeeded} pacote(s) arquivado(s). ${data.failed} falharam.`);
        }
        setSelectedPlaceIds([]);
      })
      .catch((err) => {
        toast.error(err.message || "Erro ao arquivar itens selecionados");
      });
  };

  // Handle WhatsApp action
  const handleOpenWhatsApp = (item: QueueItem) => {
    if (!item.channels.whatsapp) {
      toast.error("Sem número de WhatsApp ou telefone válido para este lead.");
      return;
    }

    let phoneClean = (item.lead.phone || "").replace(/\D/g, "");
    if (!phoneClean && item.lead.whatsapp_link) {
      const match = item.lead.whatsapp_link.match(/55\d+/);
      if (match) phoneClean = match[0];
    }

    if (!phoneClean) {
      toast.error("Número de telefone não pôde ser formatado.");
      return;
    }

    if (!phoneClean.startsWith("55") && phoneClean.length <= 11) {
      phoneClean = `55${phoneClean}`;
    }

    const rawMsg = item.conversion_pack?.initial_message || `Oi, tudo bem? Vi que a ${item.lead.name}...`;
    const saudacao = saudacaoAtual();
    const msgComSaudacao = `${saudacao}! ${rawMsg.replace(/^(Oi|Olá|Bom dia|Boa tarde|Boa noite)[!.,]?\s*/i, "")}`;

    const waUrl = safeWhatsAppUrl(`https://wa.me/${phoneClean}`, msgComSaudacao);
    if (waUrl) window.open(waUrl, "_blank", "noopener,noreferrer");
    else toast.error("Número de WhatsApp inválido para este lead.");
  };

  // Handle Prototype action
  const handleOpenPrototype = (item: QueueItem) => {
    if (!item.landing_page) {
      toast.warning("Protótipo indisponível para este lead.");
      return;
    }

    const rawUrl =
      item.landing_page.status === "published" && item.landing_page.public_url
        ? item.landing_page.public_url
        : item.landing_page.preview_url;
    const url = safeExternalUrl(rawUrl, { allowRelative: true });
    if (!url) {
      toast.error("O link do protótipo não é válido.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <Header />

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        {/* Header & Stats breakdown */}
        <OutreachQueueHeader
          counts={data?.counts}
          selectedCount={selectedPlaceIds.length}
          onRefresh={() => refetch()}
          onGenerateSelected={handleBulkGenerate}
          isGenerating={bulkGenerate.isPending}
        />

        {/* Operational Tabs */}
        <OutreachQueueTabs
          activeTab={filters.status}
          onTabChange={(newTab) => updateFilters({ status: newTab })}
          counts={data?.counts}
        />

        {/* Filters Bar */}
        <OutreachQueueFilters
          filters={filters}
          onFilterChange={updateFilters}
          onResetFilters={resetFilters}
        />

        {/* Items List / Cards */}
        <OutreachQueueList
          items={items}
          pagination={data?.pagination}
          isLoading={isLoading}
          isError={isError}
          error={error}
          selectedPlaceIds={selectedPlaceIds}
          onToggleSelectAll={handleToggleSelectAll}
          onToggleSelectOne={handleToggleSelectOne}
          onPageChange={(newPage) => updateFilters({ page: newPage })}
          onApprove={(packId) => approveMutation.mutate(packId)}
          onArchive={(packId) => archiveMutation.mutate(packId)}
          onOpenRegenerate={(item) => setRegenerateItem(item)}
          onOpenCopyModal={(item) => setCopyItem(item)}
          onOpenWhatsApp={handleOpenWhatsApp}
          onOpenPrototype={handleOpenPrototype}
          onRefetch={() => refetch()}
        />

        {/* Bulk Actions Floating Bar */}
        <OutreachQueueBulkActions
          selectedCount={selectedPlaceIds.length}
          activeTab={filters.status}
          onClearSelection={handleClearSelection}
          onBulkGenerate={handleBulkGenerate}
          onBulkApprove={handleBulkApprove}
          onBulkArchive={handleBulkArchive}
          isGenerating={bulkGenerate.isPending}
          isApproving={bulkApprove.isPending}
        />

        {/* Modals */}
        <RegeneratePackModal
          item={regenerateItem}
          open={Boolean(regenerateItem)}
          onOpenChange={(open) => !open && setRegenerateItem(null)}
        />

        <CopyMessageModal
          item={copyItem}
          open={Boolean(copyItem)}
          onOpenChange={(open) => !open && setCopyItem(null)}
        />
      </main>
    </div>
  );
}
