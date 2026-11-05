/**
 * Parse a size chart out of whatever a brand has: Excel, CSV, JSON, or text copied out of a PDF.
 * Output: { "<size>": { "<measurement>": cm } } with canonical measurement keys.
 * Handles both orientations (sizes down the first column, or sizes across the header row).
 */
import { SIZE_SYSTEMS } from '@/lib/sizeRecommendation';

export const MEASUREMENTS = ['neck', 'shoulder', 'chest', 'bicep', 'sleeve', 'cuff', 'length', 'waist', 'hips', 'rise', 'thigh', 'inseam', 'hem'];
export const ALL_SIZE_LABELS = new Set(Object.values(SIZE_SYSTEMS).flatMap((s) => s.sizes));

const MEASUREMENT_ALIASES: Record<string, string> = {
  bust: 'chest', chest: 'chest', 'pit to pit': 'chest', 'pit-to-pit': 'chest', 'half chest': 'chest', borst: 'chest',
  shoulder: 'shoulder', shoulders: 'shoulder', 'shoulder width': 'shoulder', 'across shoulder': 'shoulder', 'across back': 'shoulder', schouder: 'shoulder',
  bicep: 'bicep', biceps: 'bicep', 'upper arm': 'bicep', armhole: 'bicep',
  sleeve: 'sleeve', 'sleeve length': 'sleeve', 'arm length': 'sleeve', arm: 'sleeve', mouw: 'sleeve', mouwlengte: 'sleeve',
  cuff: 'cuff', wrist: 'cuff', 'sleeve opening': 'cuff', 'cuff width': 'cuff', 'cuff opening': 'cuff',
  neck: 'neck', neckline: 'neck', collar: 'neck', 'neck width': 'neck',
  length: 'length', 'body length': 'length', 'garment length': 'length', 'total length': 'length', 'back length': 'length', 'front length': 'length', lengte: 'length',
  waist: 'waist', taille: 'waist',
  hip: 'hips', hips: 'hips', seat: 'hips', heup: 'hips',
  rise: 'rise', 'front rise': 'rise', 'rise front': 'rise',
  thigh: 'thigh', 'thigh width': 'thigh', 'leg width': 'thigh', dij: 'thigh',
  inseam: 'inseam', 'inside leg': 'inseam', 'inner leg': 'inseam', inleg: 'inseam', binnenbeen: 'inseam',
  hem: 'hem', 'hem width': 'hem', 'bottom opening': 'hem', 'leg opening': 'hem', sweep: 'hem', 'bottom width': 'hem', opening: 'hem', zoom: 'hem',
};

export function normalizeHeader(raw: unknown): string | null {
  if (raw == null) return null;
  let h = String(raw).toLowerCase().trim();
  h = h.replace(/\([^)]*\)/g, ' ');
  h = h.replace(/\bcm\b|\binch(es)?\b|"/g, ' ');
  h = h.replace(/[_\-/]+/g, ' ').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!h) return null;
  if (MEASUREMENT_ALIASES[h]) return MEASUREMENT_ALIASES[h];
  if (MEASUREMENTS.includes(h)) return h;
  const first = h.split(' ')[0];
  if (MEASUREMENT_ALIASES[first]) return MEASUREMENT_ALIASES[first];
  if (MEASUREMENTS.includes(first)) return first;
  return null;
}

export function parseNum(raw: unknown): number {
  if (typeof raw === 'number') return raw;
  if (raw == null) return NaN;
  let s = String(raw).trim().replace(/\s/g, '');
  if (!s) return NaN;
  s = s.replace(/[^0-9.,-]/g, '');
  if (s.includes(',') && !s.includes('.')) s = s.replace(',', '.');
  else s = s.replace(/,/g, '');
  return parseFloat(s);
}

const sizeLabel = (c: unknown) => String(c ?? '').trim().toLowerCase();
const isSize = (c: unknown) => ALL_SIZE_LABELS.has(sizeLabel(c));

