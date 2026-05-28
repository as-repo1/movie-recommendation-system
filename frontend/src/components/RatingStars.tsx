import { Star } from 'lucide-react';

interface RatingStarsProps {
  value: number;       // 0-10
  onChange?: (v: number) => void;
  readonly?: boolean;
  size?: number;
}

export function RatingStars({ value, onChange, readonly = false, size = 20 }: RatingStarsProps) {
  // Display 10 stars (each representing 1 point)
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
      {Array.from({ length: 10 }, (_, i) => {
        const starVal = i + 1;
        const filled = starVal <= value;
        return (
          <Star
            key={i}
            size={size}
            fill={filled ? '#f59e0b' : 'none'}
            color={filled ? '#f59e0b' : '#475569'}
            className={readonly ? '' : 'star'}
            onClick={readonly ? undefined : () => onChange?.(starVal)}
            style={{ cursor: readonly ? 'default' : 'pointer' }}
          />
        );
      })}
      {value > 0 && (
        <span style={{ marginLeft: 6, fontSize: '0.85rem', color: '#fcd34d', fontWeight: 600 }}>
          {value}/10
        </span>
      )}
    </div>
  );
}
