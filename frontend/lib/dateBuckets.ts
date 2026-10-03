/** Shared date-bucket labels for analytics charts and tables (kept out of the lazily loaded chart bundle). */
const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Axis/tooltip label for a bucket start date (YYYY-MM-DD) at the given granularity. */
export function formatBucket(isoDate: string, granularity: 'day' | 'week' | 'month' = 'week', long = false): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  const mon = MONTHS_SHORT[(m || 1) - 1];
  if (granularity === 'month') return long ? `${mon} ${y}` : `${mon} ${String(y).slice(2)}`;
  if (granularity === 'week') return long ? `Week of ${d} ${mon} ${y}` : `${d} ${mon}`;
  return long ? `${d} ${mon} ${y}` : `${d} ${mon}`;
}
