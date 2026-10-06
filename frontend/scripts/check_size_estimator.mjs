/**
 * Offline check for the size finder's estimator (public/size-estimator.js).
 *
 *     cd frontend && node scripts/check_size_estimator.mjs
 *
 * Checks behaviour, not accuracy: accuracy is measured against ANSUR II by
 * scripts/fit_size_estimator.py (the dataset is not in the repo).
 */
import {
  estimateBody, quickSize, validateInput, inferCategory, toMetric, normalizeGender,
  MODEL, SHAPE_QUESTIONS, SHAPE_WEIGHT, BETWEEN_SIZES_AT,
} from '../public/size-estimator.js';
import { recommendSize } from '../public/sizing-engine.js';

let failures = 0;
function check(name, cond, detail) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (!cond && detail !== undefined ? '  (' + JSON.stringify(detail) + ')' : ''));
  if (!cond) failures++;
}
const ALPHA = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
const man = { gender: 'male', height: 180, weight: 80, age: 30 };
const woman = { gender: 'female', height: 167, weight: 62, age: 30 };

// --- estimate
const m = estimateBody(man);
const w = estimateBody(woman);
check('a 180 cm / 80 kg / 30-year-old man: chest 100-104, waist 87-91, hips 97-101',
  m.measurements.chest > 100 && m.measurements.chest < 104 && m.measurements.waist > 87 && m.measurements.waist < 91
  && m.measurements.hips > 97 && m.measurements.hips < 101, m.measurements);
check('a 167 cm / 62 kg / 30-year-old woman: bust 89-93, hips 97-101', w.measurements.chest > 89 && w.measurements.chest < 93
  && w.measurements.hips > 97 && w.measurements.hips < 101, w.measurements);
check('no waist is estimated for women (navel waist is not the size-chart waist)', !('waist' in w.measurements) && !('waist' in w.sd));
check('typed height is passed through for the engine', m.measurements.height === 180);
check('heavier at the same height -> every girth larger',
  ['chest', 'waist', 'hips'].every((k) => estimateBody({ ...man, weight: 95 }).measurements[k] > m.measurements[k]));
check('taller at the same weight -> every girth smaller',
  ['chest', 'waist', 'hips'].every((k) => estimateBody({ ...man, height: 195 }).measurements[k] < m.measurements[k]));
check('age is optional, and leaving it out widens the error',
  estimateBody({ ...man, age: null }).sd.waist > m.sd.waist && estimateBody({ ...man, age: '' }).usedAge === false);

// --- build questions
const broad = estimateBody({ ...man, shape: { chest: 1, belly: 0 } });
const slim = estimateBody({ ...man, shape: { chest: -1, belly: 0 } });
const avg = estimateBody({ ...man, shape: { chest: 0, belly: 0 } });
check('"broader chest" raises the chest by SHAPE_WEIGHT x the upper-third shift',
  Math.abs((broad.measurements.chest - avg.measurements.chest) - SHAPE_WEIGHT * MODEL.male.chest.shift[1]) < 0.11, broad.measurements);
check('"slimmer" lowers it, "average" leaves it', slim.measurements.chest < avg.measurements.chest && avg.measurements.chest === m.measurements.chest);
check('answering a question narrows the error for that measurement, but not to zero',
  avg.sd.chest < m.sd.chest && avg.sd.chest > MODEL.male.chest.within, { answered: avg.sd.chest, unanswered: m.sd.chest });
check('an answered question is not overridden by another answer\'s side effect',
  estimateBody({ ...man, shape: { chest: 0, belly: 1 } }).measurements.chest === avg.measurements.chest);
check('a rounder belly raises the waist', estimateBody({ ...man, shape: { belly: 1 } }).measurements.waist > m.measurements.waist + 2.5);
check('men are asked about chest and belly, women about bust and hips',
  SHAPE_QUESTIONS.male.map((q) => q.id).join() === 'chest,belly' && SHAPE_QUESTIONS.female.map((q) => q.id).join() === 'chest,hips');

// --- input handling
check('missing or absurd input -> a message, and no estimate',
  validateInput({ height: '', weight: 70 }) && validateInput({ height: 180, weight: 5 }) && validateInput({ height: 180, weight: 80, age: 3 })
  && estimateBody({ height: 900, weight: 80 }) === null && quickSize({ height: 'x', weight: 80 }, { sizes: ALPHA }) === null);
