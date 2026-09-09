export type SequenceStatus = "active" | "paused" | "replied" | "completed" | "cancelled";

export type StepStatus = "pending" | "ready" | "sent" | "skipped" | "cancelled" | "failed";

export type StopReason = "replied" | "declined" | "won" | "invalid_contact" | "manual" | "pack_archived";

export interface SequenceStep {
  id: number;
  sequence_id: number;
  step_order: number;
  step_type: "initial" | "followup";
  objective: string;
  message: string;
  delay_days: number;
  scheduled_for: string | null;
  status: StepStatus;
  channel: string;
  sent_at?: string | null;
  skipped_at?: string | null;
  cancelled_at?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SequenceDetails {
  id: number;
  place_id: string;
  conversion_pack_id: number;
  conversion_pack_version: number;
  version_outdated: boolean;
  status: SequenceStatus;
  channel: string;
  current_step_order: number;
  started_at: string;
  paused_at?: string | null;
  resumed_at?: string | null;
  completed_at?: string | null;
  stopped_at?: string | null;
  stop_reason?: StopReason | string | null;
  created_at: string;
  updated_at: string;
  next_step?: SequenceStep | null;
  steps: SequenceStep[];
}
