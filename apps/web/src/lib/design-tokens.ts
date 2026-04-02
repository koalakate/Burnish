/**
 * Burnish Design Tokens
 *
 * Programmatic access to the design system values.
 * CSS custom properties in globals.css are the source of truth for Tailwind;
 * this file mirrors them for use in JS/TS (canvas rendering, charts, inline styles).
 */

// ---------------------------------------------------------------------------
// Color palette
// ---------------------------------------------------------------------------

/** Core brand colors — dark-first, professional aesthetic */
export const colors = {
  // Brand accent — cyan family
  brand: {
    50: "oklch(0.97 0.04 200)",
    100: "oklch(0.93 0.08 200)",
    200: "oklch(0.86 0.12 200)",
    300: "oklch(0.78 0.16 200)",
    400: "oklch(0.70 0.19 200)",
    500: "oklch(0.62 0.20 200)",
    600: "oklch(0.52 0.18 200)",
    700: "oklch(0.43 0.15 200)",
    800: "oklch(0.35 0.12 200)",
    900: "oklch(0.27 0.08 200)",
  },

  // Semantic — severity / status
  severity: {
    error: "oklch(0.704 0.191 22.216)",
    warning: "oklch(0.795 0.184 86.047)",
    info: "oklch(0.70 0.19 200)",
  },

  // DQS score badge
  dqs: {
    good: "oklch(0.72 0.19 142)",      // green — score ≥80
    moderate: "oklch(0.795 0.184 86)",  // yellow — score 60-79
    poor: "oklch(0.704 0.191 22)",      // red — score <60
  },

  // Surface palette (dark mode)
  surface: {
    base: "oklch(0.145 0 0)",         // --background
    raised: "oklch(0.205 0 0)",       // --card
    overlay: "oklch(0.269 0 0)",      // --secondary / --muted
    border: "oklch(1 0 0 / 10%)",     // --border
    borderHover: "oklch(1 0 0 / 15%)",
  },

  // Text palette (dark mode)
  text: {
    primary: "oklch(0.985 0 0)",      // --foreground
    secondary: "oklch(0.708 0 0)",    // --muted-foreground
    tertiary: "oklch(0.556 0 0)",
    inverse: "oklch(0.145 0 0)",
  },
} as const;

// ---------------------------------------------------------------------------
// Typography
// ---------------------------------------------------------------------------

export const fontFamily = {
  sans: "var(--font-sans)",   // DM Sans
  mono: "var(--font-mono)",   // DM Mono
} as const;

/** Type scale — rem-based, used for consistent hierarchy */
export const fontSize = {
  xs: "0.75rem",     // 12px — captions, badges
  sm: "0.8125rem",   // 13px — secondary text, metadata
  base: "0.875rem",  // 14px — body text (compact UI)
  md: "1rem",        // 16px — emphasized body
  lg: "1.125rem",    // 18px — section headers
  xl: "1.25rem",     // 20px — page sub-headers
  "2xl": "1.5rem",   // 24px — page titles
  "3xl": "2rem",     // 32px — hero / DQS number
} as const;

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

export const lineHeight = {
  tight: "1.2",
  normal: "1.5",
  relaxed: "1.7",
} as const;

// ---------------------------------------------------------------------------
// Spacing
// ---------------------------------------------------------------------------

/** 4px base unit spacing scale */
export const spacing = {
  0: "0",
  0.5: "0.125rem",  // 2px
  1: "0.25rem",      // 4px
  1.5: "0.375rem",   // 6px
  2: "0.5rem",       // 8px
  3: "0.75rem",      // 12px
  4: "1rem",         // 16px
  5: "1.25rem",      // 20px
  6: "1.5rem",       // 24px
  8: "2rem",         // 32px
  10: "2.5rem",      // 40px
  12: "3rem",        // 48px
  16: "4rem",        // 64px
  20: "5rem",        // 80px
} as const;

// ---------------------------------------------------------------------------
// Radii
// ---------------------------------------------------------------------------

export const radius = {
  sm: "0.375rem",    // 6px — small chips, badges
  md: "0.5rem",      // 8px — cards, inputs
  lg: "0.625rem",    // 10px — panels
  xl: "0.875rem",    // 14px — modals, dropzones
  full: "9999px",    // pills, avatars
} as const;

// ---------------------------------------------------------------------------
// Shadows (subtle, dark-UI friendly)
// ---------------------------------------------------------------------------

export const shadow = {
  sm: "0 1px 2px oklch(0 0 0 / 20%)",
  md: "0 2px 8px oklch(0 0 0 / 25%)",
  lg: "0 4px 16px oklch(0 0 0 / 30%)",
  glow: "0 0 12px oklch(0.70 0.19 200 / 25%)",  // brand accent glow
} as const;

// ---------------------------------------------------------------------------
// Transitions
// ---------------------------------------------------------------------------

export const transition = {
  fast: "150ms cubic-bezier(0.4, 0, 0.2, 1)",
  normal: "200ms cubic-bezier(0.4, 0, 0.2, 1)",
  slow: "300ms cubic-bezier(0.4, 0, 0.2, 1)",
} as const;

// ---------------------------------------------------------------------------
// Z-index scale
// ---------------------------------------------------------------------------

export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  overlay: 30,
  modal: 40,
  toast: 50,
} as const;

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

export const layout = {
  sidebarWidth: "16rem",        // 256px
  sidebarCollapsed: "3.5rem",   // 56px
  headerHeight: "3.5rem",       // 56px
  maxContentWidth: "80rem",     // 1280px
  slideAspectRatio: 16 / 9,
} as const;

// ---------------------------------------------------------------------------
// DQS helpers
// ---------------------------------------------------------------------------

export function dqsColor(score: number): string {
  if (score >= 80) return colors.dqs.good;
  if (score >= 60) return colors.dqs.moderate;
  return colors.dqs.poor;
}

export function severityColor(severity: "error" | "warning" | "info"): string {
  return colors.severity[severity];
}
