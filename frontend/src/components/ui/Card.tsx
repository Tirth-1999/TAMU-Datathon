/**
 * Card Component
 *
 * Container component with consistent styling, shadows, and borders.
 * Supports interactive (clickable) and non-interactive variants.
 *
 * @example
 * <Card>Basic card content</Card>
 * <Card interactive onClick={() => handleClick()}>Clickable card</Card>
 * <Card padding="sm">Card with small padding</Card>
 */

import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Make card clickable with hover effects */
  interactive?: boolean;

  /** Padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg';

  /** Show border */
  bordered?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      interactive = false,
      padding = 'md',
      bordered = true,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    // Build class names
    const baseClasses = 'card';
    const interactiveClasses = interactive ? 'card-interactive' : '';
    const borderClasses = !bordered ? 'border-0' : '';

    // Padding classes based on size
    const paddingClasses = {
      none: 'p-0',
      sm: 'p-3 sm:p-4',
      md: 'p-4 sm:p-6',
      lg: 'p-6 sm:p-8',
    }[padding];

    const customClasses = className;

    const allClasses = [
      baseClasses,
      interactiveClasses,
      paddingClasses,
      borderClasses,
      customClasses,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div ref={ref} className={allClasses} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

/**
 * Card Header Component
 * Section for card titles and actions
 */
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Title text */
  title?: string;

  /** Subtitle text */
  subtitle?: string;

  /** Actions to display on the right */
  actions?: React.ReactNode;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, subtitle, actions, className = '', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-start justify-between gap-4 ${className}`}
        {...props}
      >
        <div className="flex-1 min-w-0">
          {title && (
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
          )}
          {children}
        </div>
        {actions && <div className="flex-shrink-0">{actions}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

/**
 * Card Footer Component
 * Section for card actions and secondary content
 */
export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Add border top */
  divided?: boolean;
}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ divided = false, className = '', children, ...props }, ref) => {
    const dividerClasses = divided ? 'border-t border-gray-200 pt-4 mt-4' : '';

    return (
      <div
        ref={ref}
        className={`${dividerClasses} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export default Card;
