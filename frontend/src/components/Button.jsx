/**
 * FILE: frontend/src/components/Button.jsx
 * ==================================================
 * Standardized Button Component
 * ==================================================
 * 
 * This component provides consistent button styling across the entire
 * application. It uses the design system tokens to ensure visual
 * consistency and prevent UI inconsistencies.
 * 
 * VARIANTS:
 *   - primary: Main action buttons with gradient background
 *   - secondary: Secondary actions with border
 *   - danger: Destructive actions with red gradient
 *   - success: Positive actions with green gradient
 *   - ghost: Transparent background with hover effects
 * 
 * SIZES:
 *   - sm: Small buttons for compact spaces
 *   - md: Default button size
 *   - lg: Large buttons for primary actions
 * 
 * USAGE:
 *   <Button variant="primary" size="md" onClick={handleClick}>
 *     Submit
 *   </Button>
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Standardized Button Component
 * 
 * @param {Object} props
 * @param {string} props.variant - Button variant (primary, secondary, danger, success, ghost)
 * @param {string} props.size - Button size (sm, md, lg)
 * @param {boolean} props.loading - Show loading state
 * @param {boolean} props.disabled - Disable button
 * @param {boolean} props.fullWidth - Make button full width
 * @param {React.ReactNode} props.children - Button content
 * @param {Function} props.onClick - Click handler
 * @param {string} props.className - Additional CSS classes
 * @param {React.ReactNode} props.icon - Icon to display before text
 * @param {string} props.type - Button type (button, submit, reset)
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  fullWidth = false,
  children,
  onClick,
  className = '',
  icon,
  type = 'button',
  ...props
}) {
  // Build CSS classes using design system
  const baseClasses = 'btn-base';
  
  // Variant classes
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
    success: 'btn-success',
    ghost: 'btn-secondary'
  };
  
  // Size classes
  const sizeClasses = {
    sm: 'btn-sm',
    md: '',
    lg: 'btn-lg'
  };
  
  // Width class
  const widthClass = fullWidth ? 'w-full' : '';
  
  // Combine all classes
  const buttonClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.primary,
    sizeClasses[size] || sizeClasses.md,
    widthClass,
    className
  ].filter(Boolean).join(' ');
  
  // Handle click events
  const handleClick = (e) => {
    if (loading || disabled) {
      e.preventDefault();
      return;
    }
    onClick?.(e);
  };
  
  return (
    <button
      type={type}
      className={buttonClasses}
      onClick={handleClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <Loader2 
          size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16}
          className="animate-spin"
          aria-hidden="true"
        />
      )}
      
      {!loading && icon && (
        <span 
          className="flex-shrink-0" 
          aria-hidden="true"
        >
          {icon}
        </span>
      )}
      
      <span className={loading ? 'opacity-0' : 'opacity-100'}>
        {children}
      </span>
    </button>
  );
}

/**
 * Button Group Component
 * For grouping related buttons together
 */
export function ButtonGroup({ children, spacing = 'sm', className = '', ...props }) {
  const spacingClasses = {
    sm: 'gap-2',
    md: 'gap-3',
    lg: 'gap-4'
  };
  
  return (
    <div 
      className={`flex items-center ${spacingClasses[spacing]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Icon Button Component
 * For buttons that only contain an icon
 */
export function IconButton({
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled = false,
  children,
  onClick,
  className = '',
  type = 'button',
  ...props
}) {
  const baseClasses = 'btn-base';
  
  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
    success: 'btn-success',
    ghost: 'btn-secondary'
  };
  
  const sizeClasses = {
    sm: 'p-2',
    md: 'p-3',
    lg: 'p-4'
  };
  
  const buttonClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.secondary,
    sizeClasses[size] || sizeClasses.md,
    className
  ].filter(Boolean).join(' ');
  
  const handleClick = (e) => {
    if (loading || disabled) {
      e.preventDefault();
      return;
    }
    onClick?.(e);
  };
  
  return (
    <button
      type={type}
      className={buttonClasses}
      onClick={handleClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 
          size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16}
          className="animate-spin"
          aria-hidden="true"
        />
      ) : (
        <span className="flex-shrink-0" aria-hidden="true">
          {children}
        </span>
      )}
    </button>
  );
}


