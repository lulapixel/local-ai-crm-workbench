import type { WarningCode } from "../review-queue/types";
import type { SequenceStatus, StepStatus } from "../sequences/types";

export type DailyCategoryTab = "all" | "overdue" | "today" | "new" | "paused" | "upcoming" | "replied";

export type ActionPriority = "overdue" | "ready_today" | "new_contacts" | "paused" | "upcoming" | "replied_recently";

export interface DailyLeadInfo {
  place_id: string;
  name: string;
  score: number;
  niche: string;
  city: string;
  phone: string;
  whatsapp_link: string;
  rating: number;
  review_count: number;
}

export interface DailySequenceInfo {
  id: number;
  status: SequenceStatus;
  conversion_pack_version: number;
  version_outdated: boolean;
}

export interface DailyStepInfo {
  id: number;
  step_order: number;
  step_type: "initial" | "followup";
  objective: string;
  message: string;
  scheduled_for: string | null;
  status: StepStatus;
}

export interface DailyLandingPageInfo {
  id: number;
  status: "draft" | "published";
  preview_url: string;
  public_url: string;
}

export interface DailyConversationInfo {
  id: number;
  status: string;
  next_action_type?: string | null;
  next_action_note?: string | null;
  last_inbound_at?: string | null;
  last_inbound_content?: string | null;
  last_inbound_classification?: string | null;
}

export interface DailyActionItem {
  action_type: "sequence_step" | "new_contact";
  priority: ActionPriority;
  lead: DailyLeadInfo;
  sequence?: DailySequenceInfo | null;
  step: DailyStepInfo;
  landing_page?: DailyLandingPageInfo | null;
  conversation?: DailyConversationInfo | null;
  warnings: WarningCode[];
}

export interface DailyCounts {
  overdue: number;
  ready_today: number;
  new_contacts: number;
  paused: number;
  replied_recently: number;
  upcoming: number;
}

export interface DailyCockpitResponse {
  date: string;
  timezone: string;
  counts: DailyCounts;
  items: DailyActionItem[];
}

export interface DailyFiltersState {
  category: DailyCategoryTab;
  search: string;
  niche: string;
  city: string;
  min_score: string;
  channel: string;
  date: string;
  page: number;
  page_size: number;
}