check('"1,80"-style decimal commas are read as numbers', estimateBody({ gender: 'male', height: '180,5', weight: '80,2' }).measurements.height === 180.5);
check('outside the sampled range -> flagged, with a wider error',
  estimateBody({ ...man, weight: 150 }).extrapolated === true && estimateBody({ ...man, weight: 150 }).sd.chest > m.sd.chest * 1.4 && m.extrapolated === false);
check('age beyond the sample is held at its edge, not extrapolated',
  estimateBody({ ...man, age: 80 }).measurements.waist === estimateBody({ ...man, age: 55 }).measurements.waist && estimateBody({ ...man, age: 80 }).extrapolated);
const uni = estimateBody({ gender: 'other', height: 172, weight: 68 });
const um = estimateBody({ gender: 'male', height: 172, weight: 68 });
const uf = estimateBody({ gender: 'female', height: 172, weight: 68 });
check('no gender given -> between the two models, wider error, no waist',
  uni.gender === 'unisex' && Math.abs(uni.measurements.chest - (um.measurements.chest + uf.measurements.chest) / 2) < 0.11
  && uni.sd.chest > Math.max(um.sd.chest, uf.sd.chest) && !('waist' in uni.measurements), uni);
check('gender spellings', normalizeGender('Women') === 'female' && normalizeGender('M') === 'male' && normalizeGender(undefined) === 'unisex');
check('feet/inches and pounds convert', JSON.stringify(toMetric('imperial', 5, 11, 176)) === JSON.stringify({ height: 180.3, weight: 79.8 }));

// --- size for a product
const r = quickSize(man, { sizes: ALPHA, category: 'tops' }, { country: 'NL' });
check('returns a size the product actually has', ALPHA.includes(r.recommendedSize), r.recommendedSize);
check('same pick as the engine given the estimated body (one set of sizing rules for both tiers)',
  r.recommendedSize === recommendSize(m.measurements, {}, 'regular', 'tops', 'regular', 'circumference', 'male', ALPHA, 'NL').recommendedSize);
const total = r.probabilities.reduce((a, b) => a + b.p, 0);
check('likelihoods cover every outcome (sum ~ 1) and are sorted', Math.abs(total - 1) < 0.03 && r.probabilities.every((x, i, a) => i === 0 || a[i - 1].p >= x.p), r.probabilities);
check('confidence is the likelihood of the recommended size', r.confidence === Math.round(r.probabilities.find((x) => x.size === r.recommendedSize).p * 100));
// 178 cm / 89 kg / 30: estimated chest ~108 cm, exactly where L ends and XL begins in Europe.
const edge = quickSize({ gender: 'male', height: 178, weight: 89, age: 30 }, { sizes: ALPHA, category: 'tops' }, { country: 'NL' });
check('someone on a size boundary is told both sizes', edge.alternative !== null && /between/i.test(edge.reasoning) && edge.confidence < 75, edge);
// 178 cm / 82 kg / 30: estimated chest ~104 cm, the middle of L (100-108).
const sure = quickSize({ gender: 'male', height: 178, weight: 82, age: 30, shape: { chest: 0, belly: 0 } }, { sizes: ALPHA, category: 'tops' }, { country: 'NL' });
check('someone mid-band gets one size and a higher likelihood', sure.confidence > edge.confidence, { sure: sure.confidence, edge: edge.confidence });
check(`a second size is only named at ${BETWEEN_SIZES_AT * 100}%+`,
  [r, edge, sure].every((x) => x.alternative === null || x.probabilities.find((q) => q.size === x.alternative).p >= BETWEEN_SIZES_AT));
check('a looser fit preference never picks a smaller size',
  ALPHA.indexOf(quickSize(man, { sizes: ALPHA }, { preferredFit: 'loose' }).recommendedSize) >= ALPHA.indexOf(quickSize(man, { sizes: ALPHA }, { preferredFit: 'slim' }).recommendedSize));
check('bottoms for men anchor on the waist, for women on the hips',
  quickSize(man, { sizes: ALPHA, category: 'bottoms' }).anchor === 'waist' && quickSize(woman, { sizes: ALPHA, category: 'bottoms' }).anchor === 'hips');
check('a product sold in S-L only: a large body is clamped to L, never an absent size',
  quickSize({ gender: 'male', height: 185, weight: 120 }, { sizes: ['S', 'M', 'L'] }).recommendedSize === 'L');
const eu = quickSize(woman, { sizes: ['34', '36', '38', '40', '42'], category: 'tops' }, { country: 'NL' });
check('numeric (EU) size labels work and keep the store\'s own labels', ['34', '36', '38', '40', '42'].includes(eu.recommendedSize), eu.recommendedSize);
check('no sizes -> no recommendation', quickSize(man, { sizes: [] }) === null && quickSize(man, {}) === null);
check('extrapolated input says so in the wording', /rough guide/.test(quickSize({ ...man, weight: 160 }, { sizes: ALPHA }).reasoning));

