export type ConversionPackStatus = "draft" | "approved" | "archived";

export interface StrategyData {
  opportunity: string;
  problem: string;
  evidence: string[];
  commercialAngle: string;
  recommendedCta: string;
  confidence: "low" | "medium" | "high";
  primaryRule?: string;
}

export interface FollowupItem {
  order: number;
  delayDays: number;
  objective: string;
  message: string;
}

export interface MessagesData {
  initial: string;
  afterInterest: string;
  prototypeDelivery: string;
  followups: FollowupItem[];
  closing: string;
}

export interface ObjectionItem {
  objection: string;
  response: string;
}

export interface PrototypeDirective {
  templateKey: string;
  focus: string[];
  heroAngle: string;
  primaryCta: string;
  sectionsToHighlight: string[];
}

export interface ConversionPack {
  id: number;
  placeId: string;
  landingPageId: number | null;
  status: ConversionPackStatus;
  strategy: StrategyData;
  messages: MessagesData;
  objections: ObjectionItem[];
  prototype: PrototypeDirective;
  provider?: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  approvedAt?: string | null;
}

export interface ConversionPackVersion {
  id: number;
  conversionPackId: number;
  version: number;
  snapshot: Omit<ConversionPack, "id" | "placeId" | "version" | "createdAt" | "updatedAt">;
  changeType: string;
  provider?: string;
  createdAt: string;
}

export type ConversationStatus = "open" | "waiting_lead" | "waiting_user" | "won" | "lost" | "archived";
export type InteractionDirection = "outbound" | "inbound" | "internal";
export type InteractionType = "message" | "response" | "note" | "call" | "status_change";

export type ResponseClassification =
  | "interested"
  | "requested_information"
  | "requested_price"
  | "requested_callback"
  | "not_now"
  | "declined"
  | "already_has_provider"
  | "invalid_contact"
  | "wrong_person"
  | "won"
  | "other";

export type NextActionType =
  | "reply"
  | "send_proposal"
  | "schedule_call"
  | "follow_up_later"
  | "close_as_lost"
  | "close_as_won"
  | "manual";

export const CLASSIFICACOES_LABELS: Record<ResponseClassification, string> = {
  interested: "Interessado",
  requested_information: "Pediu mais informações",
  requested_price: "Pediu preço",
  requested_callback: "Pediu contato depois",
  not_now: "Não é o momento",
  declined: "Recusou",
  already_has_provider: "Já possui fornecedor",
  invalid_contact: "Contato inválido",
  wrong_person: "Pessoa errada",
  won: "Venda fechada",
  other: "Outro",
};

export interface OutreachInteraction {
  id: number;
  conversation_id: number;
  sequence_id?: number | null;
  sequence_step_id?: number | null;
  direction: InteractionDirection;
  interaction_type: InteractionType;
  channel: string;
  content?: string | null;
  classification?: ResponseClassification | null;
  objection_type?: string | null;
  occurred_at: string;
  created_at: string;
}

export interface OutreachConversation {
  id: number;
  place_id: string;
  active_sequence_id?: number | null;
  status: ConversationStatus;
  last_interaction_at?: string | null;
  last_inbound_at?: string | null;
  last_outbound_at?: string | null;
  next_action_type?: NextActionType | null;
  next_action_at?: string | null;
  next_action_note?: string | null;
  created_at: string;
  updated_at: string;
  interactions?: OutreachInteraction[];
}
