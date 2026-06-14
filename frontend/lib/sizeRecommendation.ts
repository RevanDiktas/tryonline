/**
 * Size recommendation engine v2
 *
 * Inputs:  user body measurements, garment size chart, garment category,
 *          garment fit type, preferred fit
 * Outputs: recommended size + confidence score + per-size breakdown
 *
 * Key improvements over v1:
 *  - Category-aware measurement weighting (chest matters more for tops, etc.)
 *  - Garment-type ease profiles (jackets need more room than tees)
 *  - Fit preference modifies the ease TARGET, not a blind ±1 size shift
 *  - Asymmetric penalty: too-tight penalised more heavily than too-loose
 *  - Confidence score (0–100) based on data quality and match closeness
 *  - Works with any subset of measurements (graceful degradation)
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PreferredFit = 'slim' | 'regular' | 'loose'
export type GarmentCategory = 'tops' | 'bottoms' | 'outerwear' | 'dresses' | 'accessories'
export type GarmentFitType = 'slim' | 'regular' | 'oversized'

/**
 * How the garment size chart values are recorded.
 *  - 'circumference': measured all the way around (matches body tape measurements directly).
 *  - 'flat':          garment laid flat and measured across (the standard tech-pack / CLO3D
 *                     convention). A flat girth value is HALF the circumference, so girth
 *                     fields must be doubled before comparing against a body measurement.
 * Body measurements are always circumference, so 'flat' charts need conversion.
 */
export type MeasurementConvention = 'flat' | 'circumference'

// Girth fields are measured around the body, so a flat-chart value is half the real value.
// Linear/structural fields (shoulder, sleeve, inseam, torso) are point-to-point and are
// NEVER doubled.
const GIRTH_FIELDS = new Set(['chest', 'waist', 'hips', 'thigh', 'neck'])

// Structural fields are length/width matches, not ease. A correctly-fitting shoulder seam
// sits at ~0 ease; scoring it against a girth ease target (e.g. +8cm) would wrongly read a
// good fit as "too tight". These get a near-zero match target instead.
const STRUCTURAL_FIELDS = new Set([
  'shoulder_width', 'shoulder', 'arm_length', 'sleeve', 'inseam', 'torso_length',
])

export interface UserMeasurements {
  chest?: number
  waist?: number
  hips?: number
  height?: number
  inseam?: number
  shoulder_width?: number
  arm_length?: number
  neck?: number
  thigh?: number
  torso_length?: number
}

export interface SizeChart {
  [size: string]: Record<string, number>
}

export interface MeasurementBreakdown {
  key: string
  user: number
  garment: number
  ease: number
  weight: number
  score: number
}

export interface SizeScore {
  size: string
  totalScore: number
  weightedEase: number
  fit: 'tight' | 'recommended' | 'loose'
  breakdown: MeasurementBreakdown[]
}

