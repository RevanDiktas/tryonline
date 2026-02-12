/**
 * Size recommendation algorithm
 * Inputs: user measurements, product size chart, preferred fit
 * Output: recommended size
 */

export type PreferredFit = 'slim' | 'regular' | 'loose'

export interface UserMeasurements {
  chest: number
  waist: number
  hips: number
  height?: number
}

export interface SizeChart {
  [size: string]: { chest: number; waist: number; hips: number }
}

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

function sizeToOrdinal(size: string): number {
  const i = SIZE_ORDER.indexOf(size.toUpperCase())
  return i >= 0 ? i : 2 // default M
}

function ordinalToSize(ord: number): string {
  const i = Math.max(0, Math.min(ord, SIZE_ORDER.length - 1))
  return SIZE_ORDER[i]
}

/**
 * Recommends a size based on measurements, size chart, and preferred fit.
 * - Body match: size where garment ease (garment - body) is in ideal range
 * - slim: bias one size down (tighter)
 * - regular: neutral
 * - loose: bias one size up (roomier)
 */
export function recommendSize(
  measurements: UserMeasurements,
  sizeChart: SizeChart,
  preferredFit: PreferredFit = 'regular'
): string {
  const sizes = Object.keys(sizeChart).sort((a, b) => sizeToOrdinal(a) - sizeToOrdinal(b))
  if (sizes.length === 0) return 'M'

  // For each size, compute avg ease (garment - body) across chest, waist, hips
  const withEase = sizes.map((size) => {
    const chart = sizeChart[size]
    const chestEase = chart.chest - measurements.chest
    const waistEase = chart.waist - measurements.waist
    const hipsEase = chart.hips - measurements.hips
    const avgEase = (chestEase + waistEase + hipsEase) / 3
    return { size, avgEase }
  })

  // Ideal ease ranges by preference (cm)
  // slim: 0–5 (fitted), regular: 4–10, loose: 8–16
  const idealRanges: Record<PreferredFit, [number, number]> = {
    slim: [0, 5],
    regular: [4, 10],
    loose: [8, 16],
  }
  const [minEase, maxEase] = idealRanges[preferredFit]

  // Find size with ease closest to ideal midpoint
  const idealMid = (minEase + maxEase) / 2
  const sorted = [...withEase].sort((a, b) => Math.abs(a.avgEase - idealMid) - Math.abs(b.avgEase - idealMid))
  let match = sorted[0]
  let baseOrdinal = sizeToOrdinal(match.size)

  // Apply bias: slim = -1, loose = +1
  if (preferredFit === 'slim') baseOrdinal = Math.max(0, baseOrdinal - 1)
  else if (preferredFit === 'loose') baseOrdinal = Math.min(sizes.length - 1, baseOrdinal + 1)

  return sizes[Math.min(baseOrdinal, sizes.length - 1)]
}
