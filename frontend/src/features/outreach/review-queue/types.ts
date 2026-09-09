export type QueueStatusTab = "not_generated" | "draft" | "approved" | "archived";

export type WarningCode =
  | "missing_contact_channel"
  | "missing_whatsapp"
  | "missing_landing_page"
  | "landing_page_not_published"
  | "empty_initial_message"
  | "low_confidence"
  | "prototype_without_public_url"
  | "pack_archived";

export interface QueueLeadInfo {
  place_id: string;
  name: string;
  niche: string;
  city: string;
  score: number;
  phone: string;
  whatsapp_link: string;
  rating: number;
  review_count: number;
}

export interface QueueConversionPackInfo {
  id: number;
  status: "draft" | "approved" | "archived";
  strategy: {
    opportunity: string;
    commercialAngle: string;
    confidence: "low" | "medium" | "high";
    problem?: string;
    recommendedCta?: string;
  };
  initial_message: string;
  updated_at: string;
}

export interface QueueLandingPageInfo {
  id: number;
  status: "draft" | "published";
  preview_url: string;
  public_url: string;
}

export interface QueueChannels {
  whatsapp: boolean;
  phone: boolean;
  email: boolean;
}

export interface QueueItem {
  queue_status: QueueStatusTab;
  lead: QueueLeadInfo;
  conversion_pack: QueueConversionPackInfo | null;
  landing_page: QueueLandingPageInfo | null;
  sequence?: {
    id: number;
    status: "active" | "paused" | "replied" | "completed" | "cancelled";
    conversion_pack_version: number;
    version_outdated: boolean;
    current_step_order: number;
    next_step?: any;
  } | null;
  channels: QueueChannels;
  warnings: WarningCode[];
}

export interface QueueCounts {
  not_generated: number;
  draft: number;
  approved: number;
  archived: number;
}

export interface QueuePagination {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface ReviewQueueResponse {
  items: QueueItem[];
  pagination: QueuePagination;
  counts: QueueCounts;
}

export interface QueueFiltersState {
  status: QueueStatusTab;
  search: string;
  niche: string;
  city: string;
  min_score: string;
  channel: string;
  has_landing_page: string;
  landing_page_published: string;
  confidence: string;
  sort: string;
  page: number;
  page_size: number;
}
