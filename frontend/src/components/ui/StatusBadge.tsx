/**
 * StatusBadge Component
 *
 * Specialized badge for document classification statuses.
 * Automatically maps classification levels to appropriate colors and icons.
 *
 * @example
 * <StatusBadge status="Public" />
 * <StatusBadge status="Confidential" confidence={95} />
 * <StatusBadge status="Highly Sensitive" showIcon />
 */

import React from 'react';
import { Shield, AlertTriangle, AlertCircle, Ban } from 'lucide-react';
import { Badge, BadgeProps } from './Badge';

type ClassificationStatus =
  | 'Public'
  | 'Confidential'
  | 'Highly Sensitive'
  | 'Sensitive'
  | 'Unsafe';

export interface StatusBadgeProps extends Omit<BadgeProps, 'variant' | 'icon'> {
  /** Classification status */
  status: ClassificationStatus | string;

  /** Confidence score (0-100) */
  confidence?: number;

  /** Show confidence percentage */
  showConfidence?: boolean;

  /** Show status icon */
  showIcon?: boolean;
}

// Map status to badge variant and icon
const statusConfig: Record<
  ClassificationStatus,
  { variant: BadgeProps['variant']; icon: React.ReactNode; bgGradient: string }
> = {
  Public: {
    variant: 'success',
    icon: <Shield className="h-3 w-3" />,
    bgGradient: 'bg-gradient-to-r from-green-500 to-emerald-600',
  },
  Confidential: {
    variant: 'warning',
    icon: <AlertTriangle className="h-3 w-3" />,
    bgGradient: 'bg-gradient-to-r from-yellow-500 to-orange-500',
  },
  'Highly Sensitive': {
    variant: 'error',
    icon: <AlertCircle className="h-3 w-3" />,
    bgGradient: 'bg-gradient-to-r from-red-500 to-rose-600',
  },
  Sensitive: {
    variant: 'error',
    icon: <AlertCircle className="h-3 w-3" />,
    bgGradient: 'bg-gradient-to-r from-red-500 to-rose-600',
  },
  Unsafe: {
    variant: 'error',
    icon: <Ban className="h-3 w-3" />,
    bgGradient: 'bg-gradient-to-r from-purple-500 to-pink-600',
  },
};

export const StatusBadge = React.forwardRef<HTMLSpanElement, StatusBadgeProps>(
  (
    {
      status,
      confidence,
      showConfidence = false,
      showIcon = true,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    // Get configuration for this status
    const config = statusConfig[status as ClassificationStatus] || {
      variant: 'neutral' as const,
      icon: null,
      bgGradient: '',
    };

    // Format confidence if needed
    const confidenceText =
      showConfidence && confidence ? ` (${Math.round(confidence)}%)` : '';

    // Override className for unsafe status (purple theme)
    const isUnsafe = status === 'Unsafe';
    const unsafeClasses = isUnsafe ? 'status-unsafe' : '';
    
    // Enhanced styling with gradient and shadow
    const enhancedClasses = `${config.bgGradient} text-white font-bold shadow-lg border-none`;

    return (
      <Badge
        ref={ref}
        variant={config.variant}
        icon={showIcon ? config.icon : undefined}
        className={`${unsafeClasses} ${enhancedClasses} ${className}`.trim()}
        {...props}
      >
        {children || `${status}${confidenceText}`}
      </Badge>
    );
  }
);

StatusBadge.displayName = 'StatusBadge';

export default StatusBadge;
