import React from 'react';

interface BulletChartProps {
  val: number;
  refLow: number;
  refHigh: number;
  unit: string;
  testName: string;
  status: 'Low' | 'High' | 'Normal';
  isPdfMode?: boolean;
}

const BulletChart: React.FC<BulletChartProps> = ({
  val,
  refLow,
  refHigh,
  unit,
  testName,
  status,
  isPdfMode = false,
}) => {
  const diff = refHigh - refLow;
  const plotMin = Math.min(refLow - diff * 0.5, val - diff * 0.2);
  const plotMax = Math.max(refHigh + diff * 0.5, val + diff * 0.2);
  const range = plotMax - plotMin;

  const getX = (v: number) => ((v - plotMin) / range) * 100;

  const zoneMin = refLow - diff * 0.5;
  const zoneMax = refHigh + diff * 0.5;

  const barY = 40;
  const barHeight = 15;

  return (
    <div className={`flex items-center w-full ${isPdfMode ? 'py-1' : 'py-2'}`}>
      <div className="w-1/4 pr-4">
        <div className="font-bold text-sm text-slate-800">{testName}</div>
        <div className="text-[10px] text-slate-500">{unit}</div>
      </div>
      
      <div className="flex-1 relative h-16">
        <svg width="100%" height="100%" viewBox="0 0 400 64" preserveAspectRatio="none">
          {/* Background zones */}
          <rect x={`${getX(zoneMin)}%`} y={barY} width={`${getX(refLow) - getX(zoneMin)}%`} height={barHeight} fill="#fdecea" />
          <rect x={`${getX(refLow)}%`} y={barY} width={`${getX(refHigh) - getX(refLow)}%`} height={barHeight} fill="#6ee7b7" />
          <rect x={`${getX(refHigh)}%`} y={barY} width={`${getX(zoneMax) - getX(refHigh)}%`} height={barHeight} fill="#fdecea" />
          
          {/* Reference labels */}
          <text x={`${getX(refLow)}%`} y={barY + barHeight + 12} fontSize="10" textAnchor="middle" fill="#666">{refLow}</text>
          <text x={`${getX(refHigh)}%`} y={barY + barHeight + 12} fontSize="10" textAnchor="middle" fill="#666">{refHigh}</text>
          
          {/* Value Indicator (Triangle) */}
          <path 
            d={`M ${getX(val)}% ${barY - 2} L ${getX(val) - 1.5}% ${barY - 8} L ${getX(val) + 1.5}% ${barY - 8} Z`} 
            fill="black" 
          />
          <text x={`${getX(val)}%`} y={barY - 12} fontSize="12" fontWeight="bold" textAnchor="middle" fill="black">{val}</text>
          
          {/* Base line */}
          <line x1="0" y1={barY + barHeight} x2="100%" y2={barY + barHeight} stroke="black" strokeWidth="1" />
        </svg>
      </div>

      <div className="w-20 pl-4 text-right">
        <span className={`font-bold text-sm ${
          status === 'Normal' ? 'text-green-600' : 
          status === 'Low' ? 'text-orange-500' : 'text-red-600'
        }`}>
          {status}
        </span>
      </div>
    </div>
  );
};

export default BulletChart;