// --- product words
check('category from the product\'s own words (EN/NL/DE/FR)',
  inferCategory('', 'Denim slogan jeans') === 'bottoms' && inferCategory('Broek', 'Wide leg') === 'bottoms'
  && inferCategory('', 'Polka dots zipper jacket') === 'outerwear' && inferCategory('Jurk', '') === 'dresses'
  && inferCategory('', 'Colored striped logo cap') === 'accessories' && inferCategory('', 'Diamond t-shirt blue') === 'tops'
  && inferCategory('', 'Striped LA FAM longsleeve') === 'tops' && inferCategory(null, undefined) === 'tops');
check('"short" inside another word is not shorts', inferCategory('', 'Shortsleeve shirt') === 'tops');

// --- per-size fit scores (0-100)
{
  const quiz = [];
  const measured = [];
  for (const g of ['male', 'female']) for (let h = 155; h <= 200; h += 5) for (let kg = 50; kg <= 115; kg += 5) {
    const q = quickSize({ gender: g, height: h, weight: kg, age: 30 }, { sizes: ALPHA, category: 'tops' }, { country: 'NL' });
    if (q) quiz.push(q);
    const est = estimateBody({ gender: g, height: h, weight: kg, age: 30 });
    measured.push(recommendSize(est.measurements, {}, 'regular', 'tops', 'regular', 'circumference', g, ALPHA, 'NL'));
  }
  const all = quiz.concat(measured);
  check('every size gets a score from 0 to 100', all.every((r) => ALPHA.every((s) => r.scores[s] >= 0 && r.scores[s] <= 100)));
  const topIsPick = (r) => ALPHA.every((s) => r.scores[s] <= r.scores[r.recommendedSize]);
  check('the recommended size always has the top score', all.every(topIsPick), all.filter((r) => !topIsPick(r)).map((r) => [r.recommendedSize, r.scores])[0]);
  const falls = (r) => {
    const i = ALPHA.indexOf(r.recommendedSize);
    return ALPHA.every((s, j) => (j < i ? r.scores[s] <= r.scores[ALPHA[j + 1]] : j > i ? r.scores[s] <= r.scores[ALPHA[j - 1]] : true));
  };
  check('scores fall away from the recommended size on both sides', all.every(falls), all.filter((r) => !falls(r)).map((r) => [r.recommendedSize, r.scores])[0]);
  const spread = (r) => ALPHA.reduce((t, s) => t + (s === r.recommendedSize ? 0 : r.scores[s]), 0);
  const avg = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
  check('a quiz estimate is less certain than a measurement (more score on the other sizes)', avg(quiz.map(spread)) > avg(measured.map(spread)),
    [avg(quiz.map(spread)), avg(measured.map(spread))]);
  const mid = recommendSize({ chest: 110, waist: 96, hips: 108, height: 180 }, {}, 'regular', 'tops', 'regular', 'circumference', 'male', ALPHA, null);
  check('a body mid-band is near-certain of its own size and unlikely in the next', mid.scores.L >= 90 && mid.scores.M < 40 && mid.scores.XL < 40, mid.scores);
  const exact = recommendSize({ chest: 110, waist: 96, hips: 108, height: 180 }, {}, 'regular', 'tops', 'regular', 'circumference', 'male', ALPHA, null, {});
  check('exact measurements (no uncertainty) still score every size', ALPHA.every((s) => exact.scores[s] != null) && exact.recommendedSize === mid.recommendedSize);
  const charted = recommendSize({ chest: 104, waist: 90, hips: 100, height: 180 }, { m: { chest: 53 }, l: { chest: 56 } }, 'regular', 'tops', 'regular', 'flat', 'male', ['M', 'L'], 'NL');
  check('store labels (M) find lowercase chart keys (m)', charted.allSizes.every((x) => x.breakdown.length === 1), charted.allSizes);
  check('a chart never changes the scores (the body decides; the chart only describes)',
    JSON.stringify(charted.scores) === JSON.stringify(recommendSize({ chest: 104, waist: 90, hips: 100, height: 180 }, {}, 'regular', 'tops', 'regular', 'flat', 'male', ['M', 'L'], 'NL').scores));
}

console.log('\n' + (failures ? failures + ' CHECK(S) FAILED' : 'ALL CHECKS PASSED'));
process.exit(failures ? 1 : 0);
