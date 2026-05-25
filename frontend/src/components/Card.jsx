/**
 * FILE: frontend/src/components/Card.jsx
 * ==================================================
 * Standardized Card Component
 * ==================================================
 * 
 * This component provides consistent card styling across the entire
 * application. It uses the design system tokens to ensure visual
 * consistency and prevent UI inconsistencies.
 * 
 * VARIANTS:
 *   - default: Standard card with hover effects
 *   - elevated: Card with more prominent shadow
 *   - interactive: Clickable card with enhanced hover effects
 *   - flat: Card without shadow for simple layouts
 * 
 * USAGE:
 *   <Card variant="elevated" className="custom-class">
 *     <Card.Header>Header Content</Card.Header>
 *     <Card.Body>Body Content</Card.Body>
 *     <Card.Footer>Footer Content</Card.Footer>
 *   </Card>
 */

import React from 'react';
import { motion } from 'framer-motion';
import { StatusCard } from "./Card";
import PropTypes from 'prop-types';
/**
 * Standardized Card Component
 * 
 * 
 * @param {Object} props
 * @param {string} props.variant - Card variant (default, elevated, interactive, flat)
 * @param {boolean} props.padding - Apply default padding
 * @param {React.ReactNode} props.children - Card content
 * @param {string} props.className - Additional CSS classes
 * @param {Function} props.onClick - Click handler for interactive cards
 */
Card.propTypes = {
  variant: PropTypes.oneOf([
    'default',
    'elevated',
    'interactive',
    'flat'
  ]),

  padding: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
  onClick: PropTypes.func
};
export default function Card({
  variant = 'default',
  padding = true,
  children,
  className = '',
  onClick,
  ...props
}) {
  // Build CSS classes using design system
  const baseClasses = 'card-base';
  
  // Variant classes
  const variantClasses = {
    default: '',
    elevated: 'card-elevated',
    interactive: 'card-interactive',
    flat: 'shadow-none'
  };
  
  // Padding class
  const paddingClass = padding ? '' : 'p-0';
  
  // Interactive class
  const interactiveClass = onClick ? 'cursor-pointer' : '';
  
  // Combine all classes
  const cardClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    paddingClass,
    interactiveClass,
    className
  ].filter(Boolean).join(' ');
  
  const handleClick = (e) => {
    if (onClick) {
      onClick(e);
    }
  };
  
  return (
    <motion.div
      className={cardClasses}
      onClick={handleClick}
      whileHover={{ y: -2, boxShadow: "0 10px 30px rgba(59, 130, 246, 0.15)" }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Card Header Component
 */
Card.Header = function CardHeader({ children, className = '', ...props }) {
  return (
    <div 
      className={`border-b border-gray-200/10 pb-4 mb-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

/**
 * Card Body Component
 */
Card.Body = function CardBody({ children, className = '', ...props }) {
  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
};

/**
 * Card Footer Component
 */
Card.Footer = function CardFooter({ children, className = '', ...props }) {
  return (
    <div 
      className={`border-t border-gray-200/10 pt-4 mt-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

/**
 * Simple Card Component
 * For basic card usage without header/footer structure
 */
export function SimpleCard({
  variant = 'default',
  children,
  className = '',
  ...props
}) {
  const baseClasses = 'card-base';
  
  const variantClasses = {
    default: '',
    elevated: 'card-elevated',
    interactive: 'card-interactive',
    flat: 'shadow-none'
  };
  
  const cardClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    className
  ].filter(Boolean).join(' ');
  
  return (
    <div className={cardClasses} {...props}>
      {children}
    </div>
  );
}

/**
 * Alert Card Component
 * For displaying alerts and notifications
 */
export function StatusCard({
  severity = 'info',
  children,
  className = '',
  ...props
}) {
  const baseClasses = 'alert-base';
  
  const severityClasses = {
    success: 'alert-success',
    warning: 'alert-warning',
    danger: 'alert-danger',
    info: 'alert-info',
    critical: 'alert-danger'
  };
  
  const alertClasses = [
    baseClasses,
    severityClasses[severity] || severityClasses.info,
    className
  ].filter(Boolean).join(' ');
  
  return (
    <div className={alertClasses} {...props}>
      {children}
    </div>
  );
}


