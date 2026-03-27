-- ============================================================
-- TryOn Analytics RPC Functions
-- Run this in Supabase Dashboard > SQL Editor BEFORE deploying
-- the updated backend code.
-- ============================================================

-- 1. analytics_metrics
--    Returns: tryons_started, add_to_carts, purchases, revenue,
--             unique_sessions, aov (attributed within 30-day window)
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_metrics(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL,
  p_brand_id text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  -- Extend end by 30 days for attribution window
  params AS (
    SELECT p_start AS range_start,
           p_end   AS range_end,
           p_end + interval '30 days' AS range_end_extended
  ),
  -- Cohort: sessions with tryon_started in [start, end]
  cohort AS (
    SELECT session_id,
           MIN(created_at) AS first_tryon
    FROM analytics_events, params
    WHERE event_type = 'tryon_started'
      AND created_at >= params.range_start
      AND created_at <= params.range_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
      AND (p_brand_id IS NULL OR brand_id = p_brand_id)
      AND session_id IS NOT NULL
    GROUP BY session_id
  ),
  -- Conversions within attribution window
  attributed AS (
    SELECT e.event_type,
           e.session_id,
           e.event_data,
           e.created_at
    FROM analytics_events e
    JOIN cohort c ON e.session_id = c.session_id
    CROSS JOIN params
    WHERE e.created_at >= params.range_start
      AND e.created_at <= c.first_tryon + interval '30 days'
      AND (p_shop IS NULL OR e.shop_domain = p_shop)
      AND (p_brand_id IS NULL OR e.brand_id = p_brand_id)
  ),
  counts AS (
    SELECT
      (SELECT COUNT(DISTINCT session_id) FROM cohort) AS tryons_started,
      (SELECT COUNT(DISTINCT session_id) FROM attributed WHERE event_type = 'add_to_cart') AS add_to_carts,
      (SELECT COUNT(*) FROM attributed WHERE event_type = 'purchase') AS purchases,
      (SELECT COALESCE(SUM((event_data->>'amount')::numeric), 0) FROM attributed WHERE event_type = 'purchase') AS revenue,
      (SELECT COUNT(DISTINCT COALESCE(event_data->>'order_id', '')) FROM attributed WHERE event_type = 'purchase' AND event_data->>'order_id' IS NOT NULL) AS unique_orders,
      (SELECT COUNT(DISTINCT session_id) FROM cohort) AS unique_sessions
  )
  SELECT json_build_object(
    'tryons_started', c.tryons_started,
    'add_to_carts', c.add_to_carts,
    'purchases', c.purchases,
    'revenue_attributed', ROUND(c.revenue::numeric, 2),
    'unique_sessions', c.unique_sessions,
    'tryon_atc_rate', CASE WHEN c.tryons_started > 0 THEN ROUND(c.add_to_carts::numeric / c.tryons_started, 4) ELSE NULL END,
    'tryon_purchase_rate', CASE WHEN c.tryons_started > 0 THEN ROUND(c.purchases::numeric / c.tryons_started, 4) ELSE NULL END,
    'revenue_per_tryon', CASE WHEN c.tryons_started > 0 THEN ROUND(c.revenue / c.tryons_started, 2) ELSE NULL END,
    'aov_tryon', CASE WHEN c.unique_orders > 0 THEN ROUND(c.revenue / c.unique_orders, 2)
                      WHEN c.purchases > 0 THEN ROUND(c.revenue / c.purchases, 2)
                      ELSE NULL END
  ) INTO result
  FROM counts c;

  RETURN result;
END;
$$;


-- 2. analytics_metrics_by_product
--    Returns: array of per-product metrics with attribution
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_metrics_by_product(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL,
  p_brand_id text DEFAULT NULL,
  p_product_id text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  cohort AS (
    SELECT session_id, product_id,
           MIN(created_at) AS first_tryon
    FROM analytics_events
    WHERE event_type = 'tryon_started'
      AND created_at >= p_start
      AND created_at <= p_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
      AND (p_brand_id IS NULL OR brand_id = p_brand_id)
      AND (p_product_id IS NULL OR product_id = p_product_id)
      AND session_id IS NOT NULL
      AND product_id IS NOT NULL AND TRIM(product_id) != ''
    GROUP BY session_id, product_id
  ),
  tryon_counts AS (
    SELECT product_id,
           COUNT(DISTINCT session_id) AS tryons
    FROM cohort
    GROUP BY product_id
  ),
  atc_counts AS (
    SELECT c.product_id,
           COUNT(DISTINCT e.session_id) AS atcs
    FROM analytics_events e
    JOIN cohort c ON e.session_id = c.session_id AND e.product_id = c.product_id
    WHERE e.event_type = 'add_to_cart'
      AND e.created_at <= c.first_tryon + interval '30 days'
      AND (p_shop IS NULL OR e.shop_domain = p_shop)
    GROUP BY c.product_id
  ),
  purchase_counts AS (
    SELECT c.product_id,
           COUNT(*) AS purchases,
           COALESCE(SUM((e.event_data->>'amount')::numeric), 0) AS revenue,
           COUNT(DISTINCT e.event_data->>'order_id') FILTER (WHERE e.event_data->>'order_id' IS NOT NULL) AS unique_orders
    FROM analytics_events e
    JOIN cohort c ON e.session_id = c.session_id
    WHERE e.event_type = 'purchase'
      AND e.created_at <= c.first_tryon + interval '30 days'
      AND (p_shop IS NULL OR e.shop_domain = p_shop)
    GROUP BY c.product_id
  ),
  combined AS (
    SELECT
      t.product_id,
      t.tryons,
      COALESCE(a.atcs, 0) AS add_to_carts,
      COALESCE(p.purchases, 0) AS purchases,
      COALESCE(p.revenue, 0) AS revenue_attributed,
      COALESCE(p.unique_orders, 0) AS unique_orders
    FROM tryon_counts t
    LEFT JOIN atc_counts a ON t.product_id = a.product_id
    LEFT JOIN purchase_counts p ON t.product_id = p.product_id
  )
  SELECT json_agg(
    json_build_object(
      'product_id', c.product_id,
      'tryons_started', c.tryons,
      'add_to_carts', c.add_to_carts,
      'purchases', c.purchases,
      'revenue_attributed', ROUND(c.revenue_attributed::numeric, 2),
      'tryon_atc_rate', CASE WHEN c.tryons > 0 THEN ROUND(c.add_to_carts::numeric / c.tryons, 4) ELSE NULL END,
      'tryon_purchase_rate', CASE WHEN c.tryons > 0 THEN ROUND(c.purchases::numeric / c.tryons, 4) ELSE NULL END,
      'revenue_per_tryon', CASE WHEN c.tryons > 0 THEN ROUND(c.revenue_attributed / c.tryons, 2) ELSE NULL END,
      'aov_tryon', CASE WHEN c.unique_orders > 0 THEN ROUND(c.revenue_attributed / c.unique_orders, 2)
                        WHEN c.purchases > 0 THEN ROUND(c.revenue_attributed / c.purchases, 2)
                        ELSE NULL END
    ) ORDER BY c.revenue_attributed DESC, c.tryons DESC
  ) INTO result
  FROM combined c;

  RETURN COALESCE(result, '[]'::json);
END;
$$;


-- 3. analytics_velocity
--    Returns: 7d and 30d tryon/purchase counts and ratios
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_velocity(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  cutoff_7d AS (
    SELECT p_end - interval '7 days' AS ts
  ),
  base AS (
    SELECT event_type, session_id, created_at
    FROM analytics_events
    WHERE created_at >= p_start
      AND created_at <= p_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
  )
  SELECT json_build_object(
    'tryon_velocity_7d',   (SELECT COUNT(*) FROM base, cutoff_7d WHERE event_type = 'tryon_started' AND created_at >= cutoff_7d.ts),
    'tryon_velocity_30d',  (SELECT COUNT(*) FROM base WHERE event_type = 'tryon_started'),
    'purchase_velocity_7d',(SELECT COUNT(*) FROM base, cutoff_7d WHERE event_type = 'purchase' AND created_at >= cutoff_7d.ts),
    'purchase_velocity_30d',(SELECT COUNT(*) FROM base WHERE event_type = 'purchase'),
    'tryon_sessions_7d',   (SELECT COUNT(DISTINCT session_id) FROM base, cutoff_7d WHERE event_type = 'tryon_started' AND created_at >= cutoff_7d.ts AND session_id IS NOT NULL),
    'purchase_sessions_7d',(SELECT COUNT(DISTINCT session_id) FROM base, cutoff_7d WHERE event_type = 'purchase' AND created_at >= cutoff_7d.ts AND session_id IS NOT NULL),
    'velocity_ratio_7d',   (SELECT CASE WHEN t > 0 THEN ROUND(p::numeric / t, 4) ELSE NULL END
                             FROM (SELECT COUNT(*) FILTER (WHERE event_type = 'tryon_started' AND created_at >= (SELECT ts FROM cutoff_7d)) AS t,
                                          COUNT(*) FILTER (WHERE event_type = 'purchase' AND created_at >= (SELECT ts FROM cutoff_7d)) AS p FROM base) x),
    'velocity_ratio_30d',  (SELECT CASE WHEN t > 0 THEN ROUND(p::numeric / t, 4) ELSE NULL END
                             FROM (SELECT COUNT(*) FILTER (WHERE event_type = 'tryon_started') AS t,
                                          COUNT(*) FILTER (WHERE event_type = 'purchase') AS p FROM base) x)
  ) INTO result;

  RETURN result;
END;
$$;


-- 4. analytics_at_risk
--    Returns: products with high try-on but low conversion
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_at_risk(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL,
  p_min_tryons int DEFAULT 5,
  p_conversion_threshold numeric DEFAULT 0.05
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  base AS (
    SELECT event_type, product_id, session_id, event_data
    FROM analytics_events
    WHERE created_at >= p_start
      AND created_at <= p_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
  ),
  session_product AS (
    SELECT session_id, product_id
    FROM base
    WHERE event_type = 'tryon_started'
      AND session_id IS NOT NULL
      AND product_id IS NOT NULL AND TRIM(product_id) != ''
  ),
  tryon_by_product AS (
    SELECT product_id, COUNT(*) AS tryons
    FROM base
    WHERE event_type = 'tryon_started'
      AND product_id IS NOT NULL AND TRIM(product_id) != ''
    GROUP BY product_id
  ),
  purchase_by_product AS (
    SELECT sp.product_id, COUNT(DISTINCT b.session_id) AS purchases
    FROM base b
    JOIN session_product sp ON b.session_id = sp.session_id
    WHERE b.event_type = 'purchase'
    GROUP BY sp.product_id
  ),
  combined AS (
    SELECT
      t.product_id,
      t.tryons,
      COALESCE(p.purchases, 0) AS purchases,
      CASE WHEN t.tryons > 0 THEN ROUND(COALESCE(p.purchases, 0)::numeric / t.tryons, 4) ELSE 0 END AS conversion
    FROM tryon_by_product t
    LEFT JOIN purchase_by_product p ON t.product_id = p.product_id
    WHERE t.tryons >= p_min_tryons
  ),
  flagged AS (
    SELECT *,
      CASE
        WHEN purchases = 0 THEN 'critical'
        WHEN conversion < p_conversion_threshold THEN 'warning'
        WHEN conversion < 0.10 THEN 'watch'
        ELSE NULL
      END AS severity
    FROM combined
  )
  SELECT COALESCE(json_agg(
    json_build_object(
      'product_id', f.product_id,
      'tryons', f.tryons,
      'purchases', f.purchases,
      'conversion', f.conversion,
      'severity', f.severity
    ) ORDER BY f.tryons DESC, f.purchases ASC
  ), '[]'::json) INTO result
  FROM flagged f
  WHERE f.severity IS NOT NULL;

  RETURN result;
END;
$$;


-- 5. analytics_fit_metrics
--    Returns: size distributions and accuracy rates
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_fit_metrics(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL,
  p_brand_id text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  base AS (
    SELECT event_type, session_id, event_data
    FROM analytics_events
    WHERE created_at >= p_start
      AND created_at <= p_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
      AND (p_brand_id IS NULL OR brand_id = p_brand_id)
  ),
  recommended AS (
    SELECT session_id,
           UPPER(TRIM(event_data->>'size')) AS size_key,
           LOWER(TRIM(event_data->>'size')) AS size_raw
    FROM base
    WHERE event_type = 'size_recommended'
      AND event_data->>'size' IS NOT NULL
      AND TRIM(event_data->>'size') != ''
      AND session_id IS NOT NULL
  ),
  selected AS (
    SELECT session_id,
           UPPER(TRIM(event_data->>'size')) AS size_key
    FROM base
    WHERE event_type IN ('size_selected', 'add_to_cart')
      AND event_data->>'size' IS NOT NULL
      AND TRIM(event_data->>'size') != ''
      AND session_id IS NOT NULL
  ),
  dist_rec AS (
    SELECT size_key, COUNT(*) AS cnt FROM recommended GROUP BY size_key
  ),
  dist_sel AS (
    SELECT size_key, COUNT(*) AS cnt FROM selected GROUP BY size_key
  ),
  first_rec AS (
    SELECT DISTINCT ON (session_id) session_id, size_raw
    FROM recommended
    ORDER BY session_id
  ),
  first_sel AS (
    SELECT DISTINCT ON (session_id) session_id, size_key AS size_raw
    FROM selected
    ORDER BY session_id
  )
  SELECT json_build_object(
    'size_distribution_recommended', COALESCE((SELECT json_object_agg(size_key, cnt) FROM dist_rec), '{}'::json),
    'size_distribution_selected', COALESCE((SELECT json_object_agg(size_key, cnt) FROM dist_sel), '{}'::json),
    'size_distribution_purchased', '{}'::json,
    'sessions_with_recommendation', (SELECT COUNT(*) FROM first_rec),
    'sessions_with_purchase_and_size', 0,
    'acceptance_rate', NULL,
    'size_up_rate', NULL,
    'size_down_rate', NULL,
    'mase', NULL
  ) INTO result;

  RETURN result;
END;
$$;


-- 6. analytics_regional_size
--    Returns: size counts grouped by country and city
-- ============================================================
CREATE OR REPLACE FUNCTION analytics_regional_size(
  p_start timestamptz,
  p_end   timestamptz,
  p_shop  text DEFAULT NULL,
  p_brand_id text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  result json;
BEGIN
  WITH
  base AS (
    SELECT event_type, event_data, COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
           INITCAP(TRIM(city)) AS city
    FROM analytics_events
    WHERE created_at >= p_start
      AND created_at <= p_end
      AND (p_shop IS NULL OR shop_domain = p_shop)
      AND (p_brand_id IS NULL OR brand_id = p_brand_id)
  ),
  size_events AS (
    SELECT country, city,
           CASE WHEN LENGTH(TRIM(event_data->>'size')) <= 3
                THEN UPPER(TRIM(event_data->>'size'))
                ELSE TRIM(event_data->>'size')
           END AS size_key
    FROM base
    WHERE event_type IN ('size_recommended', 'size_selected', 'size_viewed')
      AND event_data->>'size' IS NOT NULL
      AND TRIM(event_data->>'size') != ''

    UNION ALL

    SELECT country, city,
           CASE WHEN LENGTH(TRIM(item->>'size')) <= 3
                THEN UPPER(TRIM(item->>'size'))
                ELSE TRIM(item->>'size')
           END AS size_key
    FROM base,
         json_array_elements(CASE WHEN event_data ? 'items' THEN (event_data->'items') ELSE '[]'::json END) AS item
    WHERE event_type = 'purchase'
      AND item->>'size' IS NOT NULL
      AND TRIM(item->>'size') != ''
  ),
  country_agg AS (
    SELECT country, size_key, COUNT(*) AS cnt
    FROM size_events
    GROUP BY country, size_key
  ),
  country_totals AS (
    SELECT country, SUM(cnt) AS total
    FROM country_agg
    GROUP BY country
  ),
  city_agg AS (
    SELECT country, city, size_key, COUNT(*) AS cnt
    FROM size_events
    WHERE city IS NOT NULL AND city != ''
    GROUP BY country, city, size_key
  ),
  city_totals AS (
    SELECT country, city, SUM(cnt) AS total
    FROM city_agg
    GROUP BY country, city
  ),
  city_json AS (
    SELECT ca.country, ca.city, ct.total,
           json_object_agg(ca.size_key, ca.cnt) AS raw,
           json_object_agg(ca.size_key, ROUND(ca.cnt::numeric / ct.total, 4)) AS pcts,
           (ARRAY_AGG(ca.size_key ORDER BY ca.cnt DESC))[1] AS top_size
    FROM city_agg ca
    JOIN city_totals ct ON ca.country = ct.country AND ca.city = ct.city
    GROUP BY ca.country, ca.city, ct.total
  )
  SELECT json_build_object(
    'raw_counts', COALESCE((
      SELECT json_object_agg(ca.country, ca.sizes)
      FROM (
        SELECT country, json_object_agg(size_key, cnt) AS sizes
        FROM country_agg GROUP BY country
      ) ca
    ), '{}'::json),
    'by_country', COALESCE((
      SELECT json_object_agg(sub.country, sub.pcts)
      FROM (
        SELECT ca.country,
               json_object_agg(ca.size_key, ROUND(ca.cnt::numeric / ct.total, 4)) AS pcts
        FROM country_agg ca
        JOIN country_totals ct ON ca.country = ct.country
        GROUP BY ca.country
      ) sub
    ), '{}'::json),
    'top_size_by_country', COALESCE((
      SELECT json_object_agg(sub.country, sub.top_size)
      FROM (
        SELECT DISTINCT ON (country) country, size_key AS top_size
        FROM country_agg
        ORDER BY country, cnt DESC
      ) sub
    ), '{}'::json),
    'by_city', COALESCE((
      SELECT json_object_agg(sub.country, sub.cities)
      FROM (
        SELECT cj.country,
               json_object_agg(cj.city, json_build_object(
                 'sizes', cj.pcts,
                 'raw_counts', cj.raw,
                 'total', cj.total,
                 'top_size', cj.top_size
               )) AS cities
        FROM city_json cj
        GROUP BY cj.country
      ) sub
    ), '{}'::json)
  ) INTO result;

  RETURN result;
END;
$$;


-- ============================================================
-- Recommended indexes for analytics_events (run if not exists)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events (created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_shop_created ON analytics_events (shop_domain, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_created ON analytics_events (event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_brand_created ON analytics_events (brand_id, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events (session_id);
