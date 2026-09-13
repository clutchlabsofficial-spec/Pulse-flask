/* ==========================================================================
   PULSE Flask — interactions
   --------------------------------------------------------------------------
   No libraries, no build step. Independent modules:
     0. Config
     1. Mobile nav toggle
     2. Scroll reveal   (fallback only — CSS handles this where supported)
     3. Showcase        (parallax layer + active-step state)
     4. FAQ disclosures
     5. Waitlist form
     6. Reading progress bar
     7. Scrollspy
     8. Anchor scroll

   Everything here is progressive enhancement: if this file fails to load,
   the page is still fully readable and every section is visible.
   ========================================================================== */

(function () {
  "use strict";

  /* 0. CONFIG =============================================================
     ###################################################################
     #  PASTE YOUR GOOGLE APPS SCRIPT URL BETWEEN THE QUOTES BELOW.    #
     #  It looks like:                                                 #
     #    https://script.google.com/macros/s/AKfy..../exec             #
     #  Setup walkthrough is in README.md → "Collecting signups".      #
     #                                                                 #
     #  Leave it empty and the form still works — it just confirms     #
     #  locally without sending anywhere.                              #
     ###################################################################  */
  var WAITLIST_ENDPOINT = "";

  /* Shown as a fallback if the endpoint is unreachable, so a signup is never
     simply lost. Replace with your real address when you have one. */
  var FALLBACK_EMAIL = "";


  /* Single source of truth for the motion preference. */
  var prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* Does the browser do scroll-driven animations natively? If so the CSS
     @supports block already handles every reveal on the compositor, and the
     JS fallback below must NOT also run — two mechanisms fighting over the
     same elements is how content ends up stuck at opacity 0. Firefox is the
     current holdout (still behind a flag), so the fallback stays. */
  var hasScrollTimeline =
    typeof CSS !== "undefined" &&
    CSS.supports &&
    CSS.supports("animation-timeline: view()");


  /* 1. MOBILE NAV ========================================================= */

  var navToggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");

  if (navToggle && nav) {
    var setNav = function (open) {
      nav.classList.toggle("is-open", open);
      navToggle.setAttribute("aria-expanded", String(open));
    };

    navToggle.addEventListener("click", function () {
      setNav(navToggle.getAttribute("aria-expanded") !== "true");
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setNav(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        setNav(false);
        navToggle.focus();
      }
    });
  }


  /* 2. SCROLL REVEAL (fallback) ===========================================
     .reveal-init sets opacity 0, so it is applied only when we know both
     that the CSS path is unavailable AND that an observer exists to remove
     it. A browser with neither never ends up with invisible content. */

  var revealables = document.querySelectorAll(".reveal");

  if (revealables.length && "IntersectionObserver" in window &&
      !prefersReducedMotion && !hasScrollTimeline) {
    revealables.forEach(function (el) { el.classList.add("reveal-init"); });

    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 }
    );

    revealables.forEach(function (el) { revealObserver.observe(el); });
  }


  /* 3. SHOWCASE ===========================================================
     Two independent pieces of the three-layer mechanic:

       a) the background layer, translated at 0.3x scroll speed
       b) the active-step state, mirrored from the scrolling copy onto the
          pinned stage (caption swap + LED ring)

     The sticky pinning itself is pure CSS — nothing here is required for the
     stage to pin, only for it to react. */

  var showcase = document.getElementById("showcase");
  var showcaseBg = showcase && showcase.querySelector(".showcase-bg");
  var stage = document.getElementById("stage");
  var steps = [].slice.call(document.querySelectorAll(".showcase-step"));

  /* Both pieces share one rAF-throttled scroll handler: a single read of
     layout per frame, then at most two writes. Parallax is skipped under
     reduced motion, but the active-step tracking still runs — the mechanic
     has to work without motion, not just look different. */
  if (showcase && stage && steps.length) {
    var stageCaption = document.getElementById("stage-caption");
    var stageLed = document.getElementById("stage-led");
    var stageNum = document.getElementById("stage-num");
    var showcaseTicking = false;

    var setActiveStep = function (step) {
      var index = Number(step.getAttribute("data-step")) || 0;
      if (stage.getAttribute("data-active") === String(index)) return;

      stage.setAttribute("data-active", String(index));
      steps.forEach(function (other) {
        other.classList.toggle("is-current", other === step);
      });

      /* textContent, not innerHTML — data-* attributes must never be able to
         inject markup. data-caption carries an escaped <br>, which becomes a
         newline here and renders via `white-space: pre-line` in the CSS. */
      if (stageCaption) {
        stageCaption.textContent =
          (step.getAttribute("data-caption") || "").replace(/<br\s*\/?>/gi, "\n");
      }
      if (stageNum) stageNum.textContent = String(index + 1).padStart(2, "0");
      if (stageLed) {
        stageLed.classList.toggle("is-lit", step.getAttribute("data-led") === "on");
      }
    };

    var updateShowcase = function () {
      showcaseTicking = false;

      var box = showcase.getBoundingClientRect();
      /* Skip all work when the section is nowhere near the viewport. */
      if (box.bottom < 0 || box.top > window.innerHeight) return;

      /* --- a) Parallax: background travels at 0.3x the content's rate --- */
      if (showcaseBg && !prefersReducedMotion) {
        var travelled = window.innerHeight - box.top;
        showcaseBg.style.transform =
          "translate3d(0," + (travelled * -0.3 * 0.12).toFixed(2) + "px,0)";
      }

      /* --- b) Active step ---------------------------------------------
         Pick the step whose centre is nearest a fixed line 40% down the
         viewport — roughly level with the pinned stage.

         An IntersectionObserver band was the obvious approach and is wrong
         here: these steps are tall with large gaps, so two of them can sit
         in any band at once, and "first visible wins" then lags a step
         behind and never reaches the last one. Nearest-to-a-line has no
         such ambiguity and behaves identically scrolling up or down. */
      var line = window.innerHeight * 0.4;
      var best = null;
      var bestDistance = Infinity;

      for (var i = 0; i < steps.length; i++) {
        var r = steps[i].getBoundingClientRect();
        var distance = Math.abs((r.top + r.height / 2) - line);
        if (distance < bestDistance) { bestDistance = distance; best = steps[i]; }
      }
      if (best) setActiveStep(best);
    };

    window.addEventListener("scroll", function () {
      if (showcaseTicking) return;
      showcaseTicking = true;
      window.requestAnimationFrame(updateShowcase);
    }, { passive: true });

    window.addEventListener("resize", updateShowcase, { passive: true });
    updateShowcase();
  }


  /* 4. FAQ DISCLOSURES ====================================================
     A real <button> controlling a panel, so Enter, Space, focus and
     screen-reader semantics all work without us implementing them. The
     panel animates via CSS (grid-template-rows 0fr → 1fr). */

  var faqButtons = [].slice.call(document.querySelectorAll(".faq-btn"));

  if (faqButtons.length) {
    var closePanel = function (btn) {
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;

      btn.setAttribute("aria-expanded", "false");
      panel.classList.remove("is-open");

      /* Wait for the collapse before hiding, or the transition is cut off. */
      if (prefersReducedMotion) {
        panel.hidden = true;
      } else {
        window.setTimeout(function () {
          if (!panel.classList.contains("is-open")) panel.hidden = true;
        }, 320);
      }
    };

    var openPanel = function (btn) {
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;

      /* One at a time — the whole list open at once is a wall of text. */
      faqButtons.forEach(function (other) {
        if (other !== btn && other.getAttribute("aria-expanded") === "true") {
          closePanel(other);
        }
      });

      panel.hidden = false;
      /* Force a reflow so the browser registers hidden:false before the class
         change, otherwise there's no start state to animate from. */
      void panel.offsetHeight;

      btn.setAttribute("aria-expanded", "true");
      panel.classList.add("is-open");
    };

    faqButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.getAttribute("aria-expanded") === "true") closePanel(btn);
        else openPanel(btn);
      });
    });
  }


  /* 5. WAITLIST FORM ======================================================
     With WAITLIST_ENDPOINT set, the address is POSTed to a Google Apps Script
     that saves it to a Sheet and emails the owner. With it empty, the form
     validates and confirms locally and sends nothing. */

  var form = document.getElementById("waitlist-form");
  var done = document.getElementById("waitlist-done");

  if (form && done) {
    var emailInput = document.getElementById("email");
    var errorEl = document.getElementById("email-error");
    var honeypot = document.getElementById("company");
    var submitBtn = form.querySelector('button[type="submit"]');
    var submitLabel = submitBtn ? submitBtn.textContent : "";

    /* Deliberately permissive: something@something.tld. Over-strict email
       regexes reject more valid addresses than they catch invalid ones. */
    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    var showError = function (html) {
      errorEl.innerHTML = html;
      emailInput.classList.add("has-error");
      emailInput.setAttribute("aria-invalid", "true");
    };

    var clearError = function () {
      errorEl.textContent = "";
      emailInput.classList.remove("has-error");
      emailInput.removeAttribute("aria-invalid");
    };

    var setBusy = function (busy) {
      if (!submitBtn) return;
      submitBtn.disabled = busy;
      submitBtn.textContent = busy ? "Joining…" : submitLabel;
    };

    var succeed = function () {
      form.hidden = true;
      done.hidden = false;
    };

    /* Never claim a success we can't back up. */
    var failed = function () {
      setBusy(false);
      var fallback = FALLBACK_EMAIL
        ? ' Please email <a href="mailto:' + FALLBACK_EMAIL + '">' + FALLBACK_EMAIL + "</a> instead."
        : "";
      showError("Something went wrong on our end — your spot wasn't saved." + fallback);
    };

    emailInput.addEventListener("input", function () {
      if (errorEl.textContent) clearError();
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      /* A filled honeypot means a bot. Pretend nothing happened. */
      if (honeypot && honeypot.value !== "") return;

      var value = emailInput.value.trim();

      if (value === "") {
        showError("Please enter your email address.");
        emailInput.focus();
        return;
      }
      if (!EMAIL_RE.test(value)) {
        showError("That doesn't look like a valid email address.");
        emailInput.focus();
        return;
      }

      clearError();

      /* No endpoint configured yet — confirm locally, send nothing. */
      if (!WAITLIST_ENDPOINT) { succeed(); return; }

      setBusy(true);

      /* text/plain is deliberate: it keeps this a "simple" CORS request so the
         browser skips the preflight, which an Apps Script web app can't
         answer (it 302s to googleusercontent). The body is still JSON and the
         script parses it out of e.postData.contents. */
      fetch(WAITLIST_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify({
          email: value,
          company: honeypot ? honeypot.value : "",
          source: "website",
        }),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          /* "already_subscribed" is still a success from the visitor's side —
             they're on the list, which is all they asked for. */
          if (data && data.ok) succeed();
          else throw new Error((data && data.error) || "unknown");
        })
        .catch(failed);
    });
  }


  /* 6. READING PROGRESS =================================================== */

  var progressBar = document.getElementById("progress-bar");

  if (progressBar && !prefersReducedMotion) {
    var progressTicking = false;

    var updateProgress = function () {
      progressTicking = false;
      var doc = document.documentElement;
      var scrollable = doc.scrollHeight - window.innerHeight;
      var pct = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
      progressBar.style.width = Math.min(100, Math.max(0, pct)) + "%";
    };

    window.addEventListener("scroll", function () {
      if (progressTicking) return;
      progressTicking = true;
      window.requestAnimationFrame(updateProgress);
    }, { passive: true });

    window.addEventListener("resize", updateProgress, { passive: true });
    updateProgress();
  }


  /* 7. SCROLLSPY ========================================================== */

  var spySections = document.querySelectorAll("main section[id]");

  if (spySections.length && "IntersectionObserver" in window) {
    var linkFor = {};
    document.querySelectorAll('.site-nav a[href^="#"]').forEach(function (link) {
      linkFor[link.getAttribute("href").slice(1)] = link;
    });

    var sectionVisible = {};

    var spyObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          sectionVisible[entry.target.id] = entry.isIntersecting;
        });

        var current = null;
        for (var i = 0; i < spySections.length; i++) {
          if (sectionVisible[spySections[i].id]) { current = spySections[i].id; break; }
        }

        Object.keys(linkFor).forEach(function (id) {
          if (id === current) linkFor[id].setAttribute("aria-current", "true");
          else linkFor[id].removeAttribute("aria-current");
        });
      },
      { rootMargin: "-20% 0px -60% 0px" }
    );

    spySections.forEach(function (section) { spyObserver.observe(section); });
  }


  /* 8. ANCHOR SCROLL ======================================================
     CSS scroll-padding-top already keeps targets clear of the sticky header
     for native jumps. This adds the smooth easing, skipped under reduced
     motion. */

  if (!prefersReducedMotion) {
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function (event) {
        var id = link.getAttribute("href");
        if (id === "#" || id.length < 2) return;

        var target = document.querySelector(id);
        if (!target) return;

        event.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });

        history.pushState(null, "", id);
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      });
    });
  }
})();
