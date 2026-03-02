'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
  Cell,
} from 'recharts';

const CHART_COLORS = {
  tryon: '#0ea5e9',
  purchase: '#22c55e',
  atc: '#f59e0b',
  recommended: '#6366f1',
  selected: '#8b5cf6',
  purchased: '#ec4899',
};

const CHART_COLORS_DARK = {
  tryon: '#38bdf8',
  purchase: '#4ade80',
  atc: '#fbbf24',
  recommended: '#818cf8',
  selected: '#a78bfa',
  purchased: '#f472b6',
};

const tooltipStyle = (dark?: boolean) => ({
  contentStyle: {
    backgroundColor: dark ? 'rgba(15,15,20,0.95)' : 'rgba(10,10,15,0.92)',
    border: dark ? '1px solid rgba(255,255,255,0.08)' : '1px solid rgba(0,0,0,0.1)',
    borderRadius: 8,
    padding: '8px 12px',
    fontSize: 11,
    color: dark ? 'rgba(255,255,255,0.85)' : '#fff',
    boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
    backdropFilter: 'blur(12px)',
  },
  labelStyle: { color: dark ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.6)', fontSize: 10, marginBottom: 2 },
  itemStyle: { color: dark ? 'rgba(255,255,255,0.85)' : '#fff', fontSize: 11, padding: 0 },
  cursor: { fill: dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
});

const gridStroke = (dark?: boolean) => dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
const tickStyle = (dark?: boolean) => ({ fontSize: 10, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)' });
const legendStyle = (dark?: boolean) => ({ fontSize: 10, color: dark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)' });

export function ConversionFunnelChart({
  tryons,
  atc,
  purchases,
  dark,
}: {
  tryons: number;
  atc: number;
  purchases: number;
  dark?: boolean;
}) {
  const colors = dark ? CHART_COLORS_DARK : CHART_COLORS;
  const data = [
    { name: 'Try-on', value: tryons, fill: colors.tryon },
    { name: 'Add to cart', value: atc, fill: colors.atc },
    { name: 'Purchase', value: purchases, fill: colors.purchase },
  ];
  const maxVal = Math.max(tryons, atc, purchases, 1) || 1;
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[140px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, maxVal]} hide />
          <YAxis type="category" dataKey="name" width={90} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            formatter={(value: number | undefined) => [value ?? 0, '']}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VelocityChart({ velocity, dark }: { velocity: { tryon_velocity_7d: number; tryon_velocity_30d: number; purchase_velocity_7d: number; purchase_velocity_30d: number } | null; dark?: boolean }) {
  if (!velocity) return null;
  const colors = dark ? CHART_COLORS_DARK : CHART_COLORS;
  const data = [
    { period: '7d', TryOn: velocity.tryon_velocity_7d, Purchase: velocity.purchase_velocity_7d },
    { period: '30d', TryOn: velocity.tryon_velocity_30d, Purchase: velocity.purchase_velocity_30d },
  ];
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[160px] w-full min-h-[140px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="period" tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tt.contentStyle} labelStyle={tt.labelStyle} itemStyle={tt.itemStyle} cursor={tt.cursor} formatter={(value: number | undefined) => [value ?? 0, '']} />
          <Legend wrapperStyle={legendStyle(dark)} />
          <Bar dataKey="TryOn" fill={colors.tryon} radius={[6, 6, 0, 0]} name="Try-on" />
          <Bar dataKey="Purchase" fill={colors.purchase} radius={[6, 6, 0, 0]} name="Purchase" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SizeDistributionChart({
  recommended,
  selected,
  purchased,
  dark,
}: {
  recommended: Record<string, number>;
  selected: Record<string, number>;
  purchased: Record<string, number>;
  dark?: boolean;
}) {
  const colors = dark ? CHART_COLORS_DARK : CHART_COLORS;
  const defaultSizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
  const allSizes = Array.from(new Set([...defaultSizes, ...Object.keys(recommended), ...Object.keys(selected), ...Object.keys(purchased)]));
  const sizes = allSizes.sort((a, b) => defaultSizes.indexOf(a) - defaultSizes.indexOf(b) || a.localeCompare(b));
  const data = sizes
    .filter((s) => recommended[s] || selected[s] || purchased[s])
    .map((size) => ({
      size,
      Recommended: recommended[size] ?? 0,
      Selected: selected[size] ?? 0,
      Purchased: purchased[size] ?? 0,
    }));

  if (data.length === 0) return null;
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[180px] w-full min-h-[140px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="size" tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tt.contentStyle} labelStyle={tt.labelStyle} itemStyle={tt.itemStyle} cursor={tt.cursor} />
          <Legend wrapperStyle={legendStyle(dark)} />
          <Bar dataKey="Recommended" fill={colors.recommended} radius={[4, 4, 0, 0]} name="Recommended" />
          <Bar dataKey="Selected" fill={colors.selected} radius={[4, 4, 0, 0]} name="Selected" />
          <Bar dataKey="Purchased" fill={colors.purchased} radius={[4, 4, 0, 0]} name="Purchased" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ExplorationTrendChart({ data, dark }: { data: { week_start: string; avg_sizes_per_session: number }[]; dark?: boolean }) {
  if (!data.length) return null;

  const chartData = data.map((d) => ({
    week: d.week_start.slice(0, 10),
    avgSizes: d.avg_sizes_per_session,
  }));

  const strokeColor = dark ? '#38bdf8' : '#6366f1';
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[160px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="explorationGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity={0.2} />
              <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="week" tick={tickStyle(dark)} tickFormatter={(v) => v?.slice(5) ?? v} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} allowDecimals axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={{ stroke: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }}
            formatter={(value: number | undefined) => [(value ?? 0).toFixed(1), 'Avg sizes/session']}
            labelFormatter={(label) => `Week ${label}`}
          />
          <Area
            type="monotone"
            dataKey="avgSizes"
            stroke={strokeColor}
            strokeWidth={2}
            fill="url(#explorationGradient)"
            name="Avg sizes per session"
            dot={{ r: 3, fill: strokeColor, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: strokeColor, strokeWidth: 2, stroke: dark ? '#000' : '#fff' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RegionalSizeChart({ by_country, dark }: { by_country: Record<string, Record<string, number>>; dark?: boolean }) {
  const countries = Object.keys(by_country);
  if (countries.length === 0) return null;

  const sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
  const data = countries.map((country) => {
    const row: Record<string, string | number> = { country };
    sizes.forEach((s) => {
      row[s] = Math.round((by_country[country][s] ?? 0) * 100);
    });
    return row;
  });

  const palette = dark
    ? ['#38bdf8', '#818cf8', '#a78bfa', '#c084fc', '#e879f9', '#f472b6']
    : ['#6366f1', '#8b5cf6', '#a78bfa', '#c084fc', '#e879f9', '#f472b6'];
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[180px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={tickStyle(dark)} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="country" width={80} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            formatter={(value: number | undefined, name?: string) => [`${value ?? 0}%`, name ?? '']}
          />
          <Legend wrapperStyle={legendStyle(dark)} />
          {sizes.map((s, i) => (
            <Bar key={s} dataKey={s} stackId="a" fill={palette[i]} radius={[0, 0, 0, 0]} name={s} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
