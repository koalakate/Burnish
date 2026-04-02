# Burnish Design Direction

## Design Principles

### 1. Speed-first for Jake (Marketing Manager)
Jake uploads decks under time pressure. Every interaction should feel instant.

- Zero forms: drag-and-drop is the primary input. No multi-step wizards.
- Minimal chrome: content (slides, issues, scores) takes 90%+ of viewport.
- Immediate feedback: upload progress, checking status, and results stream in without page reloads.
- One-click fix: "Fix All" is the hero action. Individual corrections are available but not required.
- Auto-navigate: after upload, the UI moves Jake to results without asking.

### 2. Depth-available for Priya (Brand Manager)
Priya needs to inspect, edit, and approve. The detail is there when she wants it.

- Expandable panels: issue lists collapse to summaries, expand to full details.
- Side-by-side comparison: original vs. corrected slides, with changed elements highlighted.
- Edit-in-place: Priya can tweak any AI suggestion before accepting.
- Export DQS: the score badge on the download confirmation is screenshot-friendly for client reports.

### 3. Dark-first, professional
Burnish is a tool for professionals. The dark theme reduces eye strain during long sessions
and makes slide previews pop against the background.

## Color Palette

All colors use oklch for perceptual uniformity.

### Brand Accent (Cyan)
A 10-step cyan scale from near-white to near-black. `brand-400` is the primary interactive color.

| Token         | Value                      | Usage                        |
|---------------|----------------------------|------------------------------|
| `brand-50`    | oklch(0.97 0.04 200)       | Subtle tinted backgrounds    |
| `brand-100`   | oklch(0.93 0.08 200)       | Hover tints                  |
| `brand-200`   | oklch(0.86 0.12 200)       | Active/selected backgrounds  |
| `brand-300`   | oklch(0.78 0.16 200)       | Secondary actions            |
| `brand-400`   | oklch(0.70 0.19 200)       | Primary buttons, links, CTA  |
| `brand-500`   | oklch(0.62 0.20 200)       | Pressed states               |
| `brand-600`   | oklch(0.52 0.18 200)       | Dark accents                 |
| `brand-700`   | oklch(0.43 0.15 200)       | Sidebar active indicator     |
| `brand-800`   | oklch(0.35 0.12 200)       | Dark text on light bg        |
| `brand-900`   | oklch(0.27 0.08 200)       | Deepest accent               |

### Severity
| Token             | Value                        | Usage                     |
|-------------------|------------------------------|---------------------------|
| `severity-error`  | oklch(0.704 0.191 22.216)    | Errors, red bounding boxes|
| `severity-warning`| oklch(0.795 0.184 86.047)    | Warnings, yellow overlays |
| `severity-info`   | oklch(0.70 0.19 200)         | Info, blue/cyan overlays  |

### DQS Score Badge
| Token          | Value                     | Condition   |
|----------------|---------------------------|-------------|
| `dqs-good`     | oklch(0.72 0.19 142)      | Score >= 80 |
| `dqs-moderate` | oklch(0.795 0.184 86)     | Score 60-79 |
| `dqs-poor`     | oklch(0.704 0.191 22)     | Score < 60  |

### Surfaces (Dark Mode)
| Token            | Value                 | Usage                |
|------------------|-----------------------|----------------------|
| `background`     | oklch(0.145 0 0)      | Page background      |
| `card`           | oklch(0.205 0 0)      | Cards, panels        |
| `secondary`      | oklch(0.269 0 0)      | Hover states, badges |
| `border`         | oklch(1 0 0 / 10%)    | Subtle dividers      |

## Typography

- **Font family:** DM Sans (body/headings), DM Mono (code, technical values)
- **Base size:** 14px (0.875rem) — compact for data-dense UI
- **Scale:** 12 / 13 / 14 / 16 / 18 / 20 / 24 / 32px

| Token    | Size     | Usage                                    |
|----------|----------|------------------------------------------|
| `xs`     | 12px     | Captions, timestamps, badge labels       |
| `sm`     | 13px     | Secondary text, metadata                 |
| `base`   | 14px     | Body text, issue descriptions            |
| `md`     | 16px     | Emphasized body, nav items               |
| `lg`     | 18px     | Section headers                          |
| `xl`     | 20px     | Page sub-headers                         |
| `2xl`    | 24px     | Page titles                              |
| `3xl`    | 32px     | Hero metrics (DQS score)                 |

- **Weights:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- DQS numbers use DM Sans Bold at 32px.
- Issue descriptions use DM Sans Regular at 14px.
- Code values (hex colors, font names) use DM Mono at 13px.

## Spacing System

4px base unit. Standard Tailwind spacing scale (0.5 = 2px, 1 = 4px, 2 = 8px, etc.).

Key layout values:
- Sidebar width: 256px (collapsible to 56px)
- Page padding: 24px
- Card padding: 16px
- Gap between cards: 16px
- Slide preview aspect ratio: 16:9

## Component Patterns

### Cards
- Background: `card` surface
- Border: 1px solid `border`
- Border radius: `md` (8px)
- Hover: border transitions to `brand-400` at 30% opacity

### Buttons
- Primary: `brand-400` background, inverse text
- Secondary: `secondary` background, foreground text
- Ghost: transparent, foreground text, hover shows `secondary`
- Destructive: `severity-error` background

### Badges / Chips
- Small (xs font), pill-shaped (full radius)
- Severity badges: colored background at 15% opacity, text in full severity color
- DQS badge: circular, large number, background color from DQS scale

### Issue Overlays (on slide preview)
- Bounding boxes: 2px stroke in severity color, 10% fill
- Click-to-select: selected box gets 3px stroke + subtle glow
- Correction highlight: `brand-400` glow on corrected elements

### Transitions
- All interactive elements: 150ms ease-out (fast)
- Panel expand/collapse: 200ms ease-out (normal)
- Page transitions: 300ms ease-out (slow)

## File Structure

```
src/lib/design-tokens.ts    — JS/TS access to tokens (for canvas, charts)
src/app/globals.css          — CSS custom properties + Tailwind v4 theme
```

Tailwind classes reference the CSS custom properties via `@theme inline` in globals.css.
For canvas rendering (Konva.js) and programmatic color logic, import from `design-tokens.ts`.
