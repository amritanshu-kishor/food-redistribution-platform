import React from 'react';

interface ChartDataPoint {
  label: string;
  value: number;
}

interface BarChartProps {
  data: ChartDataPoint[];
  color?: string;
  height?: number;
}

export const BarChart: React.FC<BarChartProps> = ({ data, color = '#2D5A27', height = 160 }) => {
  if (!data || data.length === 0) {
    return <div className="h-full flex items-center justify-center text-xs text-brand-stone-dark">No data available</div>;
  }
  
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const width = 500;
  const paddingLeft = 40;
  const paddingRight = 10;
  const paddingTop = 20;
  const paddingBottom = 30;
  
  const chartHeight = height - paddingTop - paddingBottom;
  const chartWidth = width - paddingLeft - paddingRight;
  const spacing = chartWidth / data.length;
  const barWidth = Math.min(24, spacing * 0.6);
  
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      {/* Horizontal gridlines and Y-axis text */}
      {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
        const y = paddingTop + chartHeight * (1 - p);
        const gridVal = Math.round(maxValue * p * 10) / 10;
        return (
          <g key={idx}>
            <line
              x1={paddingLeft}
              y1={y}
              x2={width - paddingRight}
              y2={y}
              stroke="#E7E5E4"
              strokeWidth="0.5"
              strokeDasharray="3,3"
            />
            <text
              x={paddingLeft - 8}
              y={y + 3}
              textAnchor="end"
              className="text-[10px] fill-brand-charcoal/50 font-sans"
            >
              {gridVal}
            </text>
          </g>
        );
      })}
      
      {/* Bars */}
      {data.map((d, idx) => {
        const x = paddingLeft + spacing * idx + (spacing - barWidth) / 2;
        const barHeight = (d.value / maxValue) * chartHeight;
        const y = paddingTop + chartHeight - barHeight;
        
        return (
          <g key={idx} className="group cursor-pointer">
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              fill={color}
              rx="1.5"
              className="transition-all duration-300 group-hover:opacity-90"
            />
            <text
              x={x + barWidth / 2}
              y={paddingTop + chartHeight + 15}
              textAnchor="middle"
              className="text-[9px] fill-brand-charcoal/70 font-sans truncate"
              style={{ maxWidth: spacing }}
            >
              {d.label.length > 8 ? `${d.label.substring(0, 6)}..` : d.label}
            </text>
            <title>{`${d.label}: ${d.value}`}</title>
          </g>
        );
      })}
      
      {/* Base Line */}
      <line
        x1={paddingLeft}
        y1={paddingTop + chartHeight}
        x2={width - paddingRight}
        y2={paddingTop + chartHeight}
        stroke="#1C1C1C"
        strokeWidth="1"
      />
    </svg>
  );
};

