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
  PieChart,
  Pie,
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
  isAnimationActive: false,
  animationDuration: 0,
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
    <div className="h-[140px] w-full min-h-[120px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={120} initialDimension={{ width: 400, height: 120 }}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, maxVal]} hide />
          <YAxis type="category" dataKey="name" width={90} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined) => [value ?? 0, '']}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={28} isAnimationActive={false}>
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
    <div className="h-[160px] w-full min-h-[140px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={140} initialDimension={{ width: 400, height: 140 }}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="period" tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tt.contentStyle} labelStyle={tt.labelStyle} itemStyle={tt.itemStyle} cursor={tt.cursor} isAnimationActive={false} formatter={(value: number | undefined) => [value ?? 0, '']} />
          <Legend wrapperStyle={legendStyle(dark)} />
          <Bar dataKey="TryOn" fill={colors.tryon} radius={[6, 6, 0, 0]} name="Try-on" isAnimationActive={false} />
          <Bar dataKey="Purchase" fill={colors.purchase} radius={[6, 6, 0, 0]} name="Purchase" isAnimationActive={false} />
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
    <div className="h-[180px] w-full min-h-[140px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={140} initialDimension={{ width: 400, height: 140 }}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="size" tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tt.contentStyle} labelStyle={tt.labelStyle} itemStyle={tt.itemStyle} cursor={tt.cursor} isAnimationActive={false} />
          <Legend wrapperStyle={legendStyle(dark)} />
          <Bar dataKey="Recommended" fill={colors.recommended} radius={[4, 4, 0, 0]} name="Recommended" isAnimationActive={false} />
          <Bar dataKey="Selected" fill={colors.selected} radius={[4, 4, 0, 0]} name="Selected" isAnimationActive={false} />
          <Bar dataKey="Purchased" fill={colors.purchased} radius={[4, 4, 0, 0]} name="Purchased" isAnimationActive={false} />
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
    <div className="h-[160px] w-full min-h-[120px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={120} initialDimension={{ width: 400, height: 120 }}>
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
            isAnimationActive={false}
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
            isAnimationActive={false}
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
    <div className="h-[180px] w-full min-h-[120px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={120} initialDimension={{ width: 400, height: 120 }}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={tickStyle(dark)} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="country" width={80} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined, name?: string) => [`${value ?? 0}%`, name ?? '']}
          />
          <Legend wrapperStyle={legendStyle(dark)} />
          {sizes.map((s, i) => (
            <Bar key={s} dataKey={s} stackId="a" fill={palette[i]} radius={[0, 0, 0, 0]} name={s} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── Full Funnel ─── */

export function FullFunnelChart({
  widgetOpens,
  tryons,
  atc,
  purchases,
  dark,
}: {
  widgetOpens: number;
  tryons: number;
  atc: number;
  purchases: number;
  dark?: boolean;
}) {
  const steps = [
    { name: 'Widget Opens', value: widgetOpens },
    { name: 'Try-On Start', value: tryons },
    { name: 'Size Selected', value: Math.round((tryons + atc) / 2) },
    { name: 'Add to Cart', value: atc },
    { name: 'Purchase', value: purchases },
  ];

  const gradient = ['#3b82f6', '#6366f1', '#8b5cf6', '#22c55e', '#10b981'];
  const maxVal = Math.max(...steps.map((s) => s.value), 1);
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[180px] w-full min-h-[160px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={160} initialDimension={{ width: 400, height: 160 }}>
        <BarChart data={steps} layout="vertical" margin={{ top: 0, right: 60, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, maxVal]} hide />
          <YAxis type="category" dataKey="name" width={100} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined) => [value ?? 0, '']}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={24} isAnimationActive={false} label={(props: Record<string, unknown>) => {
            const y = Number(props.y ?? 0);
            const height = Number(props.height ?? 0);
            const index = Number(props.index ?? 0);
            if (index === 0) return null;
            const prev = steps[index - 1].value;
            const cur = steps[index].value;
            const drop = prev > 0 ? (((prev - cur) / prev) * 100).toFixed(0) : '0';
            return (
              <text x="100%" dx={-4} y={y + height / 2} textAnchor="end" dominantBaseline="middle" fontSize={9} fill={dark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.45)'}>
                −{drop}%
              </text>
            );
          }}>
            {steps.map((_, i) => (
              <Cell key={i} fill={gradient[i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── Device Breakdown ─── */

const DEVICE_COLORS: Record<string, string> = {
  mobile: '#0ea5e9',
  desktop: '#22c55e',
  tablet: '#f59e0b',
  unknown: '#6b7280',
};

export function DeviceBreakdownChart({
  devices,
  dark,
}: {
  devices: Array<{ device_type: string; tryons: number; purchases: number; conversion_rate?: number | null }>;
  dark?: boolean;
}) {
  if (!devices.length) return null;

  const data = devices.map((d) => ({
    name: d.device_type,
    value: d.tryons,
    conversion: d.conversion_rate ?? (d.tryons > 0 ? (d.purchases / d.tryons) * 100 : 0),
    fill: DEVICE_COLORS[d.device_type.toLowerCase()] ?? '#6b7280',
  }));

  const tt = tooltipStyle(dark);

  const renderLabel = ({ cx, cy, midAngle, outerRadius, name, conversion }: Record<string, number | string>) => {
    const RADIAN = Math.PI / 180;
    const radius = (outerRadius as number) + 18;
    const x = (cx as number) + radius * Math.cos(-(midAngle as number) * RADIAN);
    const y = (cy as number) + radius * Math.sin(-(midAngle as number) * RADIAN);
    return (
      <text x={x} y={y} textAnchor={x > (cx as number) ? 'start' : 'end'} dominantBaseline="central" fontSize={9} fill={dark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.55)'}>
        {name} {(conversion as number).toFixed(1)}%
      </text>
    );
  };

  return (
    <div className="h-[180px] w-full min-h-[160px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={160} initialDimension={{ width: 400, height: 160 }}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={55}
            innerRadius={25}
            paddingAngle={2}
            isAnimationActive={false}
            label={renderLabel}
            labelLine={false}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            isAnimationActive={false}
            formatter={(value: number | undefined, _name: string, props: { payload?: { conversion?: number } }) => {
              const conv = props.payload?.conversion;
              return [`${value ?? 0} try-ons (${conv != null ? conv.toFixed(1) : '0'}% conv)`, ''];
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── Fit Confidence ─── */

export function FitConfidenceChart({
  products,
  dark,
}: {
  products: Array<{ product_id: string; fit_confidence_score: number; most_common_deviation?: string | null }>;
  dark?: boolean;
}) {
  if (!products.length) return null;

  const data = products.slice(0, 10).map((p) => ({
    product: p.product_id.length > 14 ? p.product_id.slice(0, 14) + '…' : p.product_id,
    score: p.fit_confidence_score,
    deviation: p.most_common_deviation ?? '—',
  }));

  const scoreColor = (score: number) => (score > 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444');
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[180px] w-full min-h-[160px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={160} initialDimension={{ width: 400, height: 160 }}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, 100]} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="product" width={100} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} horizontal={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined, _name: string, props: { payload?: { deviation?: string } }) => [`${value ?? 0} (${props.payload?.deviation ?? ''})`, 'Fit score']}
          />
          <Bar dataKey="score" radius={[0, 6, 6, 0]} maxBarSize={20} isAnimationActive={false}>
            {data.map((entry, i) => (
              <Cell key={i} fill={scoreColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── Dwell Time ─── */

export function DwellTimeChart({
  avg,
  median,
  p90,
  dark,
}: {
  avg: number;
  median: number;
  p90: number;
  dark?: boolean;
}) {
  const data = [
    { label: 'Average', value: avg },
    { label: 'Median', value: median },
    { label: 'P90', value: p90 },
  ];

  const blues = ['#3b82f6', '#0ea5e9', '#06b6d4'];
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[160px] w-full min-h-[140px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={140} initialDimension={{ width: 400, height: 140 }}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} vertical={false} />
          <XAxis dataKey="label" tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(1)}s`, 'Dwell time']}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={40} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={blues[i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── Return Risk ─── */

export function ReturnRiskChart({
  orders,
  dark,
}: {
  orders: Array<{ order_id: string; risk_score: number; risk_factors: string[] }>;
  dark?: boolean;
}) {
  if (!orders.length) return null;

  const data = orders.slice(0, 10).map((o) => ({
    order: o.order_id.length > 12 ? o.order_id.slice(0, 12) + '…' : o.order_id,
    score: o.risk_score,
    factors: o.risk_factors.join(', '),
  }));

  const riskColor = (score: number) => (score > 75 ? '#ef4444' : score >= 50 ? '#f59e0b' : '#22c55e');
  const tt = tooltipStyle(dark);

  return (
    <div className="h-[180px] w-full min-h-[160px] min-w-0">
      <ResponsiveContainer width="100%" height="100%" minHeight={160} initialDimension={{ width: 400, height: 160 }}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, 100]} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="order" width={90} tick={tickStyle(dark)} axisLine={false} tickLine={false} />
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke(dark)} horizontal={false} />
          <Tooltip
            contentStyle={tt.contentStyle}
            labelStyle={tt.labelStyle}
            itemStyle={tt.itemStyle}
            cursor={tt.cursor}
            isAnimationActive={false}
            formatter={(value: number | undefined, _name: string, props: { payload?: { factors?: string } }) => [`${value ?? 0} — ${props.payload?.factors ?? ''}`, 'Risk']}
          />
          <Bar dataKey="score" radius={[0, 6, 6, 0]} maxBarSize={20} isAnimationActive={false}>
            {data.map((entry, i) => (
              <Cell key={i} fill={riskColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
