export interface HealthResponse {
  status: 'ok' | 'error'
}

export interface PublicFeatures {
  google_login: boolean
  billing: boolean
  file_uploads: boolean
  email: boolean
}

export interface PublicConfig {
  brand_name: string
  features: PublicFeatures
}

export type PlatformRole = 'user' | 'admin' | 'superadmin'

export type OrgRole = 'owner' | 'admin' | 'member'

export interface User {
  id: string
  email: string
  full_name: string
  avatar_url: string | null
  platform_role: PlatformRole
  is_email_verified: boolean
  has_password: boolean
  google_linked: boolean
  created_at: string
}

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
  role: OrgRole
  plan_id: string
  logo_url: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface MeResponse {
  user: User
  organizations: OrganizationSummary[]
  impersonated_by: string | null
}

export interface StatusResponse {
  status: 'ok'
}

export type InvitableRole = Exclude<OrgRole, 'owner'>

export interface PlanLimits {
  members: number
  projects: number
  storage_mb: number
}

export interface OrganizationDetail extends OrganizationSummary {
  plan_name: string
  owner_id: string | null
  member_count: number
  pending_invitation_count: number
  limits: PlanLimits
  created_at: string
}

export interface Member {
  id: string
  user_id: string
  email: string
  full_name: string | null
  role: OrgRole
  joined_at: string
}

export interface Invitation {
  id: string
  email: string
  role: InvitableRole
  expires_at: string
  created_at: string
}

export interface InvitationCreated {
  invitation: Invitation
  invite_url: string
}

export interface InvitationPreview {
  organization_name: string
  inviter_name: string | null
  email: string
  role: InvitableRole
  expired: boolean
}

export type ProjectStatus = 'active' | 'archived'

export interface Project {
  id: string
  organization_id: string
  name: string
  description: string | null
  status: ProjectStatus
  created_by_id: string | null
  created_at: string
  updated_at: string
}

export interface ProjectInput {
  name: string
  description: string | null
}

export interface ProjectUpdateInput {
  name?: string
  description?: string | null
  status?: ProjectStatus
}

export interface StoredFile {
  id: string
  organization_id: string
  uploaded_by_id: string | null
  name: string
  size_bytes: number
  content_type: string
  created_at: string
}

export interface DownloadUrlResponse {
  url: string
}

export interface AvatarResponse {
  avatar_url: string | null
}

export interface LogoResponse {
  logo_url: string | null
}

export type BillingInterval = 'monthly' | 'yearly'
export type SubscriptionStatus = 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired'
export type PaymentStatus = 'succeeded' | 'failed' | 'refunded'

export interface PlanInfo {
  id: string
  name: string
  price_monthly_cents: number
  price_yearly_cents: number
  trial_days: number
  limits: PlanLimits
  features: string[]
  available: Record<BillingInterval, boolean>
}

export interface SubscriptionSummary {
  provider: string
  plan_id: string
  interval: BillingInterval
  status: SubscriptionStatus
  current_period_end: string | null
  cancel_at_period_end: boolean
  trial_ends_at: string | null
}

export interface PlanOverride {
  plan_id: string
  reason: string | null
}

export interface BillingUsage {
  members: number
  projects: number
  storage_bytes: number
}

export interface BillingOverview {
  plan: PlanInfo
  plan_override: PlanOverride | null
  subscription: SubscriptionSummary | null
  usage: BillingUsage
  billing_enabled: boolean
  provider: string | null
}

export interface PaymentRecord {
  id: string
  provider: string
  amount_cents: number
  currency: string
  status: PaymentStatus
  paid_at: string | null
  invoice_url: string | null
  created_at: string
}

export interface RedirectUrl {
  url: string
}

export type ChartRangeDays = 30 | 90

export interface DailyCount {
  day: string
  count: number
}

export interface OverviewStats {
  plan_id: string
  has_analytics: boolean
  projects_count: number
  projects_limit: number
  members_count: number
  members_limit: number
  storage_used_bytes: number
  storage_limit_bytes: number
}

export interface OverviewCharts {
  days: number
  projects_per_day: DailyCount[]
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface AdminUserSummary {
  id: string
  email: string
  full_name: string | null
  platform_role: User['platform_role']
  is_email_verified: boolean
  is_blocked: boolean
  created_at: string
  last_login_at: string | null
}

export interface AdminUserMembership {
  organization_id: string
  organization_name: string
  organization_slug: string
  role: string
  plan_id: string
}

export interface AdminUserDetail extends AdminUserSummary {
  has_password: boolean
  google_linked: boolean
  memberships: AdminUserMembership[]
}

export interface ResendVerificationResult {
  sent: boolean
}

export interface ImpersonationResult {
  access_token: string
  token_type: string
  expires_in: number
}

export interface AdminOrganizationSummary {
  id: string
  name: string
  slug: string
  plan_id: string
  plan_override_id: string | null
  owner_email: string | null
  members_count: number
  created_at: string
}

export interface AdminOrganizationMember {
  membership_id: string
  user_id: string
  email: string
  full_name: string | null
  role: string
}

export interface AdminSubscription {
  id: string
  provider: string
  plan_id: string
  interval: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
  trial_ends_at: string | null
  created_at: string
}

export interface AdminPayment {
  id: string
  provider: string
  amount_cents: number
  currency: string
  status: string
  paid_at: string | null
  invoice_url: string | null
}

export interface AdminOrganizationDetail extends AdminOrganizationSummary {
  plan_override_reason: string | null
  billing_provider: string | null
  members: AdminOrganizationMember[]
  subscription: AdminSubscription | null
  payments: AdminPayment[]
}

export interface PlanOverrideInput {
  plan_id: string | null
  reason: string
}

export interface TrialConversion {
  window_days: number
  ended_trials: number
  converted: number
  rate: number | null
}

export interface PlatformMetrics {
  currency: string
  mrr_cents: number
  active_subscriptions: number
  trialing_subscriptions: number
  past_due_subscriptions: number
  churned_last_30_days: number
  trial_conversion: TrialConversion
  total_users: number
  total_organizations: number
  days: number
  signups_per_day: DailyCount[]
  new_organizations_per_day: DailyCount[]
}

export type SetupChecklistStatus = 'ok' | 'missing' | 'warning' | 'manual'

export interface SetupChecklistItem {
  id: string
  status: SetupChecklistStatus
  docs_url: string
}

export interface SetupChecklist {
  items: SetupChecklistItem[]
}

export type NotificationKind =
  | 'welcome'
  | 'member_joined'
  | 'member_role_changed'
  | 'member_removed'
  | 'ownership_transferred'
  | 'system'

export type NotificationReadFilter = 'all' | 'unread' | 'read'

export interface AppNotification {
  id: string
  organization_id: string | null
  kind: NotificationKind | string
  title: string
  body: string
  link: string | null
  read_at: string | null
  created_at: string
}

export interface NotificationList extends Page<AppNotification> {
  unread_count: number
}

export interface NotificationEmailSetting {
  kind: NotificationKind
  email_enabled: boolean
}

export interface NotificationSettings {
  email_delivery_available: boolean
  settings: NotificationEmailSetting[]
}
