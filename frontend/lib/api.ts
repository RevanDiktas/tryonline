/**
 * Frontend API client — calls backend via /api/* (Next.js rewrites to NEXT_PUBLIC_API_URL).
 */
import { getAccessToken } from './supabase-auth';

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
    baseUrl?: string
  ): Promise<{
    product_id: string;
    model_urls: Record<string, string>;
    size_chart: Record<string, Record<string, number>>;
    model_type?: string;
  }> {
    const params = baseUrl ? { base_url: baseUrl } : undefined;
    return fetchApi(`/api/products/${encodeURIComponent(productId)}/tryon-config`, {
      params,
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
};

// --- Garment Management ---
export interface Garment {
  id: string;
  brand_id: string;
  name: string;
  category: string | null;
  shopify_product_id: string | null;
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
