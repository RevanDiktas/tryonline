/**
 * TryOn plans: the single source for every page that shows prices (/pricing, the home page
 * summary, /product). Set 2026-10-06 from competitor research (Kiwi, Goodsize, Easysize,
 * Faslet, True Fit, LiSA, Reality Try, 3DLOOK). Shopify bills in USD, so prices are USD.
 *
 * Flat monthly prices; usage is charged only where we pay real GPU cost (3D avatar builds).
 * Find my size costs next to nothing to run, so it is never metered per session or order:
 * a brand should never hide the button to save money.
 */
export type Plan = {
  id: 'free' | 'size_pro' | 'try_on' | 'scale' | 'enterprise';
  name: string;
  price: string;          // as shown, e.g. "$29"
  period: string;         // e.g. "per month"
  pitch: string;          // one line under the name
  features: string[];
  limits: string;         // the honest small print
  highlight?: boolean;    // the plan we steer to
  cta: { label: string; href: string };
};

export const TRIAL_DAYS = 30;

export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    pitch: 'Find my size on every product. Live today.',
    features: [
      'Find my size on every product with sizes',
      'A % match for every size, and the next best when one sells out',
      'No account needed for shoppers',
      'Size finder funnel in your dashboard',
    ],
    limits: '500 size recommendations a month. Small "Powered by TryOn" badge.',
    cta: { label: 'Start free', href: '/start?plan=free' },
  },
  {
    id: 'size_pro',
    name: 'Size Pro',
    price: '$29',
    period: 'per month',
    pitch: 'Unlimited sizing, measured from one photo.',
    features: [
      'Everything in Free, unlimited',
      'Fit passport: shoppers measured from one photo',
      'Full analytics: funnel, fit, returns by size',
      'No TryOn badge',
    ],
    limits: `${TRIAL_DAYS}-day free trial.`,
    highlight: true,
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
      'Photoreal 3D avatar try-on with real cloth simulation',
      'Up to 40 garments in 3D, made by our team',
      '250 avatars a month included',
    ],
    limits: `Then $0.39 per extra avatar. ${TRIAL_DAYS}-day free trial.`,
    cta: { label: 'Start free trial', href: '/start?plan=try_on' },
  },
  {
    id: 'scale',
    name: 'Scale',
    price: '$279',
    period: 'per month',
    pitch: 'For brands with a full catalogue in 3D.',
    features: [
      'Everything in Try-On',
      'Up to 200 garments in 3D',
      '1,000 avatars a month included',
      'Priority 3D queue and an onboarding call',
    ],
    limits: `Then $0.29 per extra avatar. ${TRIAL_DAYS}-day free trial.`,
    cta: { label: 'Start free trial', href: '/start?plan=scale' },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    pitch: 'Multiple stores, markets or a custom setup.',
    features: ['Everything in Scale', 'Unlimited garments and avatars', 'Multi-store and multi-market', 'Dedicated support'],
    limits: 'Talk to us.',
    cta: { label: 'Book a call', href: '/book' },
  },
];
