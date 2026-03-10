'use client';

import Link from 'next/link';
import { useTheme } from '@/contexts/ThemeContext';

type TryonLogoProps = {
  className?: string;
  href?: string;
};

/**
 * Theme-aware TRYON logo (transparent background).
 * Light theme → tryon_logo (black letters); dark theme → tryon_logo_w (white letters).
 */
export function TryonLogo({ className = 'h-10 w-auto', href = '/' }: TryonLogoProps) {
  const { theme } = useTheme();
  const src = theme === 'dark' ? '/tryon_logo_w.png' : '/tryon_logo.png';

  const img = (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="TRYON" className={className} />
  );

  if (href) {
    return (
      <Link href={href} className="inline-block hover:opacity-90 transition-opacity">
        {img}
      </Link>
    );
  }
  return <span className="inline-block">{img}</span>;
}
