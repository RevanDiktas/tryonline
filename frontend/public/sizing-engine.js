/**
 * Sizing engine — SINGLE SOURCE OF TRUTH.
 *
 * Plain ES module (no framework, no TypeScript) so it can be shared by BOTH:
 *   - the Next app  (frontend/lib/sizeRecommendation.ts re-exports this with types), and
 *   - the live PDP widget (frontend/public/test-viewer.html imports it directly).
 *
 * Previously this logic was duplicated between those two files and hand-synced on every change,
 * which is exactly how the live store drifted (the 192cm/85kg -> S bug). Keep it here only.
 *
 * Body anchoring: the garment's own measurements can't tell us a shopper's native size — an
 * intentionally oversized M jacket has a 130cm chest. So we anchor on the shopper's REAL body
 * against a standard adult scale, pick their native size, then map to the garment's matching
 * label. The garment's designed fit (oversized/slim) is communicated in copy, never used to
 * shrink/grow the recommended size.
 */

// Girth fields are measured around the body, so a flat-chart value is half the real value.
export const GIRTH_FIELDS = new Set(['chest', 'waist', 'hips', 'thigh', 'neck']);

// Structural fields are point-to-point length/width matches (shoulder seam, sleeve, inseam),
// scored toward ~0 ease — never doubled, never scored against a girth ease target.
export const STRUCTURAL_FIELDS = new Set([
  'shoulder_width', 'shoulder', 'arm_length', 'sleeve', 'inseam', 'torso_length',
]);

// Alpha master scale used for body anchoring (BODY_SIZE_SCALE bands are keyed XS..XXL).
export const SIZE_ORDER = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL'];

// ---------------------------------------------------------------------------
// Size systems
//
// A garment is sold in ONE system (letters OR a numeric/EU range). The size labels stored as
// the keys of size_chart / sizes are the source of truth, so the system is inferred from those
// keys + gender (no extra column). Every system maps onto the SAME 0..7 ordinal scale
// (0=XXS … 7=XXXL) so the body-anchored recommender is identical across systems — a Women-EU 38
// and a Men-EU 48 both anchor to ordinal 3 (≈ M).
// ---------------------------------------------------------------------------

export const SIZE_SYSTEMS = {
  alpha:    { label: 'Letter (XXS–XXXL)', sizes: ['xxs', 'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl'] },
  women_eu: { label: 'Women (EU 32–46)',  sizes: ['32', '34', '36', '38', '40', '42', '44', '46'] },
  men_eu:   { label: 'Men (EU 44–58)',    sizes: ['44', '46', '48', '50', '52', '54', '56', '58'] },
};

const SIZE_ORDINALS = {
  alpha:    { xxs: 0, xs: 1, s: 2, m: 3, l: 4, xl: 5, xxl: 6, xxxl: 7, '3xl': 7, '4xl': 8 },
  women_eu: { '32': 0, '34': 1, '36': 2, '38': 3, '40': 4, '42': 5, '44': 6, '46': 7 },
  men_eu:   { '44': 1, '46': 2, '48': 3, '50': 4, '52': 5, '54': 6, '56': 7, '58': 8 },
};

// Infer a garment's size system from its labels + gender. Women EU (32–46) and Men EU (44–58)
// only overlap at 44/46; gender breaks the tie. Non-numeric labels are always letters.
export function inferSizeSystem(labels, gender) {
  const keys = (labels || []).map((l) => String(l).toLowerCase().trim()).filter(Boolean);
  if (!keys.length || !keys.every((k) => /^\d+$/.test(k))) return 'alpha';
  if (gender === 'male') return 'men_eu';
  if (gender === 'female') return 'women_eu';
  // Unknown gender: men's run 44+ and skew higher; women's top out at 46.
  const nums = keys.map(Number);
  return Math.min.apply(null, nums) >= 48 || Math.max.apply(null, nums) >= 50 ? 'men_eu' : 'women_eu';
}

export function sizeToOrdinal(size, system) {
  const key = String(size).toLowerCase().trim();
  const map = SIZE_ORDINALS[system] || SIZE_ORDINALS.alpha;
  if (map[key] != null) return map[key];
  if (SIZE_ORDINALS.alpha[key] != null) return SIZE_ORDINALS.alpha[key]; // letter fallback
  return 3; // default M
}

