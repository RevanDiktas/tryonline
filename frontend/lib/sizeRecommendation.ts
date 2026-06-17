/**
 * Size recommendation — TYPED FACADE.
 *
 * The actual engine lives ONCE in `frontend/public/sizing-engine.js` (plain JS) so it can be
 * shared by both this Next app and the static PDP widget (test-viewer.html) without the two
 * drifting. This file only adds TypeScript types and re-exports; it contains no sizing logic.
 */

import * as engine from '../public/sizing-engine.js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PreferredFit = 'slim' | 'regular' | 'loose'
export type GarmentCategory = 'tops' | 'bottoms' | 'outerwear' | 'dresses' | 'accessories'
export type GarmentFitType = 'slim' | 'regular' | 'oversized'
export type MeasurementConvention = 'flat' | 'circumference'
export type Gender = 'male' | 'female' | 'unisex'
export type SizeSystem = 'alpha' | 'women_eu' | 'men_eu'

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
  confidence: number // 0–100
  allSizes: SizeScore[]
  reasoning: string
}

// ---------------------------------------------------------------------------
// Re-exports (typed)
// ---------------------------------------------------------------------------

export const SIZE_SYSTEMS: Record<SizeSystem, { label: string; sizes: string[] }> = engine.SIZE_SYSTEMS

export function inferSizeSystem(labels: string[], gender: Gender = 'unisex'): SizeSystem {
  return engine.inferSizeSystem(labels, gender) as SizeSystem
}

export function recommendSize(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular',
  category: GarmentCategory = 'tops',
  fitType: GarmentFitType = 'regular',
  convention: MeasurementConvention = 'circumference',
  gender: Gender = 'unisex',
  availableSizes?: string[],
  // ISO 3166-1 alpha-2 country (e.g. 'NL', 'US') — selects the regional body-size bands.
  country?: string,
): SizeRecommendation {
  return engine.recommendSize(
    measurements, sizeChart, preferredFit, category, fitType, convention, gender, availableSizes, country,
  ) as SizeRecommendation
}

export function recommendSizeSimple(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular',
  category?: GarmentCategory,
  fitType?: GarmentFitType,
  convention: MeasurementConvention = 'circumference',
  gender: Gender = 'unisex',
): string {
  return engine.recommendSize(
    measurements, sizeChart, preferredFit, category ?? 'tops', fitType ?? 'regular', convention, gender,
  ).recommendedSize as string
}
