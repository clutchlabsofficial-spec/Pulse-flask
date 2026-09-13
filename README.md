# PULSE Flask — product website

Single-page site for **PULSE Flask**, a smart water bottle for athletes and
hikers, in three sizes. Built for the CoCreate Pitch 2026 (London) application.

Static HTML, CSS and JavaScript. No framework, no build step, no dependencies.

## Preview

Open `index.html` in a browser — that's it.

To serve it (so fonts and relative paths behave as they would in production):

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Files

| File | What's in it |
|---|---|
| `index.html` | All twelve sections, commented section by section |
| `styles.css` | Palette tokens, layout, responsive rules |
| `script.js` | Nav, showcase mechanic, FAQ, waitlist form, scroll effects |
| `apps-script/Code.gs` | Waitlist backend — paste into Google Apps Script |

## Design

Black, white and red. Structure is carried entirely by black, dark-grey, white
and light-grey. **Red is a signal colour only** — the primary CTA, hover
states, the LED ring, and active-heating references. It is never a large
background block. Light mode is the default; the hero, founder and footer
sections invert to black.

Type is Inter: 800 for headlines at `-0.02em` tracking, 400 for body.

### Palette

```css
--white: #f8f9fa   --light-grey: #dee2e6   --grey:  #6c757d
--dark-grey: #343a40   --black: #212529    --pulse-red: #d62828
```

Three extra text tokens exist because several of those pairings fall under
WCAG AA (4.5:1) **as text**, even though they're fine as structure:

| Token | For | Replaces |
|---|---|---|
| `--grey-text: #5d656c` | secondary text on light | `--grey` at 4.45 on white |
| `--grey-text-dark: #adb5bd` | secondary text on dark | `--grey` at 3.29 on black |
| `--pulse-red-text: #e88787` | red **lettering** on dark | `--pulse-red` at 3.08 on black |

`--pulse-red` itself is unchanged and still the fill for every button and the
LED ring — white on it measures 4.75. The split is between red-as-fill and
red-as-text, not a change to the brand colour.

Every text node on the rendered page was measured against its real composited
background; nothing ships under its AA threshold.

## The three-layer scroll mechanic

Section 3 moves three layers at different rates:

1. **Background** — grain panel translated at 0.3× scroll speed
2. **Bottle** — `position: sticky` stage, pinned while the copy scrolls past.
   The active step is mirrored onto the stage: the caption swaps and the LED
   ring lights red on the steps where it would genuinely be glowing.
3. **Text** — five feature blocks at normal speed, revealed on entry

Two implementation notes worth keeping:

- `.showcase` uses `overflow: clip`, **not** `overflow: hidden`. `hidden` makes
  it a scroll container, which silently breaks `position: sticky` on the stage
  inside it.
- The active step is chosen by **nearest-to-a-line**, not by an
  IntersectionObserver band. The steps are tall with large gaps, so two can sit
  in any band at once — "first visible wins" then lags a step behind and never
  reaches the last one.

Reveals use native `animation-timeline: view()` where supported, with an
IntersectionObserver fallback gated behind `CSS.supports()` so exactly one
mechanism ever runs. Everything is disabled under `prefers-reduced-motion`,
where all content is visible and the stage still pins.

## The three sizes

| | Compact | Standard · launch | Pro |
|---|---|---|---|
| Capacity | 500 ml | 800 ml | 1 L |
| Heating chamber | 430 ml | 770 ml | 855 ml |
| Battery | 30 Wh | 54 Wh | 60 Wh |
| Heater | 120 W | 216 W | 240 W |
| To 165 °F | ~15 min | ~15 min | ~15 min |
| Price | $120 | $165 | $190 |
| Expected range | $95–130 | $140–195 | $155–220 |
| Landed cost | ~$82 | ~$117 | ~$128 |
| Gross margin | 32% | 29% | 33% |

All three share the same electronics module, heater design, rocker latch, UV-C
system and twist-off base; only chamber size, battery and heater wattage scale.

Pricing figures live in **one table** in the `#pricing` section and the variant
cards in `#variants`. Margin is `(retail − landed) / retail`.

## Collecting signups (Google Sheet + Gmail)

Out of the box the form validates and confirms but **sends nothing** — the
address stays in the browser. Do this once and signups land in a Google Sheet
and in your Gmail. Free, unlimited, and the data is yours.

1. **Make the Sheet.** Create a new Google Sheet.
2. **Add the script.** Extensions → Apps Script. Delete the sample code, paste
   in all of [`apps-script/Code.gs`](apps-script/Code.gs). Save.
3. **Deploy.** Deploy → New deployment → ⚙ → Web app.
   Execute as **Me**; Who has access **Anyone**. "Anyone" is required — the
   site calls this from visitors' browsers, and they aren't logged into your
   Google account. The endpoint only ever *accepts* an email; it never returns
   your list. Authorise when prompted (it sends mail as you), clicking through
   the "unverified app" warning for your own private script.
4. **Connect it.** Copy the Web app URL (ends in `/exec`) into `script.js`:

   ```js
   var WAITLIST_ENDPOINT = "https://script.google.com/macros/s/AKfy..../exec";
   ```

   Set `FALLBACK_EMAIL` to a real address while you're there — if the endpoint
   is ever unreachable the form shows it rather than pretending it worked.
5. **Check it.** Open the `/exec` URL in a browser; you should see
   `{"ok":true,"status":"PULSE Flask waitlist endpoint is live"}`.

Notes:
- **Your email address is never in the repo.** The script mails
  `Session.getEffectiveUser()` — whoever deployed it.
- Re-deploy after editing (Deploy → Manage deployments → ✎ → Version: New).
- Duplicates are ignored; the honeypot is checked server-side too.

## Swapping in real photography

Every image slot is a `<div class="ph ...">` labelled with the shot it's
waiting for. Replace the whole div with an image, keeping the aspect-ratio
class so the layout doesn't shift:

```html
<img class="ph-hero" src="images/hero.jpg" alt="PULSE Flask, three-quarter view, LED ring lit">
```

Write a real `alt` description rather than copying the placeholder label. The
showcase stage (`.stage-frame`) takes a photo per step — the captions come from
`data-caption` on each `.showcase-step`.

## Specs still to fill in

Search for `[SPEC:` — these are deliberately blank rather than guessed, because
this page goes in front of judges:

- UV-C wavelength and independent lab results
- Rocker latch tested open/close cycle count
- IP water rating
- Battery life in days of typical use

## Other things to edit

- **Social links** — footer `<ul class="social">`, currently `href="#"`.
- **Colours** — the `:root` block at the top of `styles.css`. Re-check contrast
  if you lighten any text token.

## Notes

- Mobile-first; verified at 320, 375, 768 and 1280px with no horizontal scroll.
- Nothing on the site is presented as available to buy.
- The category comparison names no competitor and invents no competitor spec.
