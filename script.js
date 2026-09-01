/* ==========================================================================
   PULSE Flask — interactions
   --------------------------------------------------------------------------
   No libraries, no build step. Four small independent modules:
     1. Mobile nav toggle
     2. Scroll reveal
     3. Waitlist form
     4. Sticky-header offset for anchor links

   Everything here is progressive enhancement: if this file fails to load,
   the page is still fully readable and every section is visible.
   ========================================================================== */

(function () {
  "use strict";

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

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);   // reveal once, then stop watching
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 }
    );

    revealables.forEach(function (el) {
      observer.observe(el);
    });
  }


  /* 3. WAITLIST FORM ======================================================
     Front-end only. Nothing is transmitted; the address stays in the browser.
     Validation lives here (the form is novalidate) so the messaging and
     error styling are identical across browsers. */

  var form = document.getElementById("waitlist-form");
  var done = document.getElementById("waitlist-done");

  if (form && done) {
    var emailInput = document.getElementById("email");
    var errorEl = document.getElementById("email-error");
    var honeypot = document.getElementById("company");

    /* Deliberately permissive: something@something.tld. Over-strict email
       regexes reject more valid addresses than they catch invalid ones. */
    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    var showError = function (message) {
      errorEl.textContent = message;
      emailInput.classList.add("has-error");
      emailInput.setAttribute("aria-invalid", "true");
    };

    var clearError = function () {
      errorEl.textContent = "";
      emailInput.classList.remove("has-error");
      emailInput.removeAttribute("aria-invalid");
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

      // TODO: POST `value` to your email provider here (Mailchimp, Buttondown,
      // ConvertKit, a Google Form, or your own endpoint). Until then the
      // address never leaves this page.

      /* Swap the form for the confirmation. The confirmation is aria-live,
         so screen readers announce it without moving focus. */
      form.hidden = true;
      done.hidden = false;
    });
  }


  /* 4. ANCHOR SCROLL ======================================================
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
