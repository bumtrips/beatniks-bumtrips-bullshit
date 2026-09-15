// 6. Theme cycling — random theme picks, two triggers:
//    (a) auto-rotate timer (1-2.5 min between rotations)
//    (b) scroll activity (600px cumulative within a 30s cooldown)
//    Both fire the acid-trip transition. Either trigger resets
//    the other clock so we never get two swaps back-to-back.
(function themes() {
  var THEMES = ['cyber', 'zine', 'radio', 'desert', 'temple', 'brutalist'];
  var TRIP_MS = 720;
  var AUTO_MIN_MS = 30000;          // 30s minimum between auto-rotations
  var AUTO_RAND_MS = 30000;         // up to +30s of randomness
  var FIRST_AUTO_DELAY_MS = 5000;   // first auto-rotation 5s after page load
  var SCROLL_THRESHOLD_PX = 300;    // cumulative scroll distance to fire
  var SCROLL_COOLDOWN_MS = 15000;   // 15s between scroll-triggered swaps

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var idx = 0;
  var autoTimer = null;
  var root = document.documentElement;

  function pickRandomNext() {
    // Avoid landing on the current theme (would be a no-op trip).
    if (THEMES.length <= 1) return 0;
    var next;
    do { next = Math.floor(Math.random() * THEMES.length); }
    while (next === idx);
    return next;
  }

  // Lazy-load the Google Fonts URL that covers a theme's typography.
  // Cyber is already loaded in <head>; the dedupe map prevents duplicates.
  var fontLoadUrls = {};
  function ensureThemeFonts(theme) {
    if (theme === 'cyber') return; // cyber faces already load eagerly in <head>
    var url;
    if (theme === 'zine') {
      url = 'https://fonts.googleapis.com/css2?family=Special+Elite&family=Crimson+Pro:wght@400&display=swap';
    } else if (theme === 'radio') {
      url = 'https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap';
    } else if (theme === 'desert') {
      url = 'https://fonts.googleapis.com/css2?family=Yeseva+One&family=Source+Sans+3:wght@400&display=swap';
    } else if (theme === 'temple') {
      url = 'https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Cormorant+Garamond:wght@400&display=swap';
    } else {
      return; // brutalist uses system fonts
    }
    if (fontLoadUrls[url]) return;
    fontLoadUrls[url] = true;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = url;
    l.crossOrigin = 'anonymous';
    document.head.appendChild(l);
  }

  function apply(nextIdx, withTrip) {
    idx = ((nextIdx % THEMES.length) + THEMES.length) % THEMES.length;
    if (withTrip && !reduce) {
      root.classList.add('tripping');
      setTimeout(function () { root.classList.remove('tripping'); }, TRIP_MS);
    }
    root.setAttribute('data-theme', THEMES[idx]);
    ensureThemeFonts(THEMES[idx]);
    // Any swap resets the auto-rotate clock.
    scheduleAuto();
  }

  function scheduleAuto() {
    if (autoTimer) clearTimeout(autoTimer);
    var delay = AUTO_MIN_MS + Math.random() * AUTO_RAND_MS;
    autoTimer = setTimeout(function () {
      apply(pickRandomNext(), true);
    }, delay);
  }

  // Scroll trigger — accumulate scroll distance; fire when the
  // threshold is crossed AND the cooldown has elapsed.
  if (!reduce) {
    var lastY = window.scrollY || 0;
    var accum = 0;
    var lastScrollSwap = 0;
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      accum += Math.abs(y - lastY);
      lastY = y;
      var now = Date.now();
      if (accum >= SCROLL_THRESHOLD_PX && (now - lastScrollSwap) >= SCROLL_COOLDOWN_MS) {
        accum = 0;
        lastScrollSwap = now;
        apply(pickRandomNext(), true);
      }
    }, { passive: true });
  }

  var btn = document.getElementById('theme-cycle');
  if (btn) {
    btn.addEventListener('click', function () {
      apply(pickRandomNext(), true);
    });
  }

  // Start at default (cyber). Auto-rotate kicks off after a beat.
  apply(0, false);
  if (!reduce) setTimeout(scheduleAuto, FIRST_AUTO_DELAY_MS);
})();
