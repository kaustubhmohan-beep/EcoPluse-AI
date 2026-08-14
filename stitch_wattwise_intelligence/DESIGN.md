---
name: Eco-Tech Kinetic Desktop
colors:
  surface: '#111412'
  surface-dim: '#111412'
  surface-bright: '#373a38'
  surface-container-lowest: '#0c0f0d'
  surface-container-low: '#191c1b'
  surface-container: '#1d201e'
  surface-container-high: '#272b29'
  surface-container-highest: '#323533'
  on-surface: '#e1e3e0'
  on-surface-variant: '#bfc9c3'
  inverse-surface: '#e1e3e0'
  inverse-on-surface: '#2e312f'
  outline: '#89938d'
  outline-variant: '#404944'
  surface-tint: '#95d3ba'
  primary: '#95d3ba'
  on-primary: '#003829'
  primary-container: '#064e3b'
  on-primary-container: '#80bea6'
  inverse-primary: '#2b6954'
  secondary: '#ddfcff'
  on-secondary: '#00363a'
  secondary-container: '#00f1fe'
  on-secondary-container: '#006a70'
  tertiary: '#adc6ff'
  on-tertiary: '#042e67'
  tertiary-container: '#21437c'
  on-tertiary-container: '#93b1f2'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b0f0d6'
  primary-fixed-dim: '#95d3ba'
  on-primary-fixed: '#002117'
  on-primary-fixed-variant: '#0b513d'
  secondary-fixed: '#74f5ff'
  secondary-fixed-dim: '#00dbe7'
  on-secondary-fixed: '#002022'
  on-secondary-fixed-variant: '#004f54'
  tertiary-fixed: '#d8e2ff'
  tertiary-fixed-dim: '#adc6ff'
  on-tertiary-fixed: '#001a41'
  on-tertiary-fixed-variant: '#24467f'
  background: '#111412'
  on-background: '#e1e3e0'
  surface-variant: '#323533'
  midnight-forest-start: '#020B09'
  midnight-forest-end: '#061A16'
  electric-cyan: '#00F2FF'
  kinetic-green: '#10B981'
  glass-stroke: rgba(255, 255, 255, 0.1)
typography:
  display-xl:
    fontFamily: Montserrat
    fontSize: 72px
    fontWeight: '700'
    lineHeight: 80px
    letterSpacing: -0.04em
  display-lg:
    fontFamily: Montserrat
    fontSize: 56px
    fontWeight: '700'
    lineHeight: 64px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Montserrat
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Montserrat
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  body-xl:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.1em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  grid-margin: 64px
  grid-gutter: 24px
  bento-gap: 16px
  section-padding: 120px
---

## Brand & Style

The design system evolves into a high-performance industrial SaaS aesthetic, blending environmental consciousness with the raw power of energy management. The brand personality is **Commanding, Technical, and Kinetic**. It signals authority in the energy sector by moving away from soft environmentalism toward a sophisticated "Midnight" tech aesthetic.

The visual style is a fusion of **Corporate Modern** and **Glassmorphism**, optimized for large-scale data density. It utilizes deep gradients to represent the "Midnight Forest"—the intersection of nature and heavy industry—while using "Electric Cyan" to symbolize the high-tech energy pulse.

**Key Visual Pillars:**
- **Kinetic Energy:** Use of luminous gradients and glowing accents to suggest active power flow and real-time monitoring.
- **Bento Efficiency:** Modular, structured grids that organize complex data into digestible, high-contrast visual "cells."
- **Industrial Sophistication:** A dark-mode first approach that reduces eye strain for long-duration monitoring while maintaining a premium, "mission control" feel.

## Colors

The desktop experience shifts to a **Dark Mode** default to emphasize the "Electric Cyan" accents and "Midnight Forest" depth.

