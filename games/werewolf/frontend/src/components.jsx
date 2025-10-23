import React from 'react';
import { theme, getCardStyle, getButtonStyle, getRoleColor } from './theme.js';

/**
 * 现代化卡片组件
 */
export const Card = ({ children, hover = true, style = {}, className = '', ...props }) => {
  return (
    <div
      style={{
        ...getCardStyle(hover),
        ...style,
      }}
      className={className}
      {...props}
    >
      {children}
    </div>
  );
};

/**
 * 现代化按钮组件
 */
export const Button = ({ children, variant = 'primary', style = {}, className = '', icon = null, ...props }) => {
  return (
    <button
      style={{
        ...getButtonStyle(variant),
        display: 'flex',
        alignItems: 'center',
        gap: theme.spacing.sm,
        ...style,
      }}
      className={className}
      {...props}
    >
      {icon && <span>{icon}</span>}
      {children}
    </button>
  );
};

/**
 * 页面容器组件
 */
export const PageContainer = ({ children, title = null, actions = null, style = {} }) => {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: theme.gradients.dark,
        padding: theme.spacing.xl,
        color: theme.colors.textPrimary,
        fontFamily: theme.fonts.sans,
        ...style,
      }}
    >
      {(title || actions) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: theme.spacing.xl,
          }}
        >
          {title && (
            <h1
              style={{
                fontSize: theme.fontSizes.xxxl,
                fontWeight: '700',
                background: theme.gradients.primary,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                margin: 0,
              }}
            >
              {title}
            </h1>
          )}
          {actions && <div style={{ display: 'flex', gap: theme.spacing.md }}>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

/**
 * 角色徽章组件
 */
export const RoleBadge = ({ role, size = 'md' }) => {
  const sizes = {
    sm: { fontSize: theme.fontSizes.xs, padding: `${theme.spacing.xs} ${theme.spacing.sm}` },
    md: { fontSize: theme.fontSizes.sm, padding: `${theme.spacing.sm} ${theme.spacing.md}` },
    lg: { fontSize: theme.fontSizes.md, padding: `${theme.spacing.md} ${theme.spacing.lg}` },
  };
  
  const roleNames = {
    werewolf: '狼人',
    seer: '预言家',
    witch: '女巫',
    hunter: '猎人',
    guard: '守卫',
    villager: '村民',
    cupid: '丘比特',
    idiot: '白痴',
    unknown: '未知',
  };
  
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...sizes[size],
        background: `linear-gradient(135deg, ${getRoleColor(role)}dd 0%, ${getRoleColor(role)} 100%)`,
        color: theme.colors.textPrimary,
        borderRadius: theme.borderRadius.sm,
        fontWeight: '600',
        boxShadow: theme.shadows.sm,
      }}
    >
      {roleNames[role] || role}
    </span>
  );
};

/**
 * 加载动画组件
 */
export const LoadingSpinner = ({ size = 40 }) => {
  return (
    <div
      style={{
        width: size,
        height: size,
        border: `4px solid ${theme.colors.bgCard}`,
        borderTop: `4px solid ${theme.colors.primary}`,
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }}
    >
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

/**
 * 状态标签组件
 */
export const StatusBadge = ({ status, children }) => {
  const statusStyles = {
    waiting: { bg: theme.colors.warning, text: '等待中' },
    running: { bg: theme.colors.success, text: '进行中' },
    ended: { bg: theme.colors.error, text: '已结束' },
    alive: { bg: theme.colors.success, text: '存活' },
    dead: { bg: theme.colors.error, text: '死亡' },
  };
  
  const config = statusStyles[status] || { bg: theme.colors.info, text: status };
  
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: `${theme.spacing.xs} ${theme.spacing.md}`,
        background: config.bg,
        color: theme.colors.textPrimary,
        borderRadius: theme.borderRadius.full,
        fontSize: theme.fontSizes.sm,
        fontWeight: '500',
      }}
    >
      {children || config.text}
    </span>
  );
};

/**
 * 输入框组件
 */
export const Input = ({ label = null, style = {}, containerStyle = {}, ...props }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm, ...containerStyle }}>
      {label && (
        <label
          style={{
            fontSize: theme.fontSizes.sm,
            color: theme.colors.textSecondary,
            fontWeight: '500',
          }}
        >
          {label}
        </label>
      )}
      <input
        style={{
          padding: `${theme.spacing.md} ${theme.spacing.lg}`,
          background: theme.bgCard,
          border: `1px solid rgba(255, 255, 255, 0.1)`,
          borderRadius: theme.borderRadius.md,
          color: theme.colors.textPrimary,
          fontSize: theme.fontSizes.md,
          outline: 'none',
          transition: theme.transitions.normal,
          ':focus': {
            border: `1px solid ${theme.colors.primary}`,
            boxShadow: theme.shadows.glow,
          },
          ...style,
        }}
        {...props}
      />
    </div>
  );
};

/**
 * 选择框组件
 */
export const Select = ({ label = null, options = [], style = {}, containerStyle = {}, ...props }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm, ...containerStyle }}>
      {label && (
        <label
          style={{
            fontSize: theme.fontSizes.sm,
            color: theme.colors.textSecondary,
            fontWeight: '500',
          }}
        >
          {label}
        </label>
      )}
      <select
        style={{
          padding: `${theme.spacing.md} ${theme.spacing.lg}`,
          background: theme.bgCard,
          border: `1px solid rgba(255, 255, 255, 0.1)`,
          borderRadius: theme.borderRadius.md,
          color: theme.colors.textPrimary,
          fontSize: theme.fontSizes.md,
          outline: 'none',
          cursor: 'pointer',
          transition: theme.transitions.normal,
          ...style,
        }}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} style={{ background: theme.bgSecondary }}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
};
