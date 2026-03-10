'use client';

import Link from 'next/link';
import { useTheme } from '@/contexts/ThemeContext';

type TryonLogoProps = {
  className?: string;
  href?: string;
};

/**
 * Theme-aware TRYON logo.
 * Light theme → tryon-logo.jpg; dark theme → tryon-logo-d.jpg (inverted for dark UI).
 */
export function TryonLogo({ className = 'h-10 w-auto', href = '/' }: TryonLogoProps) {
  const { theme } = useTheme();
  const src = theme === 'dark' ? '/tryon-logo-d.jpg' : '/tryon-logo.jpg';

  const img = (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="TRYON" className={className} />
  );

  if (href) {
    return (
      <Link href={href} className="inline-block opacity-90 hover:opacity-100 transition-opacity">
        {img}
      </Link>
    );
  }
  return <span className="inline-block">{img}</span>;
}
