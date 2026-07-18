/**
 * Frontend API client — calls backend via /api/* (Next.js rewrites to NEXT_PUBLIC_API_URL).
 */
import { getAccessToken, refreshAccessToken } from './supabase-auth';

const getBase = () => {
  let apiUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  if (apiUrl.endsWith('/api')) apiUrl = apiUrl.slice(0, -4);
  if (typeof window !== 'undefined') {
    return apiUrl || '';
  }
  return apiUrl;
};

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { params?: Record<string, string> }
): Promise<T> {
  const base = getBase();
  const { params, ...rest } = options ?? {};
  const url = params
    ? `${base}${path}?${new URLSearchParams(params)}`
    : `${base}${path}`;

  const token = await getAccessToken();
  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const res = await fetch(url, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(rest.headers as Record<string, string>),
    },
  });

  if (res.status === 401 && token) {
    const freshToken = await refreshAccessToken();
    if (freshToken && freshToken !== token) {
      const retry = await fetch(url, {
        ...rest,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${freshToken}`,
          ...(rest.headers as Record<string, string>),
        },
      });
      if (retry.ok) return retry.json() as Promise<T>;
      const retryErr = await retry.json().catch(() => ({ detail: retry.statusText }));
      throw new Error((retryErr as { detail?: string }).detail || retry.statusText);
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

// --- Brand registration ---
export interface BrandRegisterPayload {
  user_id: string;
  brand_name: string;
  email: string;
  phone?: string;
  country?: string;
  shopify_domain?: string;
}

export async function registerBrand(payload: BrandRegisterPayload): Promise<{ ok: boolean; brand_id?: string; error?: string }> {
  try {
    return await fetchApi('/api/brand/register', { method: 'POST', body: JSON.stringify(payload) });
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'Brand registration failed' };
  }
}

export async function getMyBrand(userId: string): Promise<Record<string, unknown> | null> {
  try {
    const res: { ok: boolean; brand: Record<string, unknown> } = await fetchApi('/api/brand/me', { params: { user_id: userId } });
    return res.brand ?? null;
  } catch {
    return null;
  }
}

export async function isBackendAvailable(): Promise<boolean> {
  try {
    const base = getBase();
    const res = await fetch(`${base}/health`, { method: 'GET' });
    return res.ok;
  } catch {
    return false;
  }
}

// --- Addresses (Shopper Passport) ---
export interface UserAddress {
  id: string;
  user_id: string;
  label: string;
  name: string;
  line1: string;
  line2?: string | null;
  city: string;
  state?: string | null;
  postal_code: string;
  country: string;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AddressCreatePayload {
  user_id: string;
  label: string;
  name: string;
  line1: string;
  line2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
  is_default?: boolean;
}

// --- Analytics / Events ---
export interface TrackEventPayload {
  event_type: string;
  user_id?: string;
  session_id?: string;
  shop_domain?: string;
  product_id?: string;
  variant_id?: string;
  preferred_fit?: string;
  country?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateTryonSessionPayload {
  user_id?: string;
  shop_domain?: string;
  product_id?: string;
  product_name?: string;
  variant_id?: string;
}

// --- Analytics metrics (brand dashboard) ---
export interface AnalyticsMetrics {
  tryons_started?: number;
  add_to_carts?: number;
  purchases?: number;
  revenue?: number;
  unique_sessions?: number;
  tryon_atc_rate?: number | null;
  tryon_purchase_rate?: number | null;
  revenue_attributed?: number;
  revenue_per_tryon?: number | null;
  aov_tryon?: number | null;
  widget_opens?: number;
  open_to_tryon_rate?: number | null;
  cart_abandonment_rate?: number | null;
  avg_time_to_purchase_hours?: number | null;
  same_session_purchase_rate?: number | null;
  returns?: number;
  return_rate?: number | null;
  revenue_lost_to_returns?: number;
  bracket_orders?: number;
  bracket_rate?: number | null;
  [key: string]: unknown;
}

export interface FitMetrics {
  data?: unknown[];
  [key: string]: unknown;
}

export interface VelocityMetrics {
  data?: unknown[];
  [key: string]: unknown;
}

export interface AtRiskProductsResponse {
  data?: unknown[];
  [key: string]: unknown;
}

export interface ExplorationTrendPoint {
  date?: string;
  [key: string]: unknown;
}

export interface SizeStressItem {
  [key: string]: unknown;
}

export interface RegionalSizeData {
  [key: string]: unknown;
}

export interface MetricsByProductResponse {
  data?: unknown[];
  products?: unknown[];
  [key: string]: unknown;
}

// --- New analytics types ---
export interface DwellMetrics {
  total_sessions: number;
  avg_dwell_seconds?: number | null;
  median_dwell_seconds?: number | null;
  p90_dwell_seconds?: number | null;
  dwell_to_conversion?: number | null;
}

export interface DeviceMetric {
  device_type: string;
  tryons: number;
  add_to_carts: number;
  purchases: number;
  conversion_rate?: number | null;
}
export interface DeviceMetricsResponse {
  devices: DeviceMetric[];
  total_events: number;
}

export interface ProductFitConfidence {
  product_id: string;
  total_recommendations: number;
  acceptance_count: number;
  size_up_count: number;
  size_down_count: number;
  fit_confidence_score: number;
  most_common_deviation?: string | null;
}
export interface FitConfidenceResponse {
  products: ProductFitConfidence[];
}

export interface RepeatVisitorMetrics {
  unique_users: number;
  returning_users: number;
  returning_user_rate?: number | null;
  repeat_product_tryons: number;
  high_intent_users: number;
  high_intent_conversion_rate?: number | null;
}
export interface RepeatVisitorsResponse {
  metrics: RepeatVisitorMetrics;
  top_repeated_products: Array<{ product_id: string; repeat_count: number; converted: boolean }>;
}

export interface BodyShapeInsight {
  product_id: string;
  measurement_group: string;
  recommended_size: string;
  actual_purchased_size: string;
  deviation: string;
  shopper_count: number;
}
export interface BodyShapeInsightsResponse {
  insights: BodyShapeInsight[];
  total_data_points: number;
}

export interface SkuMetricRow {
  sku: string;
  variant_id: string;
  product_id: string;
  title: string;
  return_count: number;
  purchase_count: number;
  return_rate?: number | null;
}

export interface ReturnMetricsData {
  total_purchases: number;
  total_returns: number;
  return_rate?: number | null;
  revenue_lost: number;
  top_returned_products: SkuMetricRow[];
  sku_breakdown?: SkuMetricRow[];
  avg_days_to_return?: number | null;
}

export interface CohortComparisonData {
  tryon_users_count: number;
  tryon_purchases: number;
  tryon_returns: number;
  tryon_aov?: number | null;
  tryon_return_rate?: number | null;
  tryon_conversion_rate?: number | null;
  tryon_bracket_rate?: number | null;
  baseline_note?: string;
}

export interface OrderReturnRisk {
  order_id: string;
  session_id?: string | null;
  risk_score: number;
  risk_factors: string[];
  product_id?: string | null;
}
export interface ReturnRiskResponse {
  high_risk_orders: OrderReturnRisk[];
  avg_risk_score?: number | null;
  total_scored: number;
}

// --- Time-Series Trends ---
export interface TimeSeriesPoint {
  week_start: string;
  widget_opens: number;
  tryons: number;
  add_to_carts: number;
  purchases: number;
  returns: number;
  revenue: number;
  conversion_rate?: number | null;
  atc_rate?: number | null;
  return_rate?: number | null;
}
export interface TimeSeriesResponse {
  weeks: TimeSeriesPoint[];
}

// --- Fit-to-Purchase Correlation ---
export interface FitPurchaseCorrelationBucket {
  deviation: string;
  sessions: number;
  purchases: number;
  returns: number;
  purchase_rate?: number | null;
  return_rate?: number | null;
}
export interface FitPurchaseCorrelationResponse {
  buckets: FitPurchaseCorrelationBucket[];
  total_sessions_with_recommendation: number;
  overall_acceptance_rate?: number | null;
}

// --- Avatar ---
export interface CreateAvatarPayload {
  user_id: string;
  photo_url: string;
  height: number;
  weight?: number;
  gender: string;
}

export interface CreateAvatarResult {
  success: boolean;
  avatarUrl?: string;
  measurements?: {
    height?: number;
    chest?: number;
    waist?: number;
    hips?: number;
    inseam?: number;
    [key: string]: number | undefined;
  };
  error?: string;
}

export const api = {
  async getAddresses(userId: string): Promise<{ addresses: UserAddress[] }> {
    return fetchApi(`/api/addresses?user_id=${encodeURIComponent(userId)}`);
  },

  async createAddress(payload: AddressCreatePayload): Promise<{ address: UserAddress }> {
    return fetchApi('/api/addresses', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateAddress(
    addressId: string,
    payload: Partial<AddressCreatePayload> & { user_id: string }
  ): Promise<{ address: UserAddress }> {
    return fetchApi(`/api/addresses/${addressId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteAddress(addressId: string, userId: string): Promise<{ success: boolean }> {
    return fetchApi(`/api/addresses/${addressId}?user_id=${encodeURIComponent(userId)}`, {
      method: 'DELETE',
    });
  },

  async trackEvent(payload: TrackEventPayload): Promise<{ success: boolean; event_id?: string }> {
    return fetchApi('/api/events/track', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async createTryonSession(payload: CreateTryonSessionPayload): Promise<{
    session_id: string;
    session_token: string;
  }> {
    return fetchApi('/api/events/tryon-session', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getAvatar(userId: string): Promise<{
    user_id: string;
    avatar_url: string;
    measurements?: Record<string, number | undefined>;
    [key: string]: unknown;
  }> {
    return fetchApi(`/api/avatar/${encodeURIComponent(userId)}`);
  },

  async getProductTryonConfig(
    productId: string,
    opts?: { baseUrl?: string; shop?: string; user_id?: string }
  ): Promise<{
    product_id: string;
    model_urls: Record<string, string>;
    size_chart: Record<string, Record<string, number>>;
    model_type?: string;
    category?: string;
    fit_type?: string;
    draped_urls?: Record<string, string> | null;
    has_obj?: boolean;
    garment_id?: string | null;
    draping_available?: boolean;
  }> {
    const params: Record<string, string> = {};
    if (opts?.baseUrl) params.base_url = opts.baseUrl;
    if (opts?.shop) params.shop = opts.shop;
    if (opts?.user_id) params.user_id = opts.user_id;
    return fetchApi(`/api/products/${encodeURIComponent(productId)}/tryon-config`, {
      params: Object.keys(params).length ? params : undefined,
    });
  },

  async getAnalyticsMetrics(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<AnalyticsMetrics> {
    return fetchApi('/api/analytics/metrics', { params: params as Record<string, string> });
  },

  async getFitMetrics(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<FitMetrics> {
    return fetchApi('/api/analytics/fit-metrics', { params: params as Record<string, string> });
  },

  async getVelocityMetrics(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<VelocityMetrics> {
    return fetchApi('/api/analytics/velocity', { params: params as Record<string, string> });
  },

  async getAtRiskProducts(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<AtRiskProductsResponse> {
    return fetchApi('/api/analytics/at-risk-products', { params: params as Record<string, string> });
  },

  async getExplorationTrend(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<{ data?: ExplorationTrendPoint[] }> {
    return fetchApi('/api/analytics/exploration-trend', { params: params as Record<string, string> });
  },

  async getSizeStress(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<{ data?: SizeStressItem[] }> {
    return fetchApi('/api/analytics/size-stress', { params: params as Record<string, string> });
  },

  async getRegionalSize(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<RegionalSizeData> {
    return fetchApi('/api/analytics/regional-size', { params: params as Record<string, string> });
  },

  async getMetricsByProduct(params: {
    start: string;
    end: string;
    shop?: string;
  }): Promise<MetricsByProductResponse> {
    return fetchApi('/api/analytics/metrics-by-product', {
      params: params as Record<string, string>,
    });
  },

  async getDwellMetrics(params: { start: string; end: string; shop?: string }): Promise<DwellMetrics> {
    return fetchApi('/api/analytics/dwell-metrics', { params: params as Record<string, string> });
  },

  async getDeviceMetrics(params: { start: string; end: string; shop?: string }): Promise<DeviceMetricsResponse> {
    return fetchApi('/api/analytics/device-metrics', { params: params as Record<string, string> });
  },

  async getFitConfidence(params: { start: string; end: string; shop?: string }): Promise<FitConfidenceResponse> {
    return fetchApi('/api/analytics/fit-confidence-by-product', { params: params as Record<string, string> });
  },

  async getRepeatVisitors(params: { start: string; end: string; shop?: string }): Promise<RepeatVisitorsResponse> {
    return fetchApi('/api/analytics/repeat-visitors', { params: params as Record<string, string> });
  },

  async getBodyShapeInsights(params: { start: string; end: string; shop?: string }): Promise<BodyShapeInsightsResponse> {
    return fetchApi('/api/analytics/body-shape-insights', { params: params as Record<string, string> });
  },

  async getReturnMetrics(params: { start: string; end: string; shop?: string }): Promise<ReturnMetricsData> {
    return fetchApi('/api/analytics/return-metrics', { params: params as Record<string, string> });
  },

  async getCohortComparison(params: { start: string; end: string; shop?: string }): Promise<CohortComparisonData> {
    return fetchApi('/api/analytics/cohort-comparison', { params: params as Record<string, string> });
  },

  async getTimeSeries(params: { start: string; end: string; shop?: string }): Promise<TimeSeriesResponse> {
    return fetchApi('/api/analytics/time-series', { params: params as Record<string, string> });
  },

  async getFitPurchaseCorrelation(params: { start: string; end: string; shop?: string }): Promise<FitPurchaseCorrelationResponse> {
    return fetchApi('/api/analytics/fit-purchase-correlation', { params: params as Record<string, string> });
  },

  async getReturnRisk(params: { shop?: string }): Promise<ReturnRiskResponse> {
    const p: Record<string, string> = {};
    if (params.shop) p.shop = params.shop;
    return fetchApi('/api/analytics/return-risk', { params: Object.keys(p).length ? p : undefined });
  },

  // --- Wishlist / Closet ---

  async getWishlist(listType?: 'wishlist' | 'closet'): Promise<{ items: SavedItem[] }> {
    const params: Record<string, string> = {};
    if (listType) params.list_type = listType;
    return fetchApi('/api/wishlist', { params: Object.keys(params).length ? params : undefined });
  },

  async addToWishlist(payload: WishlistAddPayload): Promise<{ item: SavedItem }> {
    return fetchApi('/api/wishlist', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async removeFromWishlist(itemId: string): Promise<{ ok: boolean }> {
    return fetchApi(`/api/wishlist/${itemId}`, { method: 'DELETE' });
  },

  async getWishlistStatus(productId: string, shop: string): Promise<{ wishlisted: boolean; owned: boolean }> {
    return fetchApi(`/api/wishlist/${encodeURIComponent(productId)}/status`, {
      params: { shop },
    });
  },
};

// --- Saved Items (Wishlist + Closet) ---
export interface SavedItem {
  id: string;
  user_id: string;
  list_type: 'wishlist' | 'closet';
  product_id: string;
  variant_id: string | null;
  shop_domain: string;
  product_name: string | null;
  product_image_url: string | null;
  product_price: number | null;
  currency: string;
  brand_name: string | null;
  created_at: string;
}

export interface WishlistAddPayload {
  product_id: string;
  shop_domain: string;
  variant_id?: string;
  product_name?: string;
  product_image_url?: string;
  product_price?: number;
  currency?: string;
  brand_name?: string;
}

// --- Garment Management ---
export interface Garment {
  id: string;
  brand_id: string;
  name: string;
  category: string | null;
  shopify_product_id: string | null;
  shopify_product_handle?: string | null;
  fit_type: string;
  sizes: Record<string, string>;
  size_chart: Record<string, Record<string, number>>;
  thumbnail_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const garmentApi = {
  async list(brandId: string): Promise<Garment[]> {
    const res: { garments: Garment[] } = await fetchApi('/api/garments', { params: { brand_id: brandId } });
    return res.garments || [];
  },

  async create(data: {
    brand_id: string;
    name: string;
    category?: string;
    shopify_product_id?: string;
    fit_type?: string;
    size_chart?: Record<string, Record<string, number>>;
  }): Promise<Garment> {
    const res: { garment: Garment } = await fetchApi('/api/garments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return res.garment;
  },

  async update(garmentId: string, data: {
    name?: string;
    category?: string;
    shopify_product_id?: string;
    fit_type?: string;
    size_chart?: Record<string, Record<string, number>>;
    is_active?: boolean;
  }): Promise<Garment> {
    const res: { garment: Garment } = await fetchApi(`/api/garments/${garmentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return res.garment;
  },

  async remove(garmentId: string): Promise<void> {
    await fetchApi(`/api/garments/${garmentId}`, { method: 'DELETE' });
  },

  async sync(garmentId: string): Promise<{ sizes: Record<string, string> }> {
    return fetchApi(`/api/garments/${garmentId}/sync`, { method: 'POST' });
  },

  async uploadGlb(garmentId: string, size: string, file: File): Promise<{ url: string }> {
    const base = getBase();
    const formData = new FormData();
    formData.append('size', size);
    formData.append('file', file);
    const tkn = await getAccessToken();
    const hdrs: Record<string, string> = {};
    if (tkn) hdrs['Authorization'] = `Bearer ${tkn}`;
    const res = await fetch(`${base}/api/garments/${garmentId}/upload`, {
      method: 'POST',
      body: formData,
      headers: hdrs,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((err as { detail?: string }).detail || res.statusText);
    }
    return res.json();
  },
};

/**
 * Upload photo via backend (uses service key, bypasses Supabase Storage RLS).
 */
export async function uploadPhotoViaBackend(
  userId: string,
  file: File,
): Promise<{ url: string | null; error: string | null }> {
  const base = getBase();
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId);

  const token = await getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(`${base}/api/avatar/upload-photo`, {
      method: 'POST',
      body: formData,
      headers,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      return { url: null, error: (err as { detail?: string }).detail || res.statusText };
    }
    const data = (await res.json()) as { url: string; path: string };
    return { url: data.url, error: null };
  } catch (e) {
    return { url: null, error: e instanceof Error ? e.message : 'Upload failed' };
  }
}

export async function createAvatarWithFallback(
  payload: CreateAvatarPayload,
  onProgress?: (progress: number, message: string) => void
): Promise<CreateAvatarResult> {
  const base = getBase();
  const token = await getAccessToken();
  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  try {
    const createRes = await fetch(`${base}/api/avatar/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({
        user_id: payload.user_id,
        photo_url: payload.photo_url,
        height: payload.height,
        weight: payload.weight ?? null,
        gender: payload.gender,
      }),
    });
    if (!createRes.ok) {
      const err = await createRes.json().catch(() => ({}));
      return {
        success: false,
        error: (err as { detail?: string }).detail || createRes.statusText,
      };
    }
    const { job_id } = (await createRes.json()) as { job_id: string };
    const maxAttempts = 300;
    const intervalMs = 2000;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, intervalMs));
      const statusRes = await fetch(`${base}/api/avatar/status/${job_id}`);
      if (!statusRes.ok) continue;
      const status = (await statusRes.json()) as {
        status: string;
        progress?: number;
        message?: string;
        avatar_url?: string;
        measurements?: Record<string, number>;
        error?: string;
      };
      onProgress?.(status.progress ?? 0, status.message ?? '');
      if (status.status === 'completed') {
        return {
          success: true,
          avatarUrl: status.avatar_url,
          measurements: status.measurements ?? undefined,
        };
      }
      if (status.status === 'failed') {
        return {
          success: false,
          error: status.error ?? 'Avatar creation failed',
        };
      }
    }
    return { success: false, error: 'Avatar creation timed out' };
  } catch (e) {
    return {
      success: false,
      error: e instanceof Error ? e.message : 'Avatar creation failed',
    };
  }
}
