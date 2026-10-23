export type EventRecord = {
  'Event id': string; 'Opened date': string; 'Opened date_parsed'?: string | null
  CUSTOMER_VERBATIM: string; CAUSAL_VERBATIM: string; CORRECTION_VERBATIM: string
  BUILD_PLANT_DESC: string; CAUSAL_CD_DESC: string; COMPLAINT_CD_DESC: string
  MAKE: string; MODEL: string; MODLYR: number | string; issue_category: string
  extracted_tags: string[]; 'Failure Component_parsed': string[]; 'Failure Condition_parsed': string[]
  'Fix Component_parsed': string[]; 'Fix Condition_parsed': string[]; text_cluster: number | string | null
  [key: string]: unknown
}
export type CountItem = { label: string; count: number }
export type FilterState = { date_from: string; date_to: string; make: string; model: string; plant: string; category: string }
export type OverviewData = {
  summary: { total_events: number; unique_event_ids: number; distinct_components: number; distinct_categories: number; distinct_causal_codes: number; distinct_complaint_codes: number; annotated_records: number; annotation_field_counts: Record<string, number>; component_condition_records: number; distinct_plants: number; model_years: string[]; denominator: number }
  monthly: { month: string; events: number }[]
  complaints: CountItem[]; causes: CountItem[]; issues: CountItem[]; makes: CountItem[]; models: CountItem[]; plants: CountItem[]; components: CountItem[]; conditions: CountItem[]; fixes: CountItem[]; combinations: CountItem[]; recent: EventRecord[]
}
export type AppStatus = { event_count: number; review_count: number; last_refresh: string | null; dataset: string; review_collection: { failed_requests?: string[] } }
export type Options = { makes: string[]; models: string[]; plants: string[]; categories: string[]; date_min: string | null; date_max: string | null }
