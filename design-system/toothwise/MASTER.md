# ToothWise Master Design System

## Direction
Quiet editorial healthcare. The interface should feel like a well-organized private clinic: calm, precise, trustworthy, and warm without looking playful or generic.

## Brand source
Use `docs/brand-guidelines.md` and `assets/design-tokens.json` as the source of truth.

## Style decisions
- No gradients on the logo.
- No emoji as UI icons.
- Solid plum primary actions for accessible contrast.
- Rose is a secondary/highlight color, not the default text-on-light CTA background.
- White surfaces on a warm off-white background.
- Borders + restrained shadows instead of heavy neumorphism. The UI/UX search suggested neumorphism for healthcare but explicitly marked its accessibility risk as high, so ToothWise uses the safer material/editorial interpretation.
- 12–20px component radii, 28px for hero shells.
- 16px body base; compact metadata can go to 12–14px but not below 12px for meaningful content.
- Lucide icons only.

## Layout
- Mobile-first; no horizontal page scroll.
- Main content max width around 1240px.
- Desktop dashboard uses a collapsible sidebar; mobile uses a full-width drawer with scrim.
- Public landing uses generous vertical rhythm and clear section anchors.
- Clinical tables must be inside an overflow-safe region on small screens.

## Motion
- UI controls: 140–280ms, custom ease-out, transform/opacity only.
- Triggered popovers scale from 0.96, not 0, and originate near the trigger.
- Hover transforms are gated to fine pointers.
- Landing/rare reveal motion may use a longer opacity/translate reveal, but always honors reduced motion.
- No `transition: all`, no `ease-in`, no layout-property animation.

## Privacy/navigation
- Staff and patient sessions are mutually exclusive in memory and local storage.
- Logout performs a real replacement navigation.
- 401 handling clears only the affected session.
- Sensitive routes use replace navigation when crossing the auth boundary.
- Staff patient-detail screens provide explicit `Back to Patients` / `Back to Patient` controls instead of relying on browser history.
