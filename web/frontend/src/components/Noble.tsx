import type { Noble as NobleType } from '../types/game';
import { GEM_COLORS, GEM_TEXT_COLORS, BASE_GEMS } from '../types/game';

interface NobleProps {
  noble: NobleType;
  testId?: string;
}

export function Noble({ noble, testId }: NobleProps) {
  return (
    <div
      className="noble-tile w-28 h-24 flex flex-col p-3"
      data-testid={testId}
    >
      {/* Points */}
      <div className="text-2xl font-bold text-white text-center mb-1">
        {noble.points}
      </div>
      
      {/* Requirements - all in one row */}
      <div className="mt-auto flex gap-1.5 justify-center">
        {BASE_GEMS.map((gem) => {
          const req = noble.requirements[gem];
          if (req === 0) return null;
          
          return (
            <div
              key={gem}
              className="w-6 h-6 rounded-md flex items-center justify-center text-sm font-bold"
              style={{
                backgroundColor: GEM_COLORS[gem],
                color: GEM_TEXT_COLORS[gem],
              }}
            >
              {req}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface NobleRowProps {
  nobles: NobleType[];
}

export function NobleRow({ nobles }: NobleRowProps) {
  return (
    <div className="flex gap-4 items-center">
      <span className="text-sm text-gray-400 font-medium w-14">Nobles</span>
      <div className="flex gap-4">
        {nobles.map((noble) => (
          <Noble key={noble.id} noble={noble} testId={`noble-${noble.id}`} />
        ))}
      </div>
    </div>
  );
}
