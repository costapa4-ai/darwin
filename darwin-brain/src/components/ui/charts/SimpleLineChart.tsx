import { useMemo } from 'react';

interface DataPoint {
  x: string | number;
  y: number;
}

interface SimpleLineChartProps {
  data: DataPoint[];
  width?: number;
  height?: number;
  lineColor?: string;
  fillColor?: string;
  showGrid?: boolean;
  showDots?: boolean;
  showLabels?: boolean;
  labelFormatter?: (value: number) => string;
  xAxisFormatter?: (value: string | number) => string;
}

export function SimpleLineChart({
  data,
  width = 300,
  height = 150,
  lineColor = '#06b6d4',
  fillColor = 'rgba(6, 182, 212, 0.1)',
  showGrid = true,
  showDots = true,
  showLabels = false,
  labelFormatter = (v) => String(v),
  xAxisFormatter = (v) => String(v),
}: SimpleLineChartProps) {
  const { path, fillPath, points, yMin, yMax, xLabels } = useMemo(() => {
    if (!data || data.length === 0) {
      return { path: '', fillPath: '', points: [], yMin: 0, yMax: 0, xLabels: [] };
    }

    const values = data.map((d) => d.y);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 1;

    const padding = { top: 20, right: 10, bottom: 30, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const pointsArr = data.map((d, i) => {
      const x = padding.left + (i / (data.length - 1 || 1)) * chartWidth;
      const y = padding.top + chartHeight - ((d.y - minVal) / range) * chartHeight;
      return { x, y, value: d.y, label: d.x };
    });

    const pathD = pointsArr
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
      .join(' ');

    const fillD =
      pathD +
      ` L ${pointsArr[pointsArr.length - 1]?.x || 0} ${padding.top + chartHeight}` +
      ` L ${pointsArr[0]?.x || 0} ${padding.top + chartHeight} Z`;

    // Generate x-axis labels (show first, middle, last)
    const labels: { x: number; label: string }[] = [];
    if (data.length > 0) {
      labels.push({ x: pointsArr[0].x, label: xAxisFormatter(data[0].x) });
      if (data.length > 2) {
        const mid = Math.floor(data.length / 2);
        labels.push({ x: pointsArr[mid].x, label: xAxisFormatter(data[mid].x) });
      }
      if (data.length > 1) {
        labels.push({
          x: pointsArr[pointsArr.length - 1].x,
          label: xAxisFormatter(data[data.length - 1].x),
        });
      }
    }

    return {
      path: pathD,
      fillPath: fillD,
      points: pointsArr,
      yMin: minVal,
      yMax: maxVal,
      xLabels: labels,
    };
  }, [data, width, height, xAxisFormatter]);

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-gray-500 text-sm"
        style={{ width, height }}
      >
        No data available
      </div>
    );
  }

  const padding = { top: 20, right: 10, bottom: 30, left: 10 };
  const chartHeight = height - padding.top - padding.bottom;

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Grid lines */}
      {showGrid && (
        <g className="grid" stroke="rgba(255,255,255,0.1)">
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
            <line
              key={ratio}
              x1={padding.left}
              y1={padding.top + chartHeight * (1 - ratio)}
              x2={width - padding.right}
              y2={padding.top + chartHeight * (1 - ratio)}
              strokeDasharray="4 4"
            />
          ))}
        </g>
      )}

      {/* Fill area */}
      <path d={fillPath} fill={fillColor} />

      {/* Line */}
      <path d={path} fill="none" stroke={lineColor} strokeWidth={2} strokeLinecap="round" />

      {/* Dots */}
      {showDots &&
        points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={3}
            fill={lineColor}
            className="transition-all hover:r-5"
          >
            <title>
              {p.label}: {labelFormatter(p.value)}
            </title>
          </circle>
        ))}

      {/* Y-axis labels */}
      {showLabels && (
        <g className="y-labels" fill="rgba(255,255,255,0.5)" fontSize={10}>
          <text x={padding.left} y={padding.top - 5} textAnchor="start">
            {labelFormatter(yMax)}
          </text>
          <text x={padding.left} y={height - padding.bottom + 15} textAnchor="start">
            {labelFormatter(yMin)}
          </text>
        </g>
      )}

      {/* X-axis labels */}
      <g className="x-labels" fill="rgba(255,255,255,0.5)" fontSize={10}>
        {xLabels.map((label, i) => (
          <text
            key={i}
            x={label.x}
            y={height - 5}
            textAnchor={i === 0 ? 'start' : i === xLabels.length - 1 ? 'end' : 'middle'}
          >
            {label.label}
          </text>
        ))}
      </g>
    </svg>
  );
}

export default SimpleLineChart;