// Reverse lookup: ordinal -> the system's label (for human-readable reasoning).
export function ordinalToLabel(ord, system) {
  const map = SIZE_ORDINALS[system] || SIZE_ORDINALS.alpha;
  const hit = Object.keys(map).find((k) => map[k] === ord);
  return (hit || 'm').toUpperCase();
}

// ---------------------------------------------------------------------------
// Measurement weights per garment category (higher = more important for that type).
// ---------------------------------------------------------------------------

export const CATEGORY_WEIGHTS = {
  tops: {
    chest: 1.0, shoulder_width: 0.8, shoulder: 0.8, waist: 0.5, hips: 0.2,
    arm_length: 0.3, sleeve: 0.3, neck: 0.3, torso_length: 0.2,
  },
  bottoms: {
    waist: 1.0, hips: 0.9, inseam: 0.7, thigh: 0.6, chest: 0.0, shoulder_width: 0.0, shoulder: 0.0,
  },
  outerwear: {
    chest: 1.0, shoulder_width: 0.9, shoulder: 0.9, waist: 0.4, hips: 0.3,
    arm_length: 0.5, sleeve: 0.5, neck: 0.2,
  },
  dresses: {
    chest: 0.8, waist: 0.9, hips: 1.0, shoulder_width: 0.5, shoulder: 0.5,
    torso_length: 0.3, arm_length: 0.2, sleeve: 0.2,
  },
  accessories: { chest: 0.5, waist: 0.5, hips: 0.5 },
};

export const DEFAULT_WEIGHTS = {
  chest: 0.8, waist: 0.7, hips: 0.7, inseam: 0.4, shoulder_width: 0.5, shoulder: 0.5,
  arm_length: 0.3, sleeve: 0.3, thigh: 0.3, neck: 0.2, torso_length: 0.2,
};

// Ideal ease profiles (cm) per category × fit type. [min, ideal, max].
export const EASE_PROFILES = {
  tops: {
    slim: { min: 2, ideal: 5, max: 8 }, regular: { min: 5, ideal: 8, max: 12 }, oversized: { min: 10, ideal: 15, max: 22 },
  },
  bottoms: {
    slim: { min: 0, ideal: 2, max: 5 }, regular: { min: 2, ideal: 5, max: 8 }, oversized: { min: 6, ideal: 10, max: 16 },
  },
  outerwear: {
    slim: { min: 6, ideal: 10, max: 14 }, regular: { min: 10, ideal: 14, max: 20 }, oversized: { min: 16, ideal: 22, max: 30 },
  },
  dresses: {
    slim: { min: 1, ideal: 4, max: 7 }, regular: { min: 4, ideal: 7, max: 11 }, oversized: { min: 8, ideal: 13, max: 20 },
  },
  accessories: {
    slim: { min: 0, ideal: 3, max: 6 }, regular: { min: 3, ideal: 6, max: 10 }, oversized: { min: 6, ideal: 10, max: 16 },
  },
};

// User's preferred fit shifts the ease target (used only for the descriptive ease feel).
export const PREFERRED_FIT_SHIFT = { slim: -3, regular: 0, loose: 3 };

// ---------------------------------------------------------------------------
// True-to-fit core: standard body -> native size scale.
// Upper bound (cm, body circumference) of each size band per gender.
// ---------------------------------------------------------------------------

export const BODY_SIZE_SCALE = {
  male: {
    chest: { XS: 90, S: 98, M: 106, L: 114, XL: 122, XXL: 130 },
    waist: { XS: 74, S: 82, M: 90, L: 98, XL: 106, XXL: 114 },
    hips:  { XS: 90, S: 98, M: 104, L: 110, XL: 117, XXL: 124 },
  },
  female: {
    chest: { XS: 80, S: 86, M: 92, L: 100, XL: 108, XXL: 116 },
    waist: { XS: 64, S: 70, M: 78, L: 86, XL: 94, XXL: 102 },
    hips:  { XS: 88, S: 94, M: 100, L: 108, XL: 116, XXL: 124 },
  },
  unisex: {
    chest: { XS: 85, S: 92, M: 99, L: 107, XL: 115, XXL: 123 },
    waist: { XS: 69, S: 76, M: 84, L: 92, XL: 100, XXL: 108 },
    hips:  { XS: 89, S: 96, M: 102, L: 109, XL: 116, XXL: 124 },
  },
};

export const NATIVE_SCALE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

