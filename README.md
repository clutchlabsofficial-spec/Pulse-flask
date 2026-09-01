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
| `script.js` | Nav, scroll reveal, feature panels, waitlist form, scroll effects |
| `apps-script/Code.gs` | Waitlist backend — paste into Google Apps Script |

## Feature panels

Each of the six feature cards opens to a longer explanation, a detail photo
slot and a spec list. They're plain `<button>` + panel disclosures, so keyboard
and screen-reader support come from the markup rather than from JavaScript.
One opens at a time, and the open one is linkable — `index.html#btn-uvc` loads
with the UV-C panel already open.

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

## Collecting signups (Google Sheet + Gmail)

Out of the box the form validates and confirms but **sends nothing** — the
address stays in the browser. Do this once and signups start landing in a
Google Sheet and in your Gmail. It's free, unlimited, and the data is yours.

**1. Make the Sheet**

Create a new Google Sheet. Name it whatever you like.

**2. Add the script**

In that Sheet: **Extensions → Apps Script**. Delete the sample code, then
paste in the entire contents of [`apps-script/Code.gs`](apps-script/Code.gs).
Save.

**3. Deploy it**

**Deploy → New deployment → ⚙ → Web app**, then:

| Setting | Value |
|---|---|
| Execute as | **Me** |
| Who has access | **Anyone** |

"Anyone" is required — the website calls this from visitors' browsers, and
they aren't logged into your Google account. The endpoint only ever *accepts*
an email address; it never returns your list.

Click **Deploy**. Google asks you to authorise it (it's sending mail as you) —
you'll see an "unverified app" warning because it's your own private script:
**Advanced → Go to … (unsafe)** → Allow.

**4. Connect the site**

Copy the **Web app URL** (it ends in `/exec`) and paste it into `script.js`:

```js
var WAITLIST_ENDPOINT = "https://script.google.com/macros/s/AKfy..../exec";
```

While you're there, set `FALLBACK_EMAIL` to a real address. If the endpoint is
ever unreachable, the form shows it rather than pretending the signup worked.

**5. Check it**

Paste the `/exec` URL straight into a browser — you should see
`{"ok":true,"status":"PULSE Flask waitlist endpoint is live"}`. Then submit
the form on the site and watch the row appear in the Sheet.

### Notes

- **Your email address is never in the repo.** The script mails
  `Session.getEffectiveUser()`, which is whoever deployed it — you.
- Re-deploy after editing the script (**Deploy → Manage deployments → ✎ →
  Version: New**), or the old code keeps running.
- Duplicate addresses are ignored, so a double-tap doesn't make two rows.
- The honeypot field is checked on the server too, not just in the browser.
- Set `SEND_NOTIFICATIONS = false` in `Code.gs` if you want rows without email.

## Specs still to fill in

The feature panels contain `[SPEC: …]` placeholders wherever a real measured
number belongs. **These are deliberately blank rather than guessed** — this
page is going in front of judges, so nothing should claim a figure that hasn't
been tested. Search the project for `[SPEC:` to find them all:

| Feature | Needs |
|---|---|
| Tap-to-glow LED ring | Seconds lit before fade; temperature range |
| Rotating bezel | Number of detent positions |
| Magnetic charging | Charge time; battery life; IP rating |
| Rocker latch spout | Tested open/close cycle count |
| UV-C purification | Cycle time; wavelength; lab results |
| Boost Mode | °C rise; run time; battery cost per boost |

## Notes

- Mobile-first; verified at 320, 375, 768 and 1280px with no horizontal scroll.
- Respects `prefers-reduced-motion` — all animation is disabled and nothing
  is hidden.
- Fonts load from Google Fonts with a full system-font fallback, so the page
  still renders correctly offline.
- Nothing on the site is presented as available to buy.
