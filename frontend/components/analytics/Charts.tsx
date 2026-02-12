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
  tryon: '#f8fafc',
  purchase: '#94a3b8',
  atc: '#64748b',
  recommended: '#e2e8f0',
  selected: '#94a3b8',
  purchased: '#64748b',
};

const tooltipDark = {
  backgroundColor: 'rgba(10,10,10,0.95)',
  borderRadius: 10,
  padding: '10px 14px',
  fontSize: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
};
const tooltipLight = {
  backgroundColor: 'rgba(255,255,255,0.96)',
  borderRadius: 10,
  padding: '10px 14px',
  fontSize: 12,
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
};
const gridDark = 'rgba(255,255,255,0.06)';

// Conversion funnel bar chart (Try-on → ATC → Purchase)
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

  return (
    <div className="h-[140px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, maxVal]} hide />
          <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} />
          <Tooltip
            contentStyle={dark ? tooltipDark : tooltipLight}
            formatter={(value: number | undefined) => [value ?? 0, '']}
            labelStyle={{ color: dark ? 'rgba(255,255,255,0.8)' : undefined }}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={32}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Velocity comparison (7d vs 30d)
export function VelocityChart({ velocity, dark }: { velocity: { tryon_velocity_7d: number; tryon_velocity_30d: number; purchase_velocity_7d: number; purchase_velocity_30d: number } | null; dark?: boolean }) {
  if (!velocity) return null;
  const colors = dark ? CHART_COLORS_DARK : CHART_COLORS;
  const data = [
    { period: '7d', TryOn: velocity.tryon_velocity_7d, Purchase: velocity.purchase_velocity_7d },
    { period: '30d', TryOn: velocity.tryon_velocity_30d, Purchase: velocity.purchase_velocity_30d },
  ];

  return (
    <div className="h-[160px] w-full min-h-[140px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? gridDark : '#e2e8f0'} vertical={false} />
          <XAxis dataKey="period" tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} />
          <YAxis tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} allowDecimals={false} />
          <Tooltip contentStyle={dark ? tooltipDark : tooltipLight} formatter={(value: number | undefined) => [value ?? 0, '']} />
          <Legend wrapperStyle={{ fontSize: 11 }} formatter={(value) => <span style={{ color: dark ? 'rgba(255,255,255,0.6)' : undefined }}>{value}</span>} />
          <Bar dataKey="TryOn" fill={colors.tryon} radius={[6, 6, 0, 0]} name="Try-on" />
          <Bar dataKey="Purchase" fill={colors.purchase} radius={[6, 6, 0, 0]} name="Purchase" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Size distribution grouped bar (Recommended, Selected, Purchased)
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

  return (
    <div className="h-[180px] w-full min-h-[140px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? gridDark : '#e2e8f0'} vertical={false} />
          <XAxis dataKey="size" tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} />
          <YAxis tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} allowDecimals={false} />
          <Tooltip contentStyle={dark ? tooltipDark : tooltipLight} />
          <Legend wrapperStyle={{ fontSize: 11 }} formatter={(value) => <span style={{ color: dark ? 'rgba(255,255,255,0.6)' : undefined }}>{value}</span>} />
          <Bar dataKey="Recommended" fill={colors.recommended} radius={[6, 6, 0, 0]} name="Recommended" />
          <Bar dataKey="Selected" fill={colors.selected} radius={[6, 6, 0, 0]} name="Selected" />
          <Bar dataKey="Purchased" fill={colors.purchased} radius={[6, 6, 0, 0]} name="Purchased" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Exploration trend over time (line chart)
export function ExplorationTrendChart({ data, dark }: { data: { week_start: string; avg_sizes_per_session: number }[]; dark?: boolean }) {
  if (!data.length) return null;

  const chartData = data.map((d) => ({
    week: d.week_start.slice(0, 10),
    avgSizes: d.avg_sizes_per_session,
  }));

  const strokeColor = dark ? '#e2e8f0' : '#6366f1';

  return (
    <div className="h-[160px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="explorationGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity={dark ? 0.25 : 0.3} />
              <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? gridDark : '#e2e8f0'} vertical={false} />
          <XAxis dataKey="week" tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} tickFormatter={(v) => v?.slice(5) ?? v} />
          <YAxis tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} allowDecimals />
          <Tooltip
            contentStyle={dark ? tooltipDark : tooltipLight}
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
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Regional size distribution (stacked bar by country)
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

  const palette = dark ? ['#94a3b8', '#64748b', '#475569', '#334155', '#1e293b', '#0f172a'] : ['#94a3b8', '#64748b', '#475569', '#334155', '#1e293b', '#0f172a'];

  return (
    <div className="h-[180px] w-full min-h-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke={dark ? gridDark : '#e2e8f0'} horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="country" width={80} tick={{ fontSize: 11, fontWeight: 500, fill: dark ? 'rgba(255,255,255,0.55)' : '#475569' }} />
          <Tooltip
            contentStyle={dark ? tooltipDark : tooltipLight}
            formatter={(value: number | undefined) => [`${value ?? 0}%`, '']}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} formatter={(value) => <span style={{ color: dark ? 'rgba(255,255,255,0.6)' : undefined }}>{value}</span>} />
          {sizes.map((s, i) => (
            <Bar key={s} dataKey={s} stackId="a" fill={palette[i]} radius={[0, 0, 0, 0]} name={s} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