export interface SizeRecommendation {
  recommendedSize: string
  confidence: number          // 0–100
  allSizes: SizeScore[]
  reasoning: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SIZE_ORDER = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL']

function sizeToOrdinal(size: string): number {
  const i = SIZE_ORDER.indexOf(size.toUpperCase())
  return i >= 0 ? i : 3 // default M
}

// ---------------------------------------------------------------------------
// Measurement weights per garment category
// Higher weight = more important for that garment type
// ---------------------------------------------------------------------------

type WeightMap = Record<string, number>

const CATEGORY_WEIGHTS: Record<GarmentCategory, WeightMap> = {
  tops: {
    chest: 1.0,
    shoulder_width: 0.8, shoulder: 0.8,
    waist: 0.5,
    hips: 0.2,
    arm_length: 0.3, sleeve: 0.3,
    neck: 0.3,
    torso_length: 0.2,
  },
  bottoms: {
    waist: 1.0,
    hips: 0.9,
    inseam: 0.7,
    thigh: 0.6,
    chest: 0.0,
    shoulder_width: 0.0, shoulder: 0.0,
  },
  outerwear: {
    chest: 1.0,
    shoulder_width: 0.9, shoulder: 0.9,
    waist: 0.4,
    hips: 0.3,
    arm_length: 0.5, sleeve: 0.5,
    neck: 0.2,
  },
  dresses: {
    chest: 0.8,
    waist: 0.9,
    hips: 1.0,
    shoulder_width: 0.5, shoulder: 0.5,
    torso_length: 0.3,
    arm_length: 0.2, sleeve: 0.2,
  },
  accessories: {
    chest: 0.5,
    waist: 0.5,
    hips: 0.5,
  },
}

const DEFAULT_WEIGHTS: WeightMap = {
  chest: 0.8,
  waist: 0.7,
  hips: 0.7,
  inseam: 0.4,
  shoulder_width: 0.5, shoulder: 0.5,
  arm_length: 0.3, sleeve: 0.3,
  thigh: 0.3,
  neck: 0.2,
  torso_length: 0.2,
}

// ---------------------------------------------------------------------------
// Ideal ease profiles (cm) per garment category × garment fit type
// Each profile defines the TARGET ease — garment dimension minus body dimension.
// [min, ideal, max] — the ideal midpoint is the sweet spot.
// ---------------------------------------------------------------------------

type EaseProfile = { min: number; ideal: number; max: number }

const EASE_PROFILES: Record<GarmentCategory, Record<GarmentFitType, EaseProfile>> = {
  tops: {
    slim:      { min: 2,  ideal: 5,  max: 8  },
    regular:   { min: 5,  ideal: 8,  max: 12 },
    oversized: { min: 10, ideal: 15, max: 22 },
  },
  bottoms: {
    slim:      { min: 0,  ideal: 2,  max: 5  },
    regular:   { min: 2,  ideal: 5,  max: 8  },
    oversized: { min: 6,  ideal: 10, max: 16 },
  },
  outerwear: {
    slim:      { min: 6,  ideal: 10, max: 14 },
    regular:   { min: 10, ideal: 14, max: 20 },
    oversized: { min: 16, ideal: 22, max: 30 },
  },
  dresses: {
    slim:      { min: 1,  ideal: 4,  max: 7  },
    regular:   { min: 4,  ideal: 7,  max: 11 },
    oversized: { min: 8,  ideal: 13, max: 20 },
  },
  accessories: {
    slim:      { min: 0,  ideal: 3,  max: 6  },
    regular:   { min: 3,  ideal: 6,  max: 10 },
    oversized: { min: 6,  ideal: 10, max: 16 },
  },
}

// User's preferred fit shifts the ease target (used only for the descriptive ease feel)
const PREFERRED_FIT_SHIFT: Record<PreferredFit, number> = {
  slim:    -3,  // tighter than garment's default
  regular:  0,
  loose:   +3,  // roomier than garment's default
}

// ---------------------------------------------------------------------------
// True-to-fit core: standard body -> native size scale
//
// The garment's own measurements cannot tell us a shopper's native size — an
// intentionally oversized M jacket has a 130cm chest. So we anchor on the shopper's REAL
// body measurements (from avatar anthropometry) against a standard adult apparel scale,
// pick their native size (the size they'd normally wear), then recommend the garment's
// matching label. The garment's designed fit (oversized/slim) is communicated in the
// message, never used to shrink/grow the recommended size.
// ---------------------------------------------------------------------------

export type Gender = 'male' | 'female' | 'unisex'

// Upper bound (cm, body circumference) of each size band. A body value <= the bound for
// size S but > the bound for XS falls into S. Values above XXL's bound clamp to XXL.
// These are industry-typical adult bands; tune per brand if needed.
type SizeBand = Partial<Record<string, number>>

const BODY_SIZE_SCALE: Record<Gender, { chest: SizeBand; waist: SizeBand; hips: SizeBand }> = {
  male: {
    chest: { XS: 90, S: 98,  M: 106, L: 114, XL: 122, XXL: 130 },
    waist: { XS: 74, S: 82,  M: 90,  L: 98,  XL: 106, XXL: 114 },
    hips:  { XS: 90, S: 98,  M: 104, L: 110, XL: 117, XXL: 124 },
  },
  female: {
    chest: { XS: 80, S: 86,  M: 92,  L: 100, XL: 108, XXL: 116 },
    waist: { XS: 64, S: 70,  M: 78,  L: 86,  XL: 94,  XXL: 102 },
    hips:  { XS: 88, S: 94,  M: 100, L: 108, XL: 116, XXL: 124 },
  },
  // Blend of male/female — used when gender is unknown (lower confidence).
  unisex: {
    chest: { XS: 85, S: 92,  M: 99,  L: 107, XL: 115, XXL: 123 },
    waist: { XS: 69, S: 76,  M: 84,  L: 92,  XL: 100, XXL: 108 },
    hips:  { XS: 89, S: 96,  M: 102, L: 109, XL: 116, XXL: 124 },
  },
}

const NATIVE_SCALE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// Typical height (cm) of the wearer at the CENTRE of each size. Used to size UP a tall
// build: a person who is much taller than their girth-size's typical wearer needs the
// next size for length (sleeves, torso, rise). This is the classic tall-and-lean problem
// where chest alone under-sizes. We never size DOWN for a short build (girth already
// covers that, and short wearers rarely need a smaller size just for length).
const EXPECTED_HEIGHT_BY_SIZE: Record<Gender, Partial<Record<string, number>>> = {
  male:   { XS: 168, S: 173, M: 178, L: 183, XL: 188, XXL: 193 },
  female: { XS: 158, S: 163, M: 168, L: 173, XL: 178, XXL: 183 },
  unisex: { XS: 163, S: 168, M: 173, L: 178, XL: 183, XXL: 188 },
}

// Which body measurement anchors native size for each garment category.
const CATEGORY_ANCHOR: Record<GarmentCategory, 'chest' | 'waist' | 'hips'> = {
  tops: 'chest',
  outerwear: 'chest',
  dresses: 'chest',
  bottoms: 'waist',
  accessories: 'chest',
}

/**
 * Map a shopper's real body measurements to their native size ORDINAL (index into
 * SIZE_ORDER). Returns null if the anchoring measurement is missing.
 */
function nativeSizeOrdinal(
  measurements: UserMeasurements,
  category: GarmentCategory,
  gender: Gender,
): { ordinal: number; girthOrdinal: number; anchorKey: string; anchorValue: number; heightBump: number } | null {
  const scale = BODY_SIZE_SCALE[gender] ?? BODY_SIZE_SCALE.unisex
  const anchorKey = CATEGORY_ANCHOR[category] ?? 'chest'
  const measMap = measurements as Record<string, number | undefined>
  let value = measMap[anchorKey]
  let usedKey = anchorKey

  // Fallback chain: bottoms can fall back to hips, tops to waist.
  if (value == null) {
    const fallback = anchorKey === 'waist' ? 'hips' : 'waist'
    value = measMap[fallback]
    usedKey = fallback
  }
  if (value == null) return null

  // 1. Girth-based size from the anchor measurement.
  const band = scale[usedKey as 'chest' | 'waist' | 'hips']
  let girthOrdinal = SIZE_ORDER.indexOf('XXL') // default if larger than every band
  for (const sz of NATIVE_SCALE_ORDER) {
    const bound = band[sz]
    if (bound != null && value <= bound) {
      girthOrdinal = SIZE_ORDER.indexOf(sz)
      break
    }
  }

  // 2. Frame / length nudge: size up when the shopper is notably taller than the typical
  // wearer of their girth size (tall-and-lean builds need the next size for length).
  let heightBump = 0
  const height = measMap['height']
  const expected = EXPECTED_HEIGHT_BY_SIZE[gender][SIZE_ORDER[girthOrdinal]]
  if (height != null && expected != null) {
    const over = height - expected
    // One size up for a clearly tall build; two only for an extreme outlier (e.g. ~198cm
    // on an M chest), which is rare. Most tall-and-lean shoppers want exactly +1.
    if (over > 20) heightBump = 2
    else if (over > 6) heightBump = 1
  }

  return {
    ordinal: girthOrdinal + heightBump,
    girthOrdinal,
    anchorKey: usedKey,
    anchorValue: value,
    heightBump,
  }
}

// Preference shifts the NATIVE size by whole sizes (true-to-fit philosophy).
const PREFERRED_FIT_SIZE_SHIFT: Record<PreferredFit, number> = {
  slim:    -1,
  regular:  0,
  loose:   +1,
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/**
 * Score a single measurement's ease against the target ease profile.
 *
 * Returns 0–1 where 1 = perfect match, 0 = terrible.
 * Asymmetric: tightness (negative ease) is penalised 1.5x more than excess room,
 * because a garment that's too tight is unwearable, while too loose is just unflattering.
 */
function scoreMeasurementEase(
  ease: number,
  profile: EaseProfile,
  preferredShift: number,
): number {
  const targetMin = profile.min + preferredShift
  const targetIdeal = profile.ideal + preferredShift
  const targetMax = profile.max + preferredShift

  if (ease >= targetMin && ease <= targetMax) {
    // Within acceptable range — score based on distance from ideal
    const maxDist = Math.max(targetIdeal - targetMin, targetMax - targetIdeal)
    const dist = Math.abs(ease - targetIdeal)
    return maxDist > 0 ? 1 - (dist / maxDist) * 0.3 : 1 // 0.7–1.0 range
  }

  // Outside acceptable range
  if (ease < targetMin) {
    // Too tight — heavier penalty
    const deficit = targetMin - ease
    const TIGHT_PENALTY = 1.5
    return Math.max(0, 1 - (deficit / 10) * TIGHT_PENALTY)
  }

  // Too loose — lighter penalty
  const excess = ease - targetMax
  return Math.max(0, 1 - (excess / 15))
}

/**
 * Score a structural/linear measurement (shoulder width, sleeve length, inseam, torso).
 *
 * Unlike girth, these want the garment dimension to MATCH the body dimension — the seam
 * should land on the shoulder point, the sleeve should reach the wrist. A small positive
 * ease (slightly long sleeve) is fine; tightness (garment shorter than body) is penalised
 * harder, same asymmetry as girth.
 *
 * Returns 0–1 where 1 = perfect match.
 */
function scoreStructuralMatch(ease: number): number {
  const TOL = 3 // cm tolerance band around a perfect match
  if (Math.abs(ease) <= TOL) {
    return 1 - (Math.abs(ease) / TOL) * 0.2 // 0.8–1.0
  }
  if (ease < -TOL) {
    // Garment too short/narrow — heavier penalty (unwearable)
    return Math.max(0, 1 - ((-ease - TOL) / 8) * 1.5)
  }
  // Garment a bit long/wide — lighter penalty
  return Math.max(0, 1 - (ease - TOL) / 12)
}

// ---------------------------------------------------------------------------
// Main recommendation function
// ---------------------------------------------------------------------------

export function recommendSize(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular',
  category: GarmentCategory = 'tops',
  fitType: GarmentFitType = 'regular',
  // Defaults to 'circumference' so existing callers (and the seeded demo chart, which is
  // authored as circumference) are unchanged. Real merchant uploads are 'flat' and must
  // pass it explicitly.
  convention: MeasurementConvention = 'circumference',
  // Gender selects the standard body->size scale used to anchor native size.
  gender: Gender = 'unisex',
): SizeRecommendation {
  const sizes = Object.keys(sizeChart).sort((a, b) => sizeToOrdinal(a) - sizeToOrdinal(b))

  // Fallback: no sizes or no measurements
  if (sizes.length === 0) {
    return {
      recommendedSize: 'M',
      confidence: 0,
      allSizes: [],
      reasoning: 'No size chart available.',
    }
  }

  const measMap = measurements as Record<string, number | undefined>
  const weights = CATEGORY_WEIGHTS[category] ?? DEFAULT_WEIGHTS
  const easeProfile = EASE_PROFILES[category]?.[fitType] ?? EASE_PROFILES.tops.regular
  const prefShift = PREFERRED_FIT_SHIFT[preferredFit]

  const allSizes: SizeScore[] = sizes.map((size) => {
    const chart = sizeChart[size]
    if (!chart) {
      return { size, totalScore: 0, weightedEase: 0, fit: 'recommended' as const, breakdown: [] }
    }

    let totalWeight = 0
    let weightedScoreSum = 0
    // Fit classification (tight/recommended/loose) reflects GIRTH ease only — structural
    // fields sit near 0 ease by design and would otherwise drag the average toward "tight".
    let girthEaseSum = 0
    let girthWeight = 0
    const breakdown: MeasurementBreakdown[] = []

    for (const key of Object.keys(chart)) {
      let garmentVal = chart[key]
      const userVal = measMap[key]
      if (garmentVal == null || userVal == null) continue

      const w = weights[key] ?? DEFAULT_WEIGHTS[key] ?? 0.3
      if (w === 0) continue

      const isStructural = STRUCTURAL_FIELDS.has(key)

      // Flat charts record girth as half the circumference — double before comparing.
      if (convention === 'flat' && GIRTH_FIELDS.has(key)) {
        garmentVal = garmentVal * 2
      }

      const ease = garmentVal - userVal
      const score = isStructural
        ? scoreStructuralMatch(ease)
        : scoreMeasurementEase(ease, easeProfile, prefShift)

      breakdown.push({ key, user: userVal, garment: garmentVal, ease, weight: w, score })
      weightedScoreSum += score * w
      totalWeight += w
      if (!isStructural) {
        girthEaseSum += ease * w
        girthWeight += w
      }
    }

    const totalScore = totalWeight > 0 ? weightedScoreSum / totalWeight : 0
    const weightedEase = girthWeight > 0 ? girthEaseSum / girthWeight : 0

    // Classify fit based on weighted ease
    const adjIdeal = easeProfile.ideal + prefShift
    const adjMin = easeProfile.min + prefShift
    const adjMax = easeProfile.max + prefShift
    let fit: 'tight' | 'recommended' | 'loose'
    if (weightedEase < adjMin) fit = 'tight'
    else if (weightedEase > adjMax) fit = 'loose'
    else fit = 'recommended'

    return { size, totalScore, weightedEase, fit, breakdown }
  })

  // ---------------------------------------------------------------------------
  // TRUE-TO-FIT selection.
  // Anchor on the shopper's REAL body -> native size, map to the garment's matching label,
  // then shift by whole sizes for the fit preference. The garment's own ease never moves
  // the size — an oversized M is still recommended as M for a native-M body.
  // ---------------------------------------------------------------------------
  const native = nativeSizeOrdinal(measurements, category, gender)

  // The garment's available sizes as ordinals, sorted ascending.
  const availOrdinals = sizes.map((s) => sizeToOrdinal(s)).sort((a, b) => a - b)
  const clampOrdinal = (ord: number): number => {
    const lo = availOrdinals[0]
    const hi = availOrdinals[availOrdinals.length - 1]
    const c = Math.max(lo, Math.min(hi, ord))
    // Snap to the nearest size the garment actually offers.
    return availOrdinals.reduce((best, o) => (Math.abs(o - c) < Math.abs(best - c) ? o : best), availOrdinals[0])
  }

  let recommendedSize: string
  let recommendedOrdinal: number
  if (native) {
    const shifted = native.ordinal + PREFERRED_FIT_SIZE_SHIFT[preferredFit]
    recommendedOrdinal = clampOrdinal(shifted)
    recommendedSize = sizes.find((s) => sizeToOrdinal(s) === recommendedOrdinal) ?? 'M'
  } else {
    // No body anchor available — fall back to the descriptive best-ease size.
    const best = [...allSizes].sort((a, b) => b.totalScore - a.totalScore)[0]
    recommendedSize = best?.size ?? 'M'
    recommendedOrdinal = sizeToOrdinal(recommendedSize)
  }

  // Relabel the per-size chips RELATIVE to the recommendation so the UI shows a clean
  // tight -> recommended -> loose gradient consistent with the pick.
  for (const s of allSizes) {
    const ord = sizeToOrdinal(s.size)
    s.fit = ord < recommendedOrdinal ? 'tight' : ord > recommendedOrdinal ? 'loose' : 'recommended'
  }

  const recommended = allSizes.find((s) => s.size === recommendedSize)

  // ---------------------------------------------------------------------------
  // Confidence scoring (0–100)
  // ---------------------------------------------------------------------------
  let confidence = 0
  if (native && recommended) {
    // Factor 1: how cleanly the body lands in its size band (35–55 pts). A value at the
    // centre of its band scores full; a value near a band edge (borderline two sizes)
    // scores less, because the native call itself is less certain.
    const scale = BODY_SIZE_SCALE[gender] ?? BODY_SIZE_SCALE.unisex
    const band = scale[native.anchorKey as 'chest' | 'waist' | 'hips']
    const upper = band[SIZE_ORDER[native.girthOrdinal]] ?? native.anchorValue
    const prevSize = SIZE_ORDER[native.girthOrdinal - 1]
    const lower = (prevSize && band[prevSize] != null) ? (band[prevSize] as number) : upper - 8
    const mid = (upper + lower) / 2
    const halfWidth = Math.max(1, (upper - lower) / 2)
    const centeredness = Math.max(0, 1 - Math.abs(native.anchorValue - mid) / halfWidth) // 0..1
    // A height-bumped recommendation is inherently a bit less certain than a pure girth match.
    const bandConfidence = 35 + centeredness * 20 - (native.heightBump > 0 ? 5 : 0)

    // Factor 2: data completeness — the anchor measurement plus supporting girth (0–30).
    const measMap2 = measurements as Record<string, number | undefined>
    const supporting = ['chest', 'waist', 'hips'].filter((k) => measMap2[k] != null).length
    const dataCompleteness = Math.min(30, supporting * 10)

    // Factor 3: gender known (0–15). Unisex scale is a blend, so slightly less certain.
    const genderConfidence = gender === 'unisex' ? 7 : 15

    confidence = Math.round(Math.min(100, bandConfidence + dataCompleteness + genderConfidence))
  } else if (recommended) {
    confidence = 25 // fell back to ease-only with no body anchor
  }

  const nativeLabel = native ? SIZE_ORDER[native.ordinal] : undefined
  const reasoning = buildReasoning(
    recommended, category, fitType, preferredFit, confidence, nativeLabel,
  )

  return {
    recommendedSize,
    confidence,
    allSizes,
    reasoning,
  }
}

// ---------------------------------------------------------------------------
// Human-readable reasoning
// ---------------------------------------------------------------------------

function buildReasoning(
  recommended: SizeScore | undefined,
  category: GarmentCategory,
  fitType: GarmentFitType,
  preferredFit: PreferredFit,
  confidence: number,
  nativeLabel: string | undefined,
): string {
  if (!recommended) {
    return 'Not enough measurement data to make a recommendation.'
  }

  const noun = category === 'tops' ? 'top'
    : category === 'bottoms' ? 'bottom'
    : category === 'outerwear' ? 'jacket'
    : category === 'dresses' ? 'dress'
    : 'item'
  const size = recommended.size.toUpperCase()
  const native = nativeLabel?.toUpperCase()
  const parts: string[] = []

  // 1. Name the garment's DESIGNED fit so the shopper knows the silhouette intent.
  if (fitType === 'oversized') parts.push(`This is an oversized ${noun}.`)
  else if (fitType === 'slim') parts.push(`This is a slim-fit ${noun}.`)

  // 2. The recommendation, framed by the shopper's chosen preference.
  if (native) {
    if (preferredFit === 'regular') {
      const feel = fitType === 'oversized' ? 'the intended relaxed fit' : 'a true-to-fit feel'
      parts.push(`Based on your measurements you are a size ${native}, so we recommend ${size} for ${feel}.`)
    } else {
      parts.push(`Based on your measurements you are a size ${native}. We recommend ${size} because you chose a ${preferredFit} fit.`)
    }
  } else {
    parts.push(`Size ${size} is the closest match.`)
  }

  // 3. Flag genuine tight spots at the recommended size (girth only).
  const tightSpots = recommended.breakdown.filter(
    (b) => !STRUCTURAL_FIELDS.has(b.key) && b.ease < 0 && b.weight >= 0.5,
  )
  if (tightSpots.length > 0) {
    const names = tightSpots.map((b) => b.key.replace(/_/g, ' ')).join(', ')
    parts.push(`It may feel snug around the ${names}.`)
  }

  if (confidence < 50) {
    parts.push('More measurements would improve accuracy.')
  }

  return parts.join(' ')
}

// ---------------------------------------------------------------------------
// Simplified wrapper (backwards compatible with v1 callers)
// Returns just the size string.
// ---------------------------------------------------------------------------

export function recommendSizeSimple(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular',
  category?: GarmentCategory,
  fitType?: GarmentFitType,
  convention: MeasurementConvention = 'circumference',
  gender: Gender = 'unisex',
): string {
  return recommendSize(
    measurements,
    sizeChart,
    preferredFit,
    category ?? 'tops',
    fitType ?? 'regular',
    convention,
    gender,
  ).recommendedSize
}
