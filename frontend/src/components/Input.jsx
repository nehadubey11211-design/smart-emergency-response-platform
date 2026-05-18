/**
 * FILE: frontend/src/components/Input.jsx
 * ==================================================
 * Standardized Input Component
 * ==================================================
 * 
 * This component provides consistent input styling across the entire
 * application. It uses the design system tokens to ensure visual
 * consistency and prevent UI inconsistencies.
 * 
 * VARIANTS:
 *   - default: Standard input field
 *   - error: Input field with error styling
 *   - success: Input field with success styling
 *   - ghost: Transparent background input
 * 
 * SIZES:
 *   - sm: Small input for compact spaces
 *   - md: Default input size
 *   - lg: Large input for primary forms
 * 
 * USAGE:
 *   <Input
 *     variant="default"
 *     size="md"
 *     placeholder="Enter text..."
 *     value={value}
 *     onChange={handleChange}
 *   />
 */

import React from 'react';

/**
 * Standardized Input Component
 * 
 * @param {Object} props
 * @param {string} props.variant - Input variant (default, error, success, ghost)
 * @param {string} props.size - Input size (sm, md, lg)
 * @param {boolean} props.disabled - Disable input
 * @param {boolean} props.fullWidth - Make input full width
 * @param {string} props.placeholder - Placeholder text
 * @param {string} props.value - Input value
 * @param {Function} props.onChange - Change handler
 * @param {Function} props.onFocus - Focus handler
 * @param {Function} props.onBlur - Blur handler
 * @param {string} props.type - Input type
 * @param {string} props.name - Input name
 * @param {string} props.id - Input id
 * @param {boolean} props.required - Required field
 * @param {React.ReactNode} props.icon - Icon to display inside input
 * @param {string} props.className - Additional CSS classes
 */
export default function Input({
  variant = 'default',
  size = 'md',
  disabled = false,
  fullWidth = true,
  placeholder,
  value,
  onChange,
  onFocus,
  onBlur,
  type = 'text',
  name,
  id,
  required = false,
  icon,
  className = '',
  ...props
}) {
  // Build CSS classes using design system
  const baseClasses = 'input-base';
  
  // Variant classes
  const variantClasses = {
    default: '',
    error: 'input-error',
    success: 'input-success',
    ghost: 'bg-transparent border-transparent hover:bg-gray-800/50'
  };
  
  // Size classes
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: '',
    lg: 'px-4 py-3 text-base'
  };
  
  // Width class
  const widthClass = fullWidth ? 'w-full' : '';
  
  // Icon padding class
  const iconPaddingClass = icon ? 'pl-10' : '';
  
  // Combine all classes
  const inputClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    sizeClasses[size] || sizeClasses.md,
    widthClass,
    iconPaddingClass,
    className
  ].filter(Boolean).join(' ');
  
  return (
    <div className={`relative ${fullWidth ? 'w-full' : ''}`}>
      {icon && (
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          {icon}
        </div>
      )}
      
      <input
        type={type}
        name={name}
        id={id}
        value={value}
        onChange={onChange}
        onFocus={onFocus}
        onBlur={onBlur}
        disabled={disabled}
        required={required}
        placeholder={placeholder}
        className={inputClasses}
        {...props}
      />
    </div>
  );
}

/**
 * Textarea Component
 * For multi-line text input
 */
export function Textarea({
  variant = 'default',
  size = 'md',
  disabled = false,
  fullWidth = true,
  placeholder,
  value,
  onChange,
  onFocus,
  onBlur,
  rows = 4,
  name,
  id,
  required = false,
  className = '',
  ...props
}) {
  const baseClasses = 'input-base resize-none';
  
  const variantClasses = {
    default: '',
    error: 'input-error',
    success: 'input-success',
    ghost: 'bg-transparent border-transparent hover:bg-gray-800/50'
  };
  
  const sizeClasses = {
    sm: 'px-3 py-2 text-xs',
    md: '',
    lg: 'px-4 py-3 text-base'
  };
  
  const widthClass = fullWidth ? 'w-full' : '';
  
  const textareaClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    sizeClasses[size] || sizeClasses.md,
    widthClass,
    className
  ].filter(Boolean).join(' ');
  
  return (
    <textarea
      name={name}
      id={id}
      value={value}
      onChange={onChange}
      onFocus={onFocus}
      onBlur={onBlur}
      disabled={disabled}
      required={required}
      placeholder={placeholder}
      rows={rows}
      className={textareaClasses}
      {...props}
    />
  );
}

/**
 * Select Component
 * For dropdown selection
 */
export function Select({
  variant = 'default',
  size = 'md',
  disabled = false,
  fullWidth = true,
  placeholder,
  value,
  onChange,
  onFocus,
  onBlur,
  name,
  id,
  required = false,
  children,
  className = '',
  ...props
}) {
  const baseClasses = 'input-base cursor-pointer';
  
  const variantClasses = {
    default: '',
    error: 'input-error',
    success: 'input-success',
    ghost: 'bg-transparent border-transparent hover:bg-gray-800/50'
  };
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: '',
    lg: 'px-4 py-3 text-base'
  };
  
  const widthClass = fullWidth ? 'w-full' : '';
  
  const selectClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    sizeClasses[size] || sizeClasses.md,
    widthClass,
    className
  ].filter(Boolean).join(' ');
  
  return (
    <select
      name={name}
      id={id}
      value={value}
      onChange={onChange}
      onFocus={onFocus}
      onBlur={onBlur}
      disabled={disabled}
      required={required}
      className={selectClasses}
      {...props}
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {children}
    </select>
  );
}

/**
 * Checkbox Component
 * For boolean input
 */
export function Checkbox({
  checked,
  onChange,
  disabled = false,
  label,
  id,
  name,
  required = false,
  className = '',
  ...props
}) {
  const checkboxId = id || name;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        type="checkbox"
        id={checkboxId}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
        {...props}
      />
      {label && (
        <label 
          htmlFor={checkboxId}
          className="text-sm text-gray-300 cursor-pointer"
        >
          {label}
        </label>
      )}
    </div>
  );
}

/**
 * Radio Button Component
 * For single selection from multiple options
 */
export function Radio({
  checked,
  onChange,
  disabled = false,
  label,
  id,
  name,
  value,
  required = false,
  className = '',
  ...props
}) {
  const radioId = id || `${name}-${value}`;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        type="radio"
        id={radioId}
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 focus:ring-blue-500 focus:ring-2"
        {...props}
      />
      {label && (
        <label 
          htmlFor={radioId}
          className="text-sm text-gray-300 cursor-pointer"
        >
          {label}
        </label>
      )}
    </div>
  );
}