export const AreaChart: React.FC<BarChartProps> = ({ data, color = '#2D5A27', height = 160 }) => {
  if (!data || data.length === 0) {
    return <div className="h-full flex items-center justify-center text-xs text-brand-stone-dark">No data available</div>;
  }
  
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const width = 500;
  const paddingLeft = 40;
  const paddingRight = 10;
  const paddingTop = 20;
  const paddingBottom = 30;
  
  const chartHeight = height - paddingTop - paddingBottom;
  const chartWidth = width - paddingLeft - paddingRight;
  const spacing = data.length > 1 ? chartWidth / (data.length - 1) : chartWidth;
  
  // Build area and line path points
  const points = data.map((d, idx) => {
    const x = paddingLeft + spacing * idx;
    const y = paddingTop + chartHeight - (d.value / maxValue) * chartHeight;
    return { x, y, val: d.value, label: d.label };
  });
  
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = points.length > 0 
    ? `${linePath} L ${points[points.length - 1].x} ${paddingTop + chartHeight} L ${points[0].x} ${paddingTop + chartHeight} Z`
    : '';
    
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      {/* Gridlines */}
      {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
        const y = paddingTop + chartHeight * (1 - p);
        const gridVal = Math.round(maxValue * p * 10) / 10;
        return (
          <g key={idx}>
            <line
              x1={paddingLeft}
              y1={y}
              x2={width - paddingRight}
              y2={y}
              stroke="#E7E5E4"
              strokeWidth="0.5"
              strokeDasharray="3,3"
            />
            <text
              x={paddingLeft - 8}
              y={y + 3}
              textAnchor="end"
              className="text-[10px] fill-brand-charcoal/50 font-sans"
            >
              {gridVal}
            </text>
          </g>
        );
      })}
      
      {/* Area Shading */}
      {areaPath && (
        <path
          d={areaPath}
          fill="url(#area-gradient)"
          className="opacity-25"
        />
      )}
      
      {/* Line Path */}
      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth="2"
        />
      )}
      
      {/* Gradient definition */}
      <defs>
        <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      
      {/* Axis Data Points */}
      {points.map((p, idx) => (
        <g key={idx} className="group cursor-pointer">
          <circle
            cx={p.x}
            cy={p.y}
            r="4"
            fill="#FAF9F6"
            stroke={color}
            strokeWidth="2"
            className="transition-all duration-200 group-hover:r-6"
          />
          <text
            x={p.x}
            y={paddingTop + chartHeight + 15}
            textAnchor="middle"
            className="text-[9px] fill-brand-charcoal/70 font-sans"
          >
            {p.label}
          </text>
          <title>{`${p.label}: ${p.val}`}</title>
        </g>
      ))}
      
      {/* Base Line */}
      <line
        x1={paddingLeft}
        y1={paddingTop + chartHeight}
        x2={width - paddingRight}
        y2={paddingTop + chartHeight}
        stroke="#1C1C1C"
        strokeWidth="1"
      />
    </svg>
  );
};

export const DonutChart: React.FC<{ data: ChartDataPoint[] }> = ({ data }) => {
  if (!data || data.length === 0) {
    return <div className="h-full flex items-center justify-center text-xs text-brand-stone-dark">No data available</div>;
  }
  
  const total = data.reduce((acc, curr) => acc + curr.value, 0);
  const size = 180;
  const radius = 50;
  const strokeWidth = 14;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  
  const colorsList = ['#2D5A27', '#8FBC8F', '#A3B18A', '#4A7A44', '#1C3B18'];
  
  let accumulatedAngle = 0;
  
  const segments = data.map((d, idx) => {
    const percentage = total > 0 ? d.value / total : 0;
    const strokeDasharray = `${percentage * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedAngle * circumference;
    accumulatedAngle += percentage;
    
    return {
      ...d,
      strokeDasharray,
      strokeDashoffset,
      color: colorsList[idx % colorsList.length]
    };
  });
  
  return (
    <div className="flex flex-col md:flex-row items-center justify-center gap-6 w-full h-full">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="transparent"
          stroke="#FAF9F6"
          strokeWidth={strokeWidth}
        />
        {segments.map((s, idx) => (
          <circle
            key={idx}
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke={s.color}
            strokeWidth={strokeWidth}
            strokeDasharray={s.strokeDasharray}
            strokeDashoffset={s.strokeDashoffset}
            transform={`rotate(-90 ${center} ${center})`}
            className="transition-all duration-300 hover:stroke-[16]"
          >
            <title>{`${s.label}: ${s.value} (${Math.round((total > 0 ? s.value / total : 0) * 100)}%)`}</title>
          </circle>
        ))}
        {/* Center label */}
        <text x={center} y={center - 2} textAnchor="middle" className="text-[10px] font-medium fill-brand-charcoal/50 uppercase tracking-wider">
          Total
        </text>
        <text x={center} y={center + 12} textAnchor="middle" className="text-base font-bold fill-brand-charcoal">
          {total}
        </text>
      </svg>
      
      {/* Legend */}
      <div className="flex flex-col gap-2 font-sans text-xs">
        {segments.map((s, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: s.color }} />
            <span className="text-brand-charcoal/80 font-medium">{s.label}:</span>
            <span className="text-brand-charcoal font-bold">{s.value}</span>
            <span className="text-brand-stone-dark font-normal">
              ({total > 0 ? Math.round((s.value / total) * 100) : 0}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
