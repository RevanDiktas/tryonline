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

// User's preferred fit shifts the ease target
const PREFERRED_FIT_SHIFT: Record<PreferredFit, number> = {
  slim:    -3,  // tighter than garment's default
  regular:  0,
  loose:   +3,  // roomier than garment's default
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

// ---------------------------------------------------------------------------
// Main recommendation function
// ---------------------------------------------------------------------------

export function recommendSize(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular',
  category: GarmentCategory = 'tops',
  fitType: GarmentFitType = 'regular',
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
    let weightedEaseSum = 0
    const breakdown: MeasurementBreakdown[] = []

    for (const key of Object.keys(chart)) {
      const garmentVal = chart[key]
      const userVal = measMap[key]
      if (garmentVal == null || userVal == null) continue

      const w = weights[key] ?? DEFAULT_WEIGHTS[key] ?? 0.3
      if (w === 0) continue

      const ease = garmentVal - userVal
      const score = scoreMeasurementEase(ease, easeProfile, prefShift)

      breakdown.push({ key, user: userVal, garment: garmentVal, ease, weight: w, score })
      weightedScoreSum += score * w
      weightedEaseSum += ease * w
      totalWeight += w
    }

    const totalScore = totalWeight > 0 ? weightedScoreSum / totalWeight : 0
    const weightedEase = totalWeight > 0 ? weightedEaseSum / totalWeight : 0

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

  // Sort by score descending — best match first
  const sorted = [...allSizes].sort((a, b) => b.totalScore - a.totalScore)
  const best = sorted[0]

  // ---------------------------------------------------------------------------
  // Confidence scoring (0–100)
  // ---------------------------------------------------------------------------
  let confidence = 0
  if (best && best.breakdown.length > 0) {
    // Factor 1: match quality (0–50 pts)
    const matchQuality = best.totalScore * 50

    // Factor 2: data completeness — how many measurement dimensions matched (0–30 pts)
    const possibleKeys = Object.keys(weights).filter((k) => weights[k] > 0)
    const matchedHighWeight = best.breakdown.filter((b) => b.weight >= 0.5).length
    const expectedHighWeight = possibleKeys.filter((k) => (weights[k] ?? 0) >= 0.5).length
    const dataCompleteness = expectedHighWeight > 0
      ? (matchedHighWeight / expectedHighWeight) * 30
      : 15

    // Factor 3: separation — how much better is #1 vs #2? (0–20 pts)
    const separation = sorted.length >= 2
      ? Math.min(1, (sorted[0].totalScore - sorted[1].totalScore) / 0.15) * 20
      : 10

    confidence = Math.round(Math.min(100, matchQuality + dataCompleteness + separation))
  }

  // Build reasoning
  const reasoning = buildReasoning(best, category, fitType, preferredFit, confidence)

  return {
    recommendedSize: best?.size ?? 'M',
    confidence,
    allSizes,
    reasoning,
  }
}

// ---------------------------------------------------------------------------
// Human-readable reasoning
// ---------------------------------------------------------------------------

function buildReasoning(
  best: SizeScore | undefined,
  category: GarmentCategory,
  fitType: GarmentFitType,
  preferredFit: PreferredFit,
  confidence: number,
): string {
  if (!best || best.breakdown.length === 0) {
    return 'Not enough measurement data to make a recommendation.'
  }

  const parts: string[] = []
  parts.push(`Size ${best.size.toUpperCase()} is the best match for this ${fitType} ${category === 'tops' ? 'top' : category === 'bottoms' ? 'bottom' : category === 'outerwear' ? 'jacket/coat' : category === 'dresses' ? 'dress' : 'item'}.`)

  // Highlight any tight spots
  const tightSpots = best.breakdown.filter((b) => b.ease < 0 && b.weight >= 0.5)
  if (tightSpots.length > 0) {
    const names = tightSpots.map((b) => b.key.replace(/_/g, ' ')).join(', ')
    parts.push(`Note: may feel snug around the ${names}.`)
  }

  // Highlight preference impact
  if (preferredFit !== 'regular') {
    parts.push(`Adjusted for your ${preferredFit} fit preference.`)
  }

  if (confidence < 50) {
    parts.push('Confidence is moderate — more measurements would improve accuracy.')
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
): string {
  return recommendSize(
    measurements,
    sizeChart,
    preferredFit,
    category ?? 'tops',
    fitType ?? 'regular',
  ).recommendedSize
}
