# Toothwise Design Reference

## Dark Mode Direction

Reference: Dark dashboard with warm accents (orange/red/yellow on near-black).

### Palette

| Token | Light | Dark | Role |
|-------|-------|------|------|
| `--tw-bg` | `#F5EFEC` | `#0F1117` | Page background |
| `--tw-surface` | `#FFFFFF` | `#181B23` | Cards, panels |
| `--tw-text` | `#3A2430` | `#F0F0F3` | Primary text |
| `--tw-muted` | `#8C7078` | `#6B7280` | Secondary text |
| `--tw-border` | `#E6DCE0` | `#262A33` | Dividers, borders |
| `--tw-teal` | `#C4847E` | `#BA7976` | Primary accent (rose) |
| `--tw-navy` | `#5C3A4A` | `#D4A0A8` | Secondary accent |

### Semantic Tokens (Dark)

| Token | Value | Use |
|-------|-------|-----|
| `--tw-danger` | `#F87171` | Errors, destructive actions |
| `--tw-danger-bg` | `rgba(248,113,113,.12)` | Danger surfaces |
| `--tw-warning` | `#FBBF24` | Warnings, pending |
| `--tw-warning-bg` | `rgba(251,191,36,.12)` | Warning surfaces |
| `--tw-success` | `#4ADE80` | Success, active, low risk |
| `--tw-success-bg` | `rgba(74,222,128,.12)` | Success surfaces |
| `--tw-indigo` | `#A5B4FC` | Info, badges |
| `--tw-indigo-bg` | `rgba(165,180,252,.12)` | Info surfaces |

### Design Principles (from reference)

1. **Backgrounds:** Near-black (`#0F1117`), not warm plum. Cards slightly lighter (`#181B23`).
2. **Text:** High-contrast white (`#F0F0F3`) for primary, neutral gray (`#6B7280`) for secondary.
3. **Accents:** Warm tones (rose/amber) for interactive elements, not everywhere.
4. **Borders:** Subtle (`#262A33`), barely visible, just enough to separate surfaces.
5. **Shadows:** Deep, dark (`rgba(0,0,0,.4)`), not colored.
6. **Charts:** Bright accent colors (orange, red, yellow) pop against dark backgrounds.
7. **Cards:** No heavy borders, rely on background contrast and subtle shadows.
8. **Typography:** Clean sans-serif, generous tracking, clear weight hierarchy.

### Anti-Patterns (avoid)

- Warm plum/brown dark backgrounds (`#1A1216`, `#251C20`) — use cool neutral grays
- Low-contrast muted text on dark backgrounds
- Colored borders on cards — use background contrast instead
- Heavy box shadows with colored tints
