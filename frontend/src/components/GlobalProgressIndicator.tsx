/**
 * Global Progress Indicator
 *
 * Small indicator in the header showing active classification operations.
 * Displays count of active operations and provides access to notification center.
 *
 * Features:
 * - Minimal UI when collapsed (just count + pulsing dot)
 * - Click to expand notification center
 * - Keyboard shortcut: Cmd+Shift+N
 * - Real-time updates from ProgressContext
 *
 * @example
 * <GlobalProgressIndicator onOpenNotifications={() => setShowNotifications(true)} />
 */

import React, { useEffect, useState } from 'react';
import { Activity, Bell, BellRing } from 'lucide-react';
import { useProgress } from '../contexts/ProgressContext';

export interface GlobalProgressIndicatorProps {
  /** Callback when notification center should open */
  onOpenNotifications?: () => void;

  /** Custom className */
  className?: string;
}

export const GlobalProgressIndicator: React.FC<GlobalProgressIndicatorProps> = ({
  onOpenNotifications,
  className = '',
}) => {
  const { activeOperations } = useProgress();
  const [isAnimating, setIsAnimating] = useState(false);

  const activeCount = activeOperations.size;
  const hasActive = activeCount > 0;

  // Trigger animation when count changes
  useEffect(() => {
    if (hasActive) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 300);
      return () => clearTimeout(timer);
    }
  }, [activeCount, hasActive]);

  // Keyboard shortcut: Cmd+Shift+N
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        onOpenNotifications?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onOpenNotifications]);

  return (
    <button
      onClick={onOpenNotifications}
      className={`
        relative flex items-center gap-2 px-3 py-2 rounded-lg
        transition-all duration-200
        hover:bg-gray-100
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500
        ${isAnimating ? 'scale-105' : 'scale-100'}
        ${className}
      `}
      title={
        hasActive
          ? `${activeCount} classification${activeCount > 1 ? 's' : ''} in progress`
          : 'View notification history'
      }
      aria-label={hasActive ? `${activeCount} active operations` : 'Notifications'}
    >
      {/* Icon */}
      <div className="relative">
        {hasActive ? (
          <BellRing className="h-5 w-5 text-gray-700" />
        ) : (
          <Bell className="h-5 w-5 text-gray-500" />
        )}

        {/* Pulsing dot for active operations */}
        {hasActive && (
          <div className="absolute -top-1 -right-1">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-600"></span>
            </div>
          </div>
        )}

        {/* Count badge */}
        {hasActive && (
          <div
            className="
              absolute -top-2 -right-2
              min-w-[1.25rem] h-5 px-1
              flex items-center justify-center
              bg-blue-600 text-white
              text-xs font-semibold
              rounded-full
              border-2 border-white
            "
          >
            {activeCount}
          </div>
        )}
      </div>

      {/* Text (hidden on mobile) */}
      <span className="hidden md:block text-sm font-medium text-gray-700">
        {hasActive ? (
          <span className="flex items-center gap-1.5">
            <Activity className="h-4 w-4 animate-pulse-subtle" />
            {activeCount} active
          </span>
        ) : (
          'Notifications'
        )}
      </span>
    </button>
  );
};

export default GlobalProgressIndicator;
