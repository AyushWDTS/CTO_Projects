export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type Source = {
  id: string;
  name: string;
  url: string;
  rss_url?: string | null;
  source_type: string;
  category?: string | null;
  region?: string | null;
  priority: number;
  fetch_method: string;
  fetch_frequency_minutes: number;
  reliability_score: number;
  is_active: boolean;
  last_fetched_at?: string | null;
  last_success_at?: string | null;
  failure_count: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceFetchLog = {
  id: string;
  source_id: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  http_status?: number | null;
  error_message?: string | null;
  items_found?: number | null;
  items_stored?: number | null;
  created_at: string;
};

export type RawDocument = {
  id: string;
  source_id: string;
  url: string;
  canonical_url?: string | null;
  content_type?: string | null;
  raw_content?: string | null;
  raw_hash: string;
  raw_size_bytes?: number | null;
  http_status?: number | null;
  fetched_at: string;
  metadata?: JsonValue;
  created_at: string;
};

export type Article = {
  id: string;
  raw_document_id: string;
  source_id: string;
  title?: string | null;
  canonical_url?: string | null;
  source_url: string;
  content_type?: string | null;
  clean_text?: string | null;
  excerpt?: string | null;
  author?: string | null;
  published_at?: string | null;
  language?: string | null;
  content_hash?: string | null;
  extraction_status: string;
  extraction_error?: string | null;
  duplicate_of_article_id?: string | null;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
};

export type NewsEvent = {
  id: string;
  canonical_title?: string | null;
  canonical_url?: string | null;
  normalized_canonical_url?: string | null;
  primary_article_id?: string | null;
  primary_source_id?: string | null;
  event_key: string;
  category?: string | null;
  region?: string | null;
  published_at?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  article_count: number;
  source_count: number;
  status: string;
  confidence_score: string | number;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
};

export type EventArticle = {
  id: string;
  event_id: string;
  article_id: string;
  source_id: string;
  match_type: string;
  similarity_score: string | number;
  confidence_score: string | number;
  is_primary: boolean;
  match_details?: JsonValue;
  created_at: string;
};

export type EventAIAnalysis = {
  id: string;
  event_id: string;
  summary?: string | null;
  short_summary?: string | null;
  why_it_matters?: string | null;
  key_points?: JsonValue;
  entities?: JsonValue;
  topics?: JsonValue;
  sentiment?: string | null;
  relevance_score?: string | number | null;
  urgency_score?: string | number | null;
  importance_tier?: string | null;
  suggested_action?: string | null;
  affected_business_area?: string | null;
  confidence_score?: string | number | null;
  status: string;
  error_message?: string | null;
  source_article_ids?: JsonValue;
  source_urls?: JsonValue;
  primary_article_id?: string | null;
  context_article_count: number;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
};

export type Digest = {
  id: string;
  digest_date: string;
  window_start: string;
  window_end: string;
  title: string;
  status: string;
  total_candidates: number;
  total_selected: number;
  critical_count: number;
  important_count: number;
  monitor_count: number;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
  items?: DigestItem[];
};

export type DigestItem = {
  id: string;
  digest_id: string;
  event_id: string;
  event_ai_analysis_id?: string | null;
  rank: number;
  section: string;
  final_score: string | number;
  relevance_score?: string | number | null;
  urgency_score?: string | number | null;
  source_authority_score?: string | number | null;
  recency_score?: string | number | null;
  business_impact_score?: string | number | null;
  importance_tier?: string | null;
  headline?: string | null;
  summary?: string | null;
  why_it_matters?: string | null;
  suggested_action?: string | null;
  source_urls?: JsonValue;
  metadata?: JsonValue;
  created_at: string;
};

export type BriefingBookmark = {
  id: string;
  user_key: string;
  event_id: string;
  digest_id?: string | null;
  digest_item_id?: string | null;
  digest_date?: string | null;
  section?: string | null;
  headline: string;
  summary?: string | null;
  why_it_matters?: string | null;
  suggested_action?: string | null;
  source_url?: string | null;
  importance_tier?: string | null;
  note?: string | null;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
};

export type OrchestrationRunRequest = {
  digest_date?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  dry_run?: boolean;
  skip_ingestion?: boolean;
  skip_normalization?: boolean;
  skip_clustering?: boolean;
  skip_ai?: boolean;
  continue_on_ai_failure?: boolean;
  refresh_digest?: boolean;
  demo_mode?: boolean;
  limit?: number;
  digest_limit?: number;
  triggered_by?: string;
};

export type OrchestrationRun = {
  id: string;
  run_type: string;
  status: string;
  digest_date?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  lock_key: string;
  idempotency_key: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  triggered_by: string;
  dry_run: boolean;
  continue_on_ai_failure: boolean;
  digest_id?: string | null;
  error_message?: string | null;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
  steps?: OrchestrationRunStep[];
};

export type OrchestrationRunStep = {
  id: string;
  run_id: string;
  step_name: string;
  step_order: number;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  items_processed?: number | null;
  items_created?: number | null;
  items_failed?: number | null;
  error_message?: string | null;
  metadata?: JsonValue;
  created_at: string;
  updated_at: string;
};

export type SourceHealthCheck = {
  id: string;
  source_id: string;
  status: string;
  checked_at: string;
  finished_at?: string | null;
  latency_ms?: number | null;
  http_status?: number | null;
  item_count?: number | null;
  content_size_bytes?: number | null;
  error_reason?: string | null;
  recommendation?: string | null;
  metadata?: JsonValue;
  created_at: string;
};

export type DataQualityRun = {
  id: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  duration_seconds?: number | null;
  scope_source_id?: string | null;
  min_severity?: string | null;
  total_findings: number;
  metadata?: JsonValue;
  created_at: string;
};

export type DataQualityFinding = {
  id: string;
  run_id: string;
  check_name: string;
  scope_type: string;
  scope_id?: string | null;
  source_id?: string | null;
  severity: string;
  message: string;
  recommendation?: string | null;
  metadata?: JsonValue;
  created_at: string;
};

export type DataQualitySummary = {
  latest_run?: DataQualityRun | null;
  severity_counts: Record<string, number>;
  source_health_counts: Record<string, number>;
  latest_findings: DataQualityFinding[];
};