export function csvToRows(text: string): string[][] {
  const lines = text.replace(/\r\n?/g, '\n').trim().split('\n').filter((l) => l.trim().length);
  if (!lines.length) return [];
  const count = (ch: string) => (lines[0].split(ch).length - 1);
  const semi = count(';'), tab = count('\t'), comma = count(',');
  const delim = semi >= comma && semi >= tab ? ';' : tab > comma ? '\t' : ',';
  return lines.map((l) => l.split(delim).map((c) => c.trim().replace(/^"|"$/g, '')));
}

/** Text copied out of a PDF: cells separated by tabs or runs of 2+ spaces; falls back to single spaces. */
export function pastedTextToRows(text: string): string[][] {
  const lines = text.replace(/\r\n?/g, '\n').split('\n').map((l) => l.trim()).filter(Boolean);
  const rows = lines.map((l) => (/\t|  +/.test(l) ? l.split(/\t| {2,}/) : l.split(/ +/)).map((c) => c.trim()).filter((c) => c.length));
  return rows;
}

/** Transpose when sizes run across the header row ("XS S M L XL") instead of down the first column. */
function orient(rows: unknown[][]): unknown[][] {
  const headerIdx = rows.findIndex((r) => Array.isArray(r) && r.slice(1).filter(isSize).length >= 2);
  const colSizes = rows.filter((r) => Array.isArray(r) && isSize(r[0])).length;
  if (headerIdx >= 0 && colSizes < 2) {
    const header = rows[headerIdx] as unknown[];
    const body = rows.slice(headerIdx + 1).filter((r) => Array.isArray(r) && normalizeHeader(r[0]));
    const out: unknown[][] = [['size', ...body.map((r) => r[0])]];
    for (let c = 1; c < header.length; c++) {
      if (!isSize(header[c])) continue;
      out.push([header[c], ...body.map((r) => r[c])]);
    }
    return out;
  }
  return rows;
}

export function rowsToChart(rowsIn: unknown[][]): Record<string, Record<string, number>> {
  const rows = orient(rowsIn);
  const out: Record<string, Record<string, number>> = {};
  if (!rows || rows.length < 2) return out;
  let headerIdx = rows.findIndex((r) => Array.isArray(r) && r.slice(1).some((c) => normalizeHeader(c)));
  if (headerIdx < 0) headerIdx = 0;
  const header = rows[headerIdx] || [];
  const colMap: Record<number, string> = {};
  for (let i = 1; i < header.length; i++) {
    const key = normalizeHeader(header[i]);
    if (key) colMap[i] = key;
  }
  for (let r = headerIdx + 1; r < rows.length; r++) {
    const row = rows[r];
    if (!Array.isArray(row)) continue;
    const sz = sizeLabel(row[0]);
    if (!ALL_SIZE_LABELS.has(sz)) continue;
    const vals: Record<string, number> = {};
    for (const idx of Object.keys(colMap)) {
      const v = parseNum(row[Number(idx)]);
      if (!isNaN(v) && v > 0) vals[colMap[Number(idx)]] = v;
    }
    if (Object.keys(vals).length) out[sz] = vals;
  }
  return out;
}

export async function parseChartFile(file: File): Promise<Record<string, Record<string, number>>> {
  const name = file.name.toLowerCase();
  if (name.endsWith('.json')) {
    const obj = JSON.parse(await file.text());
    const out: Record<string, Record<string, number>> = {};
    for (const rawSz of Object.keys(obj || {})) {
      const sz = rawSz.toLowerCase().trim();
      if (!ALL_SIZE_LABELS.has(sz)) continue;
      const vals: Record<string, number> = {};
      for (const [rawKey, rawVal] of Object.entries(obj[rawSz] || {})) {
        const key = normalizeHeader(rawKey);
        const v = parseNum(rawVal);
        if (key && !isNaN(v) && v > 0) vals[key] = v;
      }
      if (Object.keys(vals).length) out[sz] = vals;
    }
    return out;
  }
  if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
    const XLSX = await import('xlsx');
    const wb = XLSX.read(await file.arrayBuffer(), { type: 'array' });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: '' }) as unknown[][];
    return rowsToChart(rows);
  }
  return rowsToChart(csvToRows(await file.text()));
}
