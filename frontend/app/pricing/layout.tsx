import { pageMetadata } from '@/lib/seo';
import { PLANS, TRIAL_DAYS } from '@/lib/plans';

const sizePro = PLANS.find((p) => p.id === 'size_pro')!;
const tryOn = PLANS.find((p) => p.id === 'try_on')!;

export const metadata = pageMetadata(
  '/pricing',
  'Pricing',
  `Free size recommendation on every product of your Shopify store. Measured sizes from ${sizePro.price} a month, photoreal virtual try-on from ${tryOn.price}. ${TRIAL_DAYS}-day free trial.`,
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
