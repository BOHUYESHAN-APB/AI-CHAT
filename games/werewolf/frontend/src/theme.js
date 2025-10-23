/**
 * 狼人杀游戏统一UI主题配置
 * 现代化紫蓝渐变风格
 */

export const theme = {
  // 主色调
  colors: {
    primary: '#667eea',
    primaryDark: '#5568d3',
    secondary: '#764ba2',
    accent: '#f093fb',
    
    // 背景色
    bgPrimary: '#0f0f23',
    bgSecondary: '#1a1a2e',
    bgCard: 'rgba(255, 255, 255, 0.05)',
    bgCardHover: 'rgba(255, 255, 255, 0.08)',
    
    // 文字色
    textPrimary: '#ffffff',
    textSecondary: '#b8b8d1',
    textMuted: '#6b6b8c',
    
    // 状态色
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    
    // 角色色
    werewolf: '#ef4444',
    seer: '#3b82f6',
    witch: '#a855f7',
    hunter: '#f97316',
    guard: '#14b8a6',
    villager: '#6b7280',
    cupid: '#ec4899',
    idiot: '#facc15',
  },
  
  // 渐变
  gradients: {
    primary: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    secondary: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    dark: 'linear-gradient(135deg, #1a1a2e 0%, #0f0f23 100%)',
    success: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    card: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
  },
  
  // 阴影
  shadows: {
    sm: '0 2px 8px rgba(0, 0, 0, 0.1)',
    md: '0 4px 20px rgba(0, 0, 0, 0.15)',
    lg: '0 8px 32px rgba(0, 0, 0, 0.2)',
    xl: '0 12px 48px rgba(0, 0, 0, 0.25)',
    glow: '0 0 20px rgba(102, 126, 234, 0.5)',
    glowStrong: '0 0 30px rgba(102, 126, 234, 0.8)',
  },
  
  // 圆角
  borderRadius: {
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    full: '9999px',
  },
  
  // 间距
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    xxl: '48px',
  },
  
  // 字体
  fonts: {
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace',
  },
  
  // 字号
  fontSizes: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '24px',
    xxl: '32px',
    xxxl: '48px',
  },
  
  // 过渡动画
  transitions: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    normal: '250ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '350ms cubic-bezier(0.4, 0, 0.2, 1)',
  },
  
  // Z-index 层级
  zIndex: {
    base: 1,
    dropdown: 100,
    modal: 1000,
    toast: 2000,
    tooltip: 3000,
  },
};

// 通用样式辅助函数
export const getCardStyle = (hover = true) => ({
  background: theme.gradients.card,
  backdropFilter: 'blur(10px)',
  border: `1px solid rgba(255, 255, 255, 0.1)`,
  borderRadius: theme.borderRadius.lg,
  boxShadow: theme.shadows.md,
  transition: theme.transitions.normal,
  ...(hover && {
    ':hover': {
      background: theme.bgCardHover,
      boxShadow: theme.shadows.lg,
      transform: 'translateY(-2px)',
    },
  }),
});

export const getButtonStyle = (variant = 'primary') => {
  const variants = {
    primary: {
      background: theme.gradients.primary,
      color: theme.colors.textPrimary,
      border: 'none',
      ':hover': {
        boxShadow: theme.shadows.glow,
        transform: 'translateY(-1px)',
      },
    },
    secondary: {
      background: theme.bgCard,
      color: theme.colors.textPrimary,
      border: `1px solid ${theme.colors.primary}`,
      ':hover': {
        background: theme.colors.primary,
      },
    },
    ghost: {
      background: 'transparent',
      color: theme.colors.textSecondary,
      border: `1px solid rgba(255, 255, 255, 0.2)`,
      ':hover': {
        background: theme.bgCard,
        color: theme.colors.textPrimary,
      },
    },
  };
  
  return {
    ...variants[variant],
    padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
    borderRadius: theme.borderRadius.md,
    fontSize: theme.fontSizes.md,
    fontWeight: '500',
    cursor: 'pointer',
    transition: theme.transitions.normal,
    outline: 'none',
  };
};

export const getRoleColor = (role) => {
  return theme.colors[role] || theme.colors.villager;
};