- **Primary (Midnight Forest - #064E3B):** The core brand color, used for deep backgrounds and primary containers.
- **Secondary (Electric Cyan - #00F2FF):** The "High-Tech" accent. Used for interactive states, data highlights, and the "pulse" of the UI.
- **Tertiary (Deep Tech Blue - #002C65):** Used for shadow depth and differentiating technical data layers.
- **Neutral (Carbon - #0D1C2F):** Used for surface areas and secondary backgrounds to maintain contrast against the deep forest tones.

**Gradients:**
- **Midnight Gradient:** A linear transition from `#020B09` to `#064E3B` at 135 degrees, used for the main background.
- **Energy Pulse:** A radial gradient of `Electric Cyan` at 15% opacity used behind key data points to simulate a glow.

## Typography

The typography scale is expanded for desktop immersion. We introduce **JetBrains Mono** for technical labels and data points to reinforce the industrial, code-like precision of the energy sector.

- **Large-Scale Display:** For hero sections, use `display-xl` with tight tracking to create an architectural block of text.
- **Technical Readability:** All data values and status labels must use `JetBrains Mono` to differentiate dynamic machine data from UI instructional text.
- **Hierarchy:** Use `Electric Cyan` sparingly for `label-lg` items to highlight system statuses.

## Layout & Spacing

The layout is built on a **12-column fixed grid** for desktop (max-width 1440px) that centers on the screen.

- **Hero Sections:** Utilize the full viewport height (`100vh`) with content centered or split 60/40 to accommodate large-scale industrial imagery or data visualizations.
- **Bento Grid:** For feature sections and dashboards, use a "Bento-style" layout. This relies on fixed-ratio cells (e.g., 1x1, 2x1, 2x2) with a tight `bento-gap` of 16px to create a dense, functional cockpit feel.
- **Desktop Rhythm:** Vertical spacing is aggressive. Use `section-padding` (120px) to separate high-level concepts, allowing the deep gradients to breathe.

## Elevation & Depth

Hierarchy is established through **Luminous Layering** rather than traditional shadows.

1.  **The Void (Base):** The `Midnight Forest` gradient serves as the furthest Z-index.
2.  **Bento Cells (Surface):** Each grid cell is a `surface-container` with a subtle 1px border (`glass-stroke`). 
3.  **Kinetic Glow (Focus):** Active cards or hovered elements lose their border and gain an outer `Electric Cyan` glow (0px 0px 20px rgba(0, 242, 255, 0.15)) and a backdrop blur of 20px.
4.  **Floating Nav:** The top navigation bar is fully glassmorphic with a `40px` backdrop blur and a 1px bottom border to separate it from the scrolling content.

## Shapes

The shape language uses **Rounded** geometry to maintain a modern SaaS feel, but with strict alignment to the grid to keep it feeling "Industrial."

- **Bento Cells:** Use `rounded-xl` (24px) for all primary feature containers.
- **Interactive Elements:** Buttons and input fields use `rounded-lg` (16px) for a tactile, ergonomic feel.
- **Data Pills:** Status indicators remain fully pill-shaped (rounded-full) to provide a visual break from the rectangular grid.

## Components

### Hero Section
- **Visuals:** Large-scale 3D renders or technical schematics in the background.
- **Typography:** `display-xl` headers with a gradient fill (Electric Cyan to White).

### Bento Feature Grid
- **Composition:** A mix of small (label + icon), medium (description + illustration), and large (interactive chart) cells.
- **Styling:** Semi-transparent containers with `glass-stroke` borders.

### Buttons
- **Primary:** Electric Cyan fill with Midnight Forest text. Sharp, high-contrast, no shadow—only a glow on hover.
- **Ghost Technical:** White border, mono font, used for secondary data actions.

### Input Fields
- Dark backgrounds (`#020B09`) with a subtle `Electric Cyan` bottom border. On focus, the border expands to 2px with a soft glow.

### Data Widgets
- Small sparklines in the corner of bento cells.
- Large numeric values in `JetBrains Mono` for maximum technical clarity.