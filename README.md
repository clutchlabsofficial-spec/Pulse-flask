# PULSE Flask — product website

Single-page site for **PULSE Flask**, a smart water bottle for athletes and
hikers. Built for the CoCreate Pitch 2026 (London) application.

Static HTML, CSS and JavaScript. No framework, no build step, no dependencies.

## Preview

Open `index.html` in a browser — that's it.

If you'd rather serve it (so the fonts and relative paths behave exactly as
they would in production):

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Files

| File | What's in it |
|---|---|
| `index.html` | All nine sections, commented section by section |
| `styles.css` | Design tokens, layout, responsive rules |
| `script.js` | Nav toggle, scroll reveal, waitlist form |

## Swapping in real photography

Every image slot is a placeholder `<div class="ph ...">` with a label naming
the shot it's waiting for. To replace one, swap the whole div for an image:

```html
<!-- before -->
<div class="ph ph-hero" role="img" aria-label="Placeholder for the hero product photograph">
  <span class="ph-label">Product photo · hero<br>bottle, 3/4 view, LED ring lit</span>
</div>

<!-- after -->
<img class="ph-hero" src="images/hero.jpg" alt="PULSE Flask, three-quarter view, LED ring lit">
```

Keep the `ph-hero` / `ph-wide` / `ph-square` / `ph-portrait` class — it sets
the aspect ratio so the layout doesn't shift. Write a real `alt` description
rather than copying the placeholder label.

There are six placeholders: hero, feature detail, PULSE Point, founder
portrait, and the aspect-ratio helpers are reused between them.

## Things you'll want to edit

- **Pricing figures** — one table in the `#pricing` section. Landed cost,
  retail range and margin all live there and nowhere else.
- **Founder story** — the `<blockquote>` in the `#founder` section.
- **Social links** — the footer `<ul class="social">`; the `href="#"` values
  are placeholders.
- **Colours** — the entire palette is the `:root` block at the top of
  `styles.css`. Six colours reskin the site. The ink tones are set where they
  are because they clear WCAG AA contrast against every background they sit
  on; re-check contrast if you lighten them.

## The waitlist form

Front-end only. It validates the address and shows a confirmation, but
**nothing is transmitted anywhere** — the email stays in the browser and is
not stored. To make it real, find the `// TODO: POST` comment in `script.js`
and send `value` to your email provider (Mailchimp, Buttondown, ConvertKit,
a Google Form, or your own endpoint).

## Notes

- Mobile-first; verified at 320, 375, 768 and 1280px with no horizontal scroll.
- Respects `prefers-reduced-motion` — all animation is disabled and nothing
  is hidden.
- Fonts load from Google Fonts with a full system-font fallback, so the page
  still renders correctly offline.
- Nothing on the site is presented as available to buy.
