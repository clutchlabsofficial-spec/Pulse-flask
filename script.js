/* ==========================================================================
   PULSE Flask — interactions
   --------------------------------------------------------------------------
   No libraries, no build step. Independent modules:
     0. Config
     1. Mobile nav toggle
     2. Scroll reveal
     3. Feature disclosures
     4. Waitlist form
     5. Reading progress bar
     6. Scrollspy
     7. Pricing count-up
     8. Sticky-header offset for anchor links

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
     #  locally without sending anywhere, exactly as it does today.    #
     ###################################################################  */
  var WAITLIST_ENDPOINT = "";

  /* Shown as a fallback if the endpoint is unreachable, so a signup is never
     simply lost. Replace with your real address when you have one. */
  var FALLBACK_EMAIL = "";


  /* Single source of truth for the motion preference. */
  var prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;


  /* 1. MOBILE NAV =========================================================
     The nav is CSS-hidden below 720px and revealed by the .is-open class. */

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

    /* Tapping a link should close the menu and let the jump happen. */
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setNav(false);
    });

    /* Escape closes the menu and returns focus to the button. */
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        setNav(false);
        navToggle.focus();
      }
    });
  }


  /* 2. SCROLL REVEAL ======================================================
     Elements marked .reveal in the HTML fade and rise into place once.

     Note the ordering: .reveal-init (which sets opacity 0) is only applied
     by JS, and only when we know an observer is available to remove it.
     That way a browser without IntersectionObserver — or with JS disabled —
     never ends up with permanently invisible content. */

  var revealables = document.querySelectorAll(".reveal");

  if (revealables.length && "IntersectionObserver" in window && !prefersReducedMotion) {
    revealables.forEach(function (el) {
      el.classList.add("reveal-init");
    });

    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);   // reveal once, then stop
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 }
    );

    revealables.forEach(function (el) {
      revealObserver.observe(el);
    });
  }


  /* 3. FEATURE DISCLOSURES ================================================
     Each feature card's header is a <button> controlling a panel. Using a
     real button means Enter, Space, focus and screen-reader semantics all
     work without us implementing them.

     The panel animates via CSS (grid-template-rows 0fr → 1fr); all this does
     is toggle `hidden` and a class, and keep the URL hash in sync so a single
     feature can be linked to directly. */

  var featureButtons = [].slice.call(document.querySelectorAll(".feature-btn"));

  if (featureButtons.length) {
    var closePanel = function (btn) {
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;

      btn.setAttribute("aria-expanded", "false");
      panel.classList.remove("is-open");

      /* Wait for the collapse to finish before hiding, or the transition is
         cut off. Skipped entirely when motion is reduced. */
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

      /* One at a time — six open panels is a wall of text. */
      featureButtons.forEach(function (other) {
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

      /* Bring the card into view under the sticky header. */
      btn.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
        block: "nearest",
      });

      /* Make the open feature linkable without adding a history entry per
         click — replaceState keeps the back button meaning "previous page". */
      if (btn.id) history.replaceState(null, "", "#" + btn.id);
    };

    featureButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.getAttribute("aria-expanded") === "true") {
          closePanel(btn);
          history.replaceState(null, "", location.pathname + location.search);
        } else {
          openPanel(btn);
        }
      });
    });

    /* Deep link: /#btn-uvc opens that panel on load. */
    if (location.hash.length > 1) {
      var deepLinked = document.getElementById(location.hash.slice(1));
      if (deepLinked && deepLinked.classList.contains("feature-btn")) {
        openPanel(deepLinked);
      }
    }
  }


  /* 4. WAITLIST FORM ======================================================
     Validation lives here (the form is novalidate) so the messaging and
     error styling are identical across browsers.

     With WAITLIST_ENDPOINT set, the address is POSTed to a Google Apps Script
     that saves it to a Sheet and emails you. With it empty, the form behaves
     exactly as it did before: validate, confirm, send nothing. */

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

    /* Never claim success we can't back up. If the request failed, say so and
       give people another way through. */
    var failed = function () {
      setBusy(false);
      var fallback = FALLBACK_EMAIL
        ? ' Please email <a href="mailto:' + FALLBACK_EMAIL + '">' + FALLBACK_EMAIL + "</a> instead."
        : "";
      showError("Something went wrong on our end — your spot wasn't saved." + fallback);
    };

    /* Clear the error as soon as the person starts correcting it. */
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
      if (!WAITLIST_ENDPOINT) {
        succeed();
        return;
      }

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


  /* 5. READING PROGRESS ===================================================
     Width is set inside rAF so a fast scroll doesn't queue a layout write per
     event. Skipped entirely under reduced motion (the CSS hides the bar too). */

  var progressBar = document.getElementById("progress-bar");

  if (progressBar && !prefersReducedMotion) {
    var ticking = false;

    var updateProgress = function () {
      var doc = document.documentElement;
      var scrollable = doc.scrollHeight - window.innerHeight;
      var pct = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
      progressBar.style.width = Math.min(100, Math.max(0, pct)) + "%";
      ticking = false;
    };

    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateProgress);
    }, { passive: true });

    /* Panels opening and closing change the page height. */
    window.addEventListener("resize", updateProgress, { passive: true });
    updateProgress();
  }


  /* 6. SCROLLSPY ==========================================================
     Marks the nav link for whichever section is currently in view. */

  var spySections = document.querySelectorAll("main section[id]");

  if (spySections.length && "IntersectionObserver" in window) {
    var linkFor = {};
    document.querySelectorAll('.site-nav a[href^="#"]').forEach(function (link) {
      linkFor[link.getAttribute("href").slice(1)] = link;
    });

    var visible = {};

    var spyObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          visible[entry.target.id] = entry.isIntersecting;
        });

        /* Topmost visible section wins, so scrolling up and down agree. */
        var current = null;
        for (var i = 0; i < spySections.length; i++) {
          if (visible[spySections[i].id]) { current = spySections[i].id; break; }
        }

        Object.keys(linkFor).forEach(function (id) {
          if (id === current) linkFor[id].setAttribute("aria-current", "true");
          else linkFor[id].removeAttribute("aria-current");
        });
      },
      /* Only count a section once it's properly in the upper viewport. */
      { rootMargin: "-20% 0px -60% 0px" }
    );

    spySections.forEach(function (section) {
      spyObserver.observe(section);
    });
  }


  /* 7. PRICING COUNT-UP ===================================================
     Animates the three ledger figures once, when they scroll into view.

     The final text is read straight out of the DOM and restored verbatim at
     the end, so the animation can never show a number that disagrees with
     what's actually written in the HTML. Only the digits are animated; any
     surrounding characters (~, $, %, en dashes) are preserved. */

  var ledgerCells = document.querySelectorAll(".ledger .num");

  if (ledgerCells.length && "IntersectionObserver" in window && !prefersReducedMotion) {
    var countUp = function (cell) {
      var finalText = cell.textContent;
      var numbers = finalText.match(/\d+/g);
      if (!numbers) return;

      var targets = numbers.map(Number);
      var DURATION = 900;
      var start = null;

      var frame = function (now) {
        if (start === null) start = now;
        var t = Math.min(1, (now - start) / DURATION);
        /* easeOutCubic — fast then settling, rather than a linear ramp. */
        var eased = 1 - Math.pow(1 - t, 3);

        var i = 0;
        cell.textContent = finalText.replace(/\d+/g, function () {
          return String(Math.round(targets[i++] * eased));
        });

        if (t < 1) window.requestAnimationFrame(frame);
        else cell.textContent = finalText;   // exact original, always
      };

      window.requestAnimationFrame(frame);
    };

    var ledgerObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          countUp(entry.target);
          ledgerObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.6 }
    );

    ledgerCells.forEach(function (cell) {
      ledgerObserver.observe(cell);
    });
  }


  /* 8. ANCHOR SCROLL ======================================================
     CSS `scroll-padding-top` already keeps targets clear of the sticky
     header for native jumps. This adds the smooth easing, and skips it
     entirely when reduced motion is requested. */

  if (!prefersReducedMotion) {
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function (event) {
        var id = link.getAttribute("href");
        if (id === "#" || id.length < 2) return;

        var target = document.querySelector(id);
        if (!target) return;

        event.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });

        /* Keep the URL and keyboard focus in sync with where we scrolled. */
        history.pushState(null, "", id);
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      });
    });
  }
})();
