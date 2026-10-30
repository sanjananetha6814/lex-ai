export type UserRole = 'USER' | 'LAWYER' | 'ADMIN'

export interface UserProfile {
  id?: number
  user_id?: number
  full_name: string
  phone_number?: string | null
  city?: string | null
  preferred_language?: string
  bio?: string
}

export interface LawyerAccount {
  id: number
  name: string
  email?: string
}

export interface User {
  id: number
  email: string
  role: UserRole
  is_active?: boolean
  profile?: UserProfile | null
  lawyer_account?: LawyerAccount | null
  created_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface RegisterUserData {
  email: string
  password: string
  full_name: string
  phone_number?: string
  city?: string
  preferred_language?: string
  role?: UserRole
}

export interface LawyerReview {
  author?: string
  client_name?: string
  rating: number
  date?: string
  comment: string
}

export interface LawyerProfileData {
  id?: number
  specialty?: string
  experience_years?: string
  consultation_fee?: string
  fee_number?: number
  languages?: string
  bio?: string
  practice_summary?: string
  practice_areas?: string[]
  qualifications?: string[]
  availability_status?: string
  next_slot?: string
  rating?: number
  review_count?: string
  initials?: string
  tone?: string
  slots?: string[]
}

export interface BackendLawyerReview {
  id?: number
  client_name: string
  rating: number
  comment: string
  created_at?: string
}

export interface BackendLawyer {
  id: number
  name: string
  email?: string
  phone?: string
  city: string
  state?: string
  bar_council_id?: string
  is_verified?: boolean
  profile?: LawyerProfileData
  reviews?: BackendLawyerReview[]
  created_at?: string
}

export interface FrontendLawyer {
  [index: number]: string | undefined
  id: number | string
  name: string
  specialty: string
  years?: string
  exp?: string
  city: string
  langs: string
  rating: string | number
  reviews: string | number
  initials: string
  tone: string
  fee: string
  feeNumber?: number
  availability: string
  nextSlot?: string
  barId?: string
  bio?: string
  areas?: string[]
  qualifications?: string[]
  experienceSummary?: string
  summary?: string
  slots?: string[]
  reviewsList?: LawyerReview[]
  email?: string
  phone?: string
}

export type ConsultationStatus = 'PENDING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED'

export interface ConsultationBookingRequest {
  lawyer_id: number
  client_name: string
  client_email: string
  client_phone: string
  client_language: string
  format: string
  scheduled_date: string
  scheduled_slot: string
  issue_description: string
  is_urgent: boolean
}

export interface ConsultationResponse {
  id: number
  reference_no: string
  lawyer_id: number
  user_id?: number | null
  client_name: string
  client_email: string
  client_phone: string
  client_language: string
  format: string
  scheduled_date: string
  scheduled_slot: string
  issue_description: string
  is_urgent: boolean
  fee?: string
  status: ConsultationStatus
  lawyer_name?: string | null
  lawyer_specialty?: string | null
  created_at?: string
}

export interface ChatMessage {
  id: number | string
  role: 'user' | 'assistant' | 'system'
  text?: string
  content?: string
  title?: string
  explanation?: string
  implication?: string
  checks?: string[]
  consult?: string
  sources?: string[]
  caveat?: string
  conversation_id?: number
  created_at?: string
  language?: string
  is_grounded?: boolean
  backend?: unknown
}

export interface ConversationMessage {
  id: number
  role: string
  content: string
  sources?: string[]
  created_at?: string
}

export interface Conversation {
  id: number
  title: string
  language?: string
  created_at?: string
  updated_at?: string
  messages?: ConversationMessage[]
}

export interface ChatAnswerResponse {
  id: number
  role: 'assistant'
  title: string
  text: string
  explanation: string
  implication: string
  checks: string[]
  consult: string
  sources: string[]
  caveat: string
  conversation_id?: number
}

export interface ClauseFinding {
  clause_name: string
  original_snippet?: string
  simplified_explanation: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  recommended_action: string
  practical_action?: string
  confidence_score?: number
}

export interface DocumentClauseItem {
  clause?: string
  title?: string
  clause_name?: string
  level?: string
  risk?: string
  risk_level?: string
  text?: string
  explanation?: string
  simplified_explanation?: string
  excerpt?: string
  action?: string
  original_snippet?: string
}

export interface DocumentAnalysisResult {
  id?: number
  filename?: string
  title?: string
  file_type?: string
  summary?: string
  document_type?: string
  overall_risk?: string
  overall_risk_score?: string | number
  risk_score?: number
  key_dates?: string[]
  key_entities?: string[]
  key_clauses?: ClauseFinding[]
  findings?: ClauseFinding[]
  clauses?: DocumentClauseItem[]
  unclear_items?: string
  raw_text_preview?: string
  verified_sources?: string[]
  detectedText?: boolean
  clausesIdentified?: boolean
  analyzed?: boolean
  created_at?: string
}

export interface NotificationItem {
  id: number
  user_id: number
  title: string
  message: string
  type: string
  is_read: boolean
  created_at: string
  updated_at: string
}

export interface NotificationListResponse {
  items: NotificationItem[]
  unread_count: number
}

export interface MarkAllReadResponse {
  success: boolean
  marked_count: number
}

export interface FormattedClause {
  clause: string
  level: string
  text: string
  excerpt?: string
}
