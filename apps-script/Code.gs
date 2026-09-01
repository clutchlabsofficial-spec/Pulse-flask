/**
 * PULSE Flask — waitlist backend
 * ---------------------------------------------------------------------------
 * Receives waitlist signups from the website, saves them to this spreadsheet,
 * and emails you when someone joins.
 *
 * SETUP (about 5 minutes) — full walkthrough is in the repo README:
 *   1. Create a Google Sheet.
 *   2. Extensions → Apps Script. Delete whatever is there, paste this file.
 *   3. Deploy → New deployment → type "Web app".
 *        Execute as:      Me
 *        Who has access:  Anyone            ← required, or the site gets a 401
 *   4. Authorise when prompted (it asks because the script sends mail as you).
 *   5. Copy the /exec URL and paste it into WAITLIST_ENDPOINT in script.js.
 *
 * Nothing here is secret — the URL is public by design. The only thing the
 * endpoint accepts is an email address, and it never returns the list.
 */

/** Tab to write to. Created automatically if it doesn't exist. */
var SHEET_NAME = 'Waitlist';

/** Set to false if you'd rather only collect rows and not get notified. */
var SEND_NOTIFICATIONS = true;

/** Same permissive rule the front end uses: something@something.tld */
var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;


/**
 * Handles a signup POSTed from the website.
 *
 * The site sends its body as text/plain on purpose: that keeps the request
 * "simple" so the browser skips the CORS preflight, which an Apps Script web
 * app cannot answer. The body is still JSON — we parse it ourselves here.
 */
function doPost(e) {
  try {
    var payload = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var email = String(payload.email || '').trim();

    // Honeypot: a real person never fills this in, so drop it silently.
    // Returning "ok" means bots get no signal about why they failed.
    if (payload.company) {
      return json({ ok: true, status: 'ignored' });
    }

    if (!EMAIL_RE.test(email)) {
      return json({ ok: false, error: 'invalid_email' });
    }

    var sheet = getSheet_();

    // Don't create a second row if someone submits twice.
    if (isDuplicate_(sheet, email)) {
      return json({ ok: true, status: 'already_subscribed' });
    }

    sheet.appendRow([
      new Date(),
      email,
      String(payload.source || 'website'),
    ]);

    if (SEND_NOTIFICATIONS) {
      notify_(email, sheet.getLastRow() - 1);
    }

    return json({ ok: true, status: 'subscribed' });

  } catch (err) {
    // Log for the Apps Script execution view, but never leak internals to the
    // browser — the site only needs to know it failed so it can say so.
    console.error(err);
    return json({ ok: false, error: 'server_error' });
  }
}


/**
 * Visiting the /exec URL in a browser hits this. It exists purely so you can
 * confirm the deployment is live without having to submit the real form.
 */
function doGet() {
  return json({ ok: true, status: 'PULSE Flask waitlist endpoint is live' });
}


/* -------------------------------------------------------------------------
   Helpers
   ------------------------------------------------------------------------- */

/** Returns the waitlist tab, creating it with headers on first run. */
function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['Joined', 'Email', 'Source']);
    sheet.getRange('A1:C1').setFontWeight('bold');
    sheet.setFrozenRows(1);
  }

  return sheet;
}


/** Case-insensitive check against column B, skipping the header row. */
function isDuplicate_(sheet, email) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;

  var existing = sheet.getRange(2, 2, lastRow - 1, 1).getValues();
  var needle = email.toLowerCase();

  for (var i = 0; i < existing.length; i++) {
    if (String(existing[i][0]).trim().toLowerCase() === needle) return true;
  }
  return false;
}


/**
 * Emails the owner of this script. Session.getEffectiveUser() resolves to
 * whoever deployed it, so there is no address to hardcode or keep in sync —
 * and none is ever committed to the repository.
 */
function notify_(email, total) {
  var to = Session.getEffectiveUser().getEmail();
  if (!to) return;

  MailApp.sendEmail({
    to: to,
    subject: 'PULSE Flask — new waitlist signup (' + total + ' total)',
    body: [
      email + ' just joined the PULSE Flask waitlist.',
      '',
      'That makes ' + total + ' on the list.',
      '',
      SpreadsheetApp.getActiveSpreadsheet().getUrl(),
    ].join('\n'),
  });
}


/** Apps Script's way of returning a JSON response. */
function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
