import { Inter, Inter_Tight, IBM_Plex_Mono } from 'next/font/google';

/* The three families of the site: Inter Tight for headings, Inter for text, IBM Plex Mono for labels.
   Two weights only. Exposed as CSS variables on the page wrapper. */
const display = Inter_Tight({ subsets: ['latin'], weight: ['400', '500'], variable: '--f-display', display: 'swap' });
const body = Inter({ subsets: ['latin'], weight: ['400', '500'], variable: '--f-body', display: 'swap' });
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500'], variable: '--f-mono', display: 'swap' });

export const fontVars = `${display.variable} ${body.variable} ${mono.variable}`;
