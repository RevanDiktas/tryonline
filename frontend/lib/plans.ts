/**
 * TryOn plans: the single source for every page that shows prices (/pricing, the home page
 * summary, /product, /start). Set 2026-10-06 from competitor research (Kiwi, Goodsize,
 * Easysize, Faslet, True Fit, LiSA, Reality Try, 3DLOOK); Brand is the top tier from the
 * original pricing. Shopify bills in USD, so prices are USD.
 *
 * No free plan: every plan starts with a free trial. Nothing is metered: Find my size, try-ons
 * and avatars are unlimited on every plan (Revan, 2026-10-06: a brand must never be capped
 * because shoppers try on a lot; La Fam went from 300 to 600 try-ons in a weekend). Plans
 * differ in what is included: Size Pro has no 3D; the 3D plans differ in garments we make.
 */
export type Plan = {
  id: 'size_pro' | 'try_on' | 'scale' | 'brand';
  name: string;
  price: string;          // as shown, e.g. "$29"
  period: string;         // e.g. "per month"
  setup?: string;         // one-time fee, when there is one
  pitch: string;          // one line under the name
  features: string[];
  limits: string;         // the honest small print
  highlight?: boolean;    // the plan we steer to
  cta: { label: string; href: string };
};

export const TRIAL_DAYS = 30;

export const PLANS: Plan[] = [
  {
    id: 'size_pro',
    name: 'Size Pro',
    price: '$29',
    period: 'per month',
    pitch: 'The Find my size button on every product. No 3D.',
    features: [
      'Find my size on every product with sizes, unlimited',
      'A % match for every size, and the next best when one sells out',
      'Fit passport: shoppers measured from one photo',
      'Full analytics: size funnel, fit, returns by size',
    ],
    limits: `${TRIAL_DAYS}-day free trial.`,
    cta: { label: 'Start free trial', href: '/start?plan=size_pro' },
  },
  {
    id: 'try_on',
    name: 'Try-On',
    price: '$109',
    period: 'per month',
    pitch: 'Shoppers see your clothes on their own 3D body.',
    features: [
      'Everything in Size Pro',
      'Photoreal 3D try-on with real cloth simulation',
      'Up to 40 garments in 3D, made by our team',
      'Unlimited try-ons',
    ],
    limits: `${TRIAL_DAYS}-day free trial.`,
    highlight: true,
    cta: { label: 'Start free trial', href: '/start?plan=try_on' },
  },
  {
    id: 'scale',
    name: 'Scale',
    price: '$279',
    period: 'per month',
    pitch: 'For brands with a big part of their range in 3D.',
    features: [
      'Everything in Try-On',
      'Up to 200 garments in 3D',
      'Unlimited try-ons',
      'Priority 3D queue and an onboarding call',
    ],
    limits: `${TRIAL_DAYS}-day free trial.`,
    cta: { label: 'Start free trial', href: '/start?plan=scale' },
  },
  {
    id: 'brand',
    name: 'Brand',
    price: '$2,490',
    period: 'per month',
    setup: '+ $1,500 one-time setup',
    pitch: 'Enterprise: your whole catalogue in 3D.',
    features: [
      'Everything in Scale',
      '400+ garments in 3D',
      'Unlimited try-ons',
      'Cohort analytics, return-reason export and A/B testing',
      'Slack support with a 24-hour response',
    ],
    limits: 'Set up with our team.',
    cta: { label: 'Book a call', href: '/book' },
  },
];

/** The cheapest plan, for "from $29/month" lines. */
export const ENTRY_PLAN = PLANS[0];
