---
name: frontend-design
description: Standalone frontend design skill. Reuse scan → design-system check → component scaffold → responsive patterns → a11y audit. Technology-agnostic with stack adaptation notes.
user-invocable: true
disable-model-invocation: false
---

# /frontend-design

## When to run

Before building any UI component, page, or layout. Also useful mid-task when design
quality is in question. Skip only for trivial style tweaks (single property change).

---

## Phase 1 — Reuse Scan

Before creating anything new, look for what already exists.

1. List all existing UI components in the project (search `components/`, `ui/`, `atoms/`,
   `molecules/`, `src/shared/`, or the project's declared component directories).
2. For each candidate component, check:
   - **Exact match**: does it already do what's needed?
   - **Extension candidate**: could it accept new props without rewriting?
   - **Composition candidate**: can two existing components compose into the needed result?
3. Report: `REUSE: found [N] candidates → extending <name> / composing <a> + <b> / creating new`
4. Only proceed to scaffold if no reuse or extension is viable.

---

## Phase 2 — Design System Check

Verify the project has a design system foundation. If not, establish minimums before
building components.

### Token audit

Check for (or create) these token categories:

| Category | What to define | Example |
|----------|---------------|---------|
| **Color** | Primary, secondary, accent, neutrals, semantic (success/warning/error) | `--color-primary: #…` |
| **Typography** | Font families, scale (xs→4xl), line heights, weights | `--text-lg: 1.125rem` |
| **Spacing** | Base unit + scale (4px or 8px grid) | `--space-4: 1rem` |
| **Radius** | Consistent border-radius values | `--radius-md: 6px` |
| **Shadow** | Elevation levels | `--shadow-sm: 0 1px 2px …` |
| **Breakpoints** | Named screen sizes | `sm: 640px, md: 768px …` |

If tokens don't exist: propose a minimal token file before scaffolding components.
If tokens exist: reference them — never use hardcoded hex, px, or magic numbers.

### Stack adaptation

| Stack | Token mechanism |
|-------|----------------|
| React / Next.js | CSS custom properties, Tailwind config, or CSS-in-JS theme |
| React Native | StyleSheet constants / design-tokens.ts file |
| Vue / Nuxt | CSS custom properties or Pinia design store |
| Svelte | CSS custom properties or `$lib/tokens.ts` |
| Generic | CSS custom properties in `:root {}` |

---

## Phase 3 — Component Scaffold

### Structure rules

Every component must follow the **separation of concerns** split:

```
ComponentName.tsx          ← presentational shell (markup + props only)
useComponentName.ts        ← all logic: state, effects, API calls, navigation
componentName.types.ts     ← prop types, event types
componentName.constants.ts ← magic values, variant maps, config
```

Generate all four files even if some start nearly empty — it prevents future logic leakage.

### Presentational shell checklist

The shell must:
- [ ] Destructure all props at the top
- [ ] Call exactly **one** custom hook
- [ ] Contain no `useState`, `useEffect`, `useQuery`, data transforms, or API calls
- [ ] Be readable top-to-bottom: root → sections → atoms
- [ ] Stay under 60 lines (split if exceeded)

### Variant pattern

For components with multiple visual states (size, variant, state):

```typescript
const variantStyles = {
  primary: '…',
  secondary: '…',
  ghost: '…',
} as const;

type Variant = keyof typeof variantStyles;
```

Never use ad-hoc ternaries for variants — they don't scale.

---

## Phase 4 — Responsive Patterns

Apply these patterns by default; adapt to project's breakpoint system.

### Layout approach

1. **Mobile-first**: base styles = mobile, progressively enhance for larger screens.
2. **Fluid before breakpoints**: prefer `clamp()`, `min()`, `max()` over snap breakpoints
   for spacing and type when the range is continuous.
3. **Content-driven breakpoints**: break when the content breaks, not at arbitrary device sizes.

### Common patterns

| Pattern | When | Implementation |
|---------|------|----------------|
| Stack → Row | Navigation, button groups | `flex-direction: column` → `row` at breakpoint |
| Single → Multi-column | Lists, cards | CSS Grid with `auto-fill / auto-fit` |
| Full-width → Contained | Page sections | `max-width` + `margin: auto` |
| Hidden → Visible | Sidebar, filters | `display: none` → `flex/block` |
| Truncate → Expand | Long text | Line-clamp → full text |

### Touch targets (mobile)

- Minimum interactive area: **44×44px** (iOS HIG / WCAG 2.5.5)
- Adjacent targets: minimum **8px gap**
- Never make the visual element smaller than the touch target — use padding

---

## Phase 5 — Accessibility Audit

Run after every component is scaffolded. Every item is mandatory.

### Semantic HTML

- [ ] Headings follow hierarchy (h1 → h2 → h3, no skips)
- [ ] Interactive elements use `<button>` or `<a>` — never `<div onClick>`
- [ ] Form inputs have `<label>` (explicit or `aria-label`)
- [ ] Lists use `<ul>/<ol>` + `<li>`, not `<div>` stacks
- [ ] Landmark regions present: `<header>`, `<main>`, `<nav>`, `<footer>`

### ARIA

- [ ] `aria-label` or `aria-labelledby` on every interactive element without visible text
- [ ] `role` set only when native semantics are overridden
- [ ] Dynamic content updates use `aria-live` (polite) or `aria-atomic`
- [ ] Modal/dialog: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`

### Keyboard navigation

- [ ] All interactive elements reachable via Tab
- [ ] Focus order is logical (matches visual order)
- [ ] Focus visible (`:focus-visible` styled — never `outline: none` without replacement)
- [ ] Modals trap focus; restore focus on close
- [ ] Escape key closes modals/dropdowns

### Color & contrast

- [ ] Text on background: minimum **4.5:1** contrast (WCAG AA) — **7:1** for AAA
- [ ] UI components / graphical elements: minimum **3:1** contrast
- [ ] No information conveyed by color alone (add icon, label, or pattern)

### Motion

- [ ] Animations respect `prefers-reduced-motion` media query
- [ ] No content flashing more than 3 times per second

---

## Phase 6 — Post-scaffold checks

1. Run the **`audit-loop` skill** — it enforces size caps and architecture rules.
2. Check that every token reference is valid (no undefined CSS variables).
3. Verify the component renders correctly at: mobile (375px), tablet (768px), desktop (1280px).
4. Confirm the a11y checklist above is fully green.

---

## Output format

After completing all phases, emit:

```
FRONTEND DESIGN SUMMARY
────────────────────────────────────────────────
Reuse scan      : [extended <name> / created new / composed <a>+<b>]
Tokens          : [verified existing / created <token-file>]
Files created   : [list of scaffolded files]
Responsive      : [breakpoints applied]
A11y            : [N] checks — [all pass / N issues fixed]
Audit-loop      : [✅ READY / ⚠️ needs attention]
────────────────────────────────────────────────
```

---

## Don't

- Use hardcoded hex values, magic px numbers, or arbitrary opacity values.
- Put any logic (state, effects, fetching) in the presentational shell.
- Create a new component when an existing one can be extended or composed.
- Skip the a11y checklist because the design looks complete — visual ≠ accessible.
- Use `<div onClick>` for interactive elements.
