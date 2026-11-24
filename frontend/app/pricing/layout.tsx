import { pageMetadata } from '@/lib/seo';
import { PLANS, TRIAL_DAYS } from '@/lib/plans';

const tryOn = PLANS.find((p) => p.id === 'try_on')!;

export const metadata = pageMetadata(
  '/pricing',
  'Pricing',
  `Size recommendation on every product of your Shopify store for free, photoreal virtual try-on from ${tryOn.price} a month with a ${TRIAL_DAYS}-day free trial.`,
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
