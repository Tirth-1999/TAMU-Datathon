/**
 * Button Component
 *
 * Modern, accessible button component with multiple variants and sizes.
 * Uses design tokens for consistent styling across the application.
 *
 * @example
 * <Button variant="primary" size="md">Click me</Button>
 * <Button variant="secondary" icon={<Plus />}>Add Item</Button>
 * <Button variant="ghost" loading>Processing...</Button>
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Button visual style */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';

  /** Button size */
  size?: 'sm' | 'md' | 'lg';

  /** Show loading spinner */
  loading?: boolean;

  /** Icon element to display before children */
  icon?: React.ReactNode;

  /** Make button full width */
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      fullWidth = false,
      className = '',
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    // Build class names
    const baseClasses = 'btn';
    const variantClasses = `btn-${variant}`;
    const sizeClasses = size !== 'md' ? `btn-${size}` : '';
    const widthClasses = fullWidth ? 'w-full' : '';
    const customClasses = className;

    const allClasses = [
      baseClasses,
      variantClasses,
      sizeClasses,
      widthClasses,
      customClasses,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        className={allClasses}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : icon ? (
          <span className="flex-shrink-0">{icon}</span>
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