// Typical wearer height (cm) at the centre of each size: a build much taller than their
// girth-size's typical wearer needs the next size up for length (tall-and-lean problem).
export const EXPECTED_HEIGHT_BY_SIZE = {
  male:   { XS: 168, S: 173, M: 178, L: 183, XL: 188, XXL: 193 },
  female: { XS: 158, S: 163, M: 168, L: 173, XL: 178, XXL: 183 },
  unisex: { XS: 163, S: 168, M: 173, L: 178, XL: 183, XXL: 188 },
};

// Which body measurement anchors native size for each garment category.
export const CATEGORY_ANCHOR = {
  tops: 'chest', outerwear: 'chest', dresses: 'chest', bottoms: 'waist', accessories: 'chest',
};

// Preference shifts the NATIVE size by whole sizes (true-to-fit philosophy).
export const PREFERRED_FIT_SIZE_SHIFT = { slim: -1, regular: 0, loose: 1 };

// Map a shopper's real body measurements to their native size ORDINAL (index into SIZE_ORDER).
// Returns null if the anchoring measurement is missing.
export function nativeSizeOrdinal(measurements, category, gender) {
  const scale = BODY_SIZE_SCALE[gender] || BODY_SIZE_SCALE.unisex;
  const anchorKey = CATEGORY_ANCHOR[category] || 'chest';
  const measMap = measurements || {};
  let value = measMap[anchorKey];
  let usedKey = anchorKey;

  // Fallback chain: bottoms can fall back to hips, tops to waist.
  if (value == null) {
    const fallback = anchorKey === 'waist' ? 'hips' : 'waist';
    value = measMap[fallback];
    usedKey = fallback;
  }
  if (value == null) return null;

  // 1. Girth-based size from the anchor measurement.
  const band = scale[usedKey];
  let girthOrdinal = SIZE_ORDER.indexOf('XXL'); // default if larger than every band
  for (const sz of NATIVE_SCALE_ORDER) {
    const bound = band[sz];
    if (bound != null && value <= bound) { girthOrdinal = SIZE_ORDER.indexOf(sz); break; }
  }

  // 2. Frame / length nudge: size up a notably tall build (never down).
  let heightBump = 0;
  const height = measMap['height'];
  const expected = EXPECTED_HEIGHT_BY_SIZE[gender] && EXPECTED_HEIGHT_BY_SIZE[gender][SIZE_ORDER[girthOrdinal]];
  if (height != null && expected != null) {
    const over = height - expected;
    if (over > 20) heightBump = 2;
    else if (over > 6) heightBump = 1;
  }

  return { ordinal: girthOrdinal + heightBump, girthOrdinal, anchorKey: usedKey, anchorValue: value, heightBump };
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

// Score a girth ease against the target profile. 0–1. Tightness penalised 1.5x vs excess room.
export function scoreMeasurementEase(ease, profile, preferredShift) {
  const targetMin = profile.min + preferredShift;
  const targetIdeal = profile.ideal + preferredShift;
  const targetMax = profile.max + preferredShift;
  if (ease >= targetMin && ease <= targetMax) {
    const maxDist = Math.max(targetIdeal - targetMin, targetMax - targetIdeal);
    const dist = Math.abs(ease - targetIdeal);
    return maxDist > 0 ? 1 - (dist / maxDist) * 0.3 : 1;
  }
  if (ease < targetMin) {
    const deficit = targetMin - ease;
    return Math.max(0, 1 - (deficit / 10) * 1.5);
  }
  const excess = ease - targetMax;
  return Math.max(0, 1 - (excess / 15));
}

// Score a structural/linear measurement (shoulder, sleeve, inseam, torso) toward ~0 ease.
export function scoreStructuralMatch(ease) {
  const TOL = 3;
  if (Math.abs(ease) <= TOL) return 1 - (Math.abs(ease) / TOL) * 0.2;
  if (ease < -TOL) return Math.max(0, 1 - ((-ease - TOL) / 8) * 1.5);
  return Math.max(0, 1 - (ease - TOL) / 12);
}

// ---------------------------------------------------------------------------
// Main recommendation function
//
// availableSizes (optional): the candidate size labels to choose among. Defaults to the chart's
// keys. The PDP widget passes the sizes that actually have a 3D model, which lets it recommend
// from a body anchor even when no chart exists.
// ---------------------------------------------------------------------------

export function recommendSize(
  measurements,
  sizeChart,
  preferredFit,
  category,
  fitType,
  convention,
  gender,
  availableSizes,
) {
  preferredFit = preferredFit || 'regular';
  category = category || 'tops';
  fitType = fitType || 'regular';
  convention = convention || 'circumference';
  gender = gender || 'unisex';
  sizeChart = sizeChart || {};

  const candidates = (availableSizes && availableSizes.length) ? availableSizes : Object.keys(sizeChart);
  // Which size system this garment uses (letters / Women EU / Men EU), inferred from its labels.
  const system = inferSizeSystem(candidates, gender);
  const sizes = candidates.slice().sort((a, b) => sizeToOrdinal(a, system) - sizeToOrdinal(b, system));

  if (sizes.length === 0) {
    return { recommendedSize: 'M', confidence: 0, allSizes: [], reasoning: 'No size chart available.' };
  }

  const measMap = measurements || {};
  const weights = CATEGORY_WEIGHTS[category] || DEFAULT_WEIGHTS;
  const easeProfile = (EASE_PROFILES[category] && EASE_PROFILES[category][fitType]) || EASE_PROFILES.tops.regular;
  const prefShift = PREFERRED_FIT_SHIFT[preferredFit];

  const allSizes = sizes.map((size) => {
    const chart = sizeChart[size];
    if (!chart) {
      return { size, totalScore: 0, weightedEase: 0, fit: 'recommended', breakdown: [] };
    }
    let totalWeight = 0;
    let weightedScoreSum = 0;
    let girthEaseSum = 0;
    let girthWeight = 0;
    const breakdown = [];

    for (const key of Object.keys(chart)) {
      let garmentVal = chart[key];
      const userVal = measMap[key];
      if (garmentVal == null || userVal == null) continue;

      const w = weights[key] != null ? weights[key] : (DEFAULT_WEIGHTS[key] != null ? DEFAULT_WEIGHTS[key] : 0.3);
      if (w === 0) continue;

      const isStructural = STRUCTURAL_FIELDS.has(key);
      if (convention === 'flat' && GIRTH_FIELDS.has(key)) garmentVal = garmentVal * 2;

      const ease = garmentVal - userVal;
      const score = isStructural ? scoreStructuralMatch(ease) : scoreMeasurementEase(ease, easeProfile, prefShift);

      breakdown.push({ key, user: userVal, garment: garmentVal, ease, weight: w, score });
      weightedScoreSum += score * w;
      totalWeight += w;
      if (!isStructural) { girthEaseSum += ease * w; girthWeight += w; }
    }

    const totalScore = totalWeight > 0 ? weightedScoreSum / totalWeight : 0;
    const weightedEase = girthWeight > 0 ? girthEaseSum / girthWeight : 0;

    const adjIdeal = easeProfile.ideal + prefShift;
    const adjMin = easeProfile.min + prefShift;
    const adjMax = easeProfile.max + prefShift;
    let fit;
    if (weightedEase < adjMin) fit = 'tight';
    else if (weightedEase > adjMax) fit = 'loose';
    else fit = 'recommended';

    return { size, totalScore, weightedEase, fit, breakdown };
  });

  // TRUE-TO-FIT selection: anchor on the shopper's REAL body -> native size, map to the
  // garment's matching label, then shift by whole sizes for the fit preference.
  const native = nativeSizeOrdinal(measurements, category, gender);
  const availOrdinals = sizes.map((s) => sizeToOrdinal(s, system)).sort((a, b) => a - b);
  const clampOrdinal = (ord) => {
    const lo = availOrdinals[0];
    const hi = availOrdinals[availOrdinals.length - 1];
    const c = Math.max(lo, Math.min(hi, ord));
    return availOrdinals.reduce((best, o) => (Math.abs(o - c) < Math.abs(best - c) ? o : best), availOrdinals[0]);
  };

  let recommendedSize;
  let recommendedOrdinal;
  if (native) {
    const shifted = native.ordinal + PREFERRED_FIT_SIZE_SHIFT[preferredFit];
    recommendedOrdinal = clampOrdinal(shifted);
    recommendedSize = sizes.find((s) => sizeToOrdinal(s, system) === recommendedOrdinal) || sizes[0];
  } else {
    const best = allSizes.slice().sort((a, b) => b.totalScore - a.totalScore)[0];
    recommendedSize = (best && best.size) || sizes[0];
    recommendedOrdinal = sizeToOrdinal(recommendedSize, system);
  }

  // Relabel the per-size chips RELATIVE to the recommendation (tight -> recommended -> loose).
  for (const s of allSizes) {
    const ord = sizeToOrdinal(s.size, system);
    s.fit = ord < recommendedOrdinal ? 'tight' : ord > recommendedOrdinal ? 'loose' : 'recommended';
  }

  const recommended = allSizes.find((s) => s.size === recommendedSize);

  // Confidence scoring (0–100).
  let confidence = 0;
  if (native && recommended) {
    const scale = BODY_SIZE_SCALE[gender] || BODY_SIZE_SCALE.unisex;
    const band = scale[native.anchorKey];
    const upper = band[SIZE_ORDER[native.girthOrdinal]] != null ? band[SIZE_ORDER[native.girthOrdinal]] : native.anchorValue;
    const prevSize = SIZE_ORDER[native.girthOrdinal - 1];
    const lower = (prevSize && band[prevSize] != null) ? band[prevSize] : upper - 8;
    const mid = (upper + lower) / 2;
    const halfWidth = Math.max(1, (upper - lower) / 2);
    const centeredness = Math.max(0, 1 - Math.abs(native.anchorValue - mid) / halfWidth);
    const bandConfidence = 35 + centeredness * 20 - (native.heightBump > 0 ? 5 : 0);

    const supporting = ['chest', 'waist', 'hips'].filter((k) => measMap[k] != null).length;
    const dataCompleteness = Math.min(30, supporting * 10);
    const genderConfidence = gender === 'unisex' ? 7 : 15;

    confidence = Math.round(Math.min(100, bandConfidence + dataCompleteness + genderConfidence));
  } else if (recommended) {
    confidence = 25;
  }

  const nativeLabel = native ? ordinalToLabel(native.ordinal, system) : undefined;
  const reasoning = buildReasoning(recommended, category, fitType, preferredFit, confidence, nativeLabel);

  return { recommendedSize, confidence, allSizes, reasoning };
}

// ---------------------------------------------------------------------------
// Human-readable reasoning
// ---------------------------------------------------------------------------

export function buildReasoning(recommended, category, fitType, preferredFit, confidence, nativeLabel) {
  if (!recommended) return 'Not enough measurement data to make a recommendation.';

  const noun = category === 'tops' ? 'top'
    : category === 'bottoms' ? 'bottom'
    : category === 'outerwear' ? 'jacket'
    : category === 'dresses' ? 'dress'
    : 'item';
  const size = recommended.size.toUpperCase();
  const native = nativeLabel ? nativeLabel.toUpperCase() : undefined;
  const parts = [];

  if (fitType === 'oversized') parts.push('This is an oversized ' + noun + '.');
  else if (fitType === 'slim') parts.push('This is a slim-fit ' + noun + '.');

  if (native) {
    if (preferredFit === 'regular') {
      const feel = fitType === 'oversized' ? 'the intended relaxed fit' : 'a true-to-fit feel';
      parts.push('Based on your measurements you are a size ' + native + ', so we recommend ' + size + ' for ' + feel + '.');
    } else {
      parts.push('Based on your measurements you are a size ' + native + '. We recommend ' + size + ' because you chose a ' + preferredFit + ' fit.');
    }
  } else {
    parts.push('Size ' + size + ' is the closest match.');
  }

  const tightSpots = recommended.breakdown.filter(
    (b) => !STRUCTURAL_FIELDS.has(b.key) && b.ease < 0 && b.weight >= 0.5,
  );
  if (tightSpots.length > 0) {
    const names = tightSpots.map((b) => b.key.replace(/_/g, ' ')).join(', ');
    parts.push('It may feel snug around the ' + names + '.');
  }

  if (confidence < 50) parts.push('More measurements would improve accuracy.');

  return parts.join(' ');
}

// Simplified wrapper (backwards compatible) — returns just the size string.
export function recommendSizeSimple(measurements, sizeChart, preferredFit, category, fitType, convention, gender, availableSizes) {
  return recommendSize(
    measurements, sizeChart, preferredFit || 'regular', category || 'tops', fitType || 'regular',
    convention || 'circumference', gender || 'unisex', availableSizes,
  ).recommendedSize;
}
