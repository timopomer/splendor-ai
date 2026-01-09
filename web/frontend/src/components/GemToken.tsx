import type { GemType } from '../types/game';
import { GEM_COLORS, GEM_TEXT_COLORS } from '../types/game';

interface GemTokenProps {
  gem: GemType;
  count?: number;
  size?: 'sm' | 'md' | 'lg';
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  showCount?: boolean;
  testId?: string;
}

const SIZES = {
  sm: 'w-8 h-8 text-sm',
  md: 'w-12 h-12 text-lg',
  lg: 'w-16 h-16 text-2xl',
};

export function GemToken({
  gem,
  count,
  size = 'md',
  selected = false,
  disabled = false,
  onClick,
  showCount = true,
  testId,
}: GemTokenProps) {
  const isClickable = onClick && !disabled;
  
  return (
    <button
      onClick={onClick}
      disabled={disabled || !onClick}
      className={`
        gem-token ${SIZES[size]}
        ${selected ? 'selected' : ''}
        ${isClickable ? 'cursor-pointer hover:scale-110' : 'cursor-default'}
        ${disabled ? 'opacity-50' : ''}
      `}
      style={{
        backgroundColor: GEM_COLORS[gem],
        color: GEM_TEXT_COLORS[gem],
      }}
      data-testid={testId || `gem-${gem}`}
    >
      {showCount && count !== undefined ? count : null}
    </button>
  );
}

interface GemCostProps {
  cost: Record<GemType, number>;
  bonuses?: Record<GemType, number>;
  tokens?: Record<GemType, number>;
}

export function GemCost({ cost, bonuses, tokens }: GemCostProps) {
  const gems: GemType[] = ['diamond', 'sapphire', 'emerald', 'ruby', 'onyx'];
  
  return (
    <div className="flex flex-col gap-1">
      {gems.map((gem) => {
        const costVal = cost[gem];
        if (costVal === 0) return null;
        
        const bonusVal = bonuses?.[gem] || 0;
        const tokenVal = tokens?.[gem] || 0;
        const covered = bonusVal + tokenVal;
        const needed = Math.max(0, costVal - covered);
        
        return (
          <div key={gem} className="flex items-center gap-1">
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
              style={{
                backgroundColor: GEM_COLORS[gem],
                color: GEM_TEXT_COLORS[gem],
              }}
            >
              {costVal}
            </div>
            {bonuses && needed > 0 && (
              <span className="text-xs text-red-400">-{needed}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

