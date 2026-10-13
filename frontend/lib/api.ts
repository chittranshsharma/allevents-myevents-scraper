export type Event = { id: number; name: string; platform: string; url: string; date: string | null; location: string | null; original_ticket_price: string | null; currency: string | null; description: string; last_checked_at: string; provenance: { source_url: string; excerpt?: string; price_method?: string }; organizer?: { name: string } | null; tickets?: { name: string; price: string | null; currency: string | null }[]; promotions?: Promotion[] };
export type Evidence = { id: number; source_url: string; excerpt: string; official: boolean; extracted_at: string; extraction_method: string };
export type Promotion = { id: number; event_id: number; event_name: string; event_url: string; platform: string; coupon_code: string | null; discount_value: string | null; discount_type: string | null; verification_status: string; confidence: string; eligibility: string | null; expiration_at: string | null; last_checked_at: string; evidence: Evidence[]; remaining_ticket_price: string | null; mandatory_fees: string | null; estimated_final_price: string | null; price_basis: string };
export type Job = { id: number; status: string; pages_processed: number; events_found: number; promotions_found: number; error_count: number; message: string; created_at: string; finished_at: string | null; results?: { id: number; url: string; fetch_status: string; error: string | null }[] };
export type Platform = { id: string; domain: string; status: string; reason: string };
export type Watch = { id: number; kind: string; value: string };
export type Notice = { id: number; title: string; message: string; created_at: string };
export type Overview = { total_events: number; events_examined: number; candidates: number; advertised_full_discounts: number; confirmed_full_discounts: number; possible_full_discounts: number; last_successful_job: Job | null };
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export const statuses = ['CONFIRMED FULL DISCOUNT', 'PUBLICLY ADVERTISED FULL DISCOUNT', 'POSSIBLE FULL DISCOUNT', 'VERIFIED PARTIAL DISCOUNT', 'UNVERIFIED CODE', 'EXPIRED', 'INELIGIBLE', 'UNKNOWN'];
export async function api<T>(path: string, token = '', method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, { method, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || (Array.isArray(result.detail) ? result.detail.map((d: { msg: string }) => d.msg).join('; ') : result.detail) || 'Request failed');
  return result as T;
}
export function when(value: string | null) { return value ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Unknown'; }
export function price(value: string | null, currency: string | null = 'INR') { return value === null ? 'Price unknown' : `${currency === 'INR' ? '₹' : currency || ''}${Number(value).toLocaleString()}`; }
