import type { AppStatus, EventRecord, FilterState, Options, OverviewData } from './types'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
export const apiUrl = (path: string) => `${API_BASE_URL}${path}`
async function get<T>(url: string): Promise<T> { const response = await fetch(apiUrl(url)); if (!response.ok) throw new Error(`${response.status} ${response.statusText}`); return response.json() as Promise<T> }
export const fetchStatus = () => get<AppStatus>('/api/status')
export const fetchOptions = () => get<Options>('/api/options')
export const fetchOverview = (filters: FilterState) => { const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => Boolean(v))); return get<OverviewData>(`/api/overview?${params}`) }
export const fetchEvents = (params: URLSearchParams) => get<{ rows: EventRecord[]; total: number; page: number; page_size: number; pages: number }>(`/api/events?${params}`)
export const fetchInvestigations = () => get<{ denominator: number; findings: Investigation[]; clusters: Cluster[] }>('/api/investigations')
export const fetchReviews = (q = '') => get<{ rows: Record<string, unknown>[]; total: number; available: boolean }>(`/api/reviews?q=${encodeURIComponent(q)}`)
export const fetchReports = () => get<{ files: ReportFile[] }>('/api/reports')
export type Investigation = { category: string; count: number; denominator: number; share: number; evidence: string; hypothesis: string; samples: Record<string, string>[]; causes: { label: string; count: number }[]; fixes: { label: string; count: number }[] }
export type Cluster = { cluster: number; records: number; top_terms: string; silhouette_sample: number | string }
export type ReportFile = { name: string; path: string; bytes: number; updated: string; description: string }
