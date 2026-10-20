/**
 * The size for one product, for the MCP tools. The SAME calls as the Find my size card
 * (public/size-finder.html, compute() and renderResult()), on the same engine files, so a
 * shopper gets the same size in a chat as on the store:
 *
 *   quiz answers   -> quickSize(answers, { sizes, category, fitType }, { preferredFit, country })
 *   fit passport   -> recommendSize(measurements, chart, fit, category, fitType,
 *                                   chart ? 'flat' : 'circumference', gender, sizes, country)
 *
 * A completed fit passport always wins over quiz answers (as in the card). Sold out: the best
 * size stays the answer, and the best-scoring size in stock is offered next to it, but only
 * when it scores at least MIN_FALLBACK_MATCH. (The store card offers any in-stock size; in a
 * chat an assistant may buy what we name, so a 1% "next best" must never be named.)
 */
// @ts-ignore - plain ES modules shared with the store-page card
import { recommendSize } from '../../public/sizing-engine.js';
// @ts-ignore
import { quickSize, inferCategory, normalizeGender, validateInput } from '../../public/size-estimator.js';
import type { ProductSize } from './product';

export type Fit = 'slim' | 'regular' | 'loose';

export const MIN_FALLBACK_MATCH = 30;

export interface QuizAnswers {
  gender: 'female' | 'male';
  height: number;
  weight: number;
  age?: number;
  shape?: { chest?: -1 | 0 | 1; belly?: -1 | 0 | 1; hips?: -1 | 0 | 1 };
  fit?: Fit;
}

export type Body =
  | { basis: 'measured'; measurements: Record<string, number>; gender: string; fit?: Fit }
  | { basis: 'estimate'; answers: QuizAnswers };

export interface Garment { category: string; fitType: string; chart: Record<string, Record<string, number>> }

export interface SizeAnswer {
  size: string;
  basis: 'measured' | 'estimate';
  /** 0-100 chance each size fits, by label */
  scores: Record<string, number>;
  match: number;
  reasoning: string;
  /** Quiz only: a second size the shopper is between, or null */
  between: string | null;
  soldOut: boolean;
  /** Best-scoring size in stock when the best size is sold out, if it scores >= MIN_FALLBACK_MATCH */
  nextInStock: string | null;
}

export function garmentFromProduct(productType: string, title: string): Garment {
  return { category: String(inferCategory(productType, title)), fitType: 'regular', chart: {} };
}

export function usableAnswers(a: unknown): a is QuizAnswers {
  return !!a && typeof a === 'object' && ['female', 'male'].includes((a as QuizAnswers).gender) && !validateInput(a);
}

export function sizeFor(body: Body, sizes: ProductSize[], garment: Garment, fit: Fit | undefined, country: string | null): SizeAnswer | null {
  const labels = sizes.map((s) => s.label);
  if (!labels.length) return null;
  let r: any;
  let between: string | null = null;
  if (body.basis === 'estimate') {
    const a = body.answers;
    r = quickSize({ gender: a.gender, height: a.height, weight: a.weight, age: a.age, shape: a.shape || {} },
      { sizes: labels, category: garment.category, fitType: garment.fitType },
      { preferredFit: fit || a.fit || 'regular', country: country || undefined });
    between = r?.alternative || null;
  } else {
    const hasChart = Object.keys(garment.chart).length > 0;
    r = recommendSize(body.measurements, garment.chart, fit || body.fit || 'regular', garment.category, garment.fitType,
      hasChart ? 'flat' : 'circumference', normalizeGender(body.gender), labels, country || undefined);
  }
  if (!r || !r.recommendedSize) return null;
  const scores: Record<string, number> = r.scores || {};
  const size: string = r.recommendedSize;
  const soldOut = sizes.some((s) => s.label === size && !s.available);
  let nextInStock: string | null = null;
  if (soldOut) {
    const inStock = sizes.filter((s) => s.available).map((s) => s.label).sort((x, y) => (scores[y] || 0) - (scores[x] || 0));
    // Only offer a size that might actually fit: an assistant will act on it.
    nextInStock = inStock.find((l) => (scores[l] || 0) >= MIN_FALLBACK_MATCH) || null;
  }
  return {
    size, basis: body.basis, scores, match: Math.round(scores[size] || 0), reasoning: String(r.reasoning || ''),
    between, soldOut, nextInStock,
  };
}
