/**
 * Badge Component
 *
 * Small, colored labels for statuses, categories, and tags.
 * Uses design tokens for semantic colors.
 *
 * @example
 * <Badge variant="success">Active</Badge>
 * <Badge variant="warning">Pending</Badge>
 * <Badge variant="error">Failed</Badge>
 */

import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Badge color variant */
  variant?: 'neutral' | 'success' | 'warning' | 'error' | 'info';

  /** Custom icon to display before children */
  icon?: React.ReactNode;
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'neutral', icon, className = '', children, ...props }, ref) => {
    // Build class names
    const baseClasses = 'badge';
    const variantClasses = `badge-${variant}`;
    const customClasses = className;

    const allClasses = [baseClasses, variantClasses, customClasses]
      .filter(Boolean)
      .join(' ');

    return (
      <span ref={ref} className={allClasses} {...props}>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
