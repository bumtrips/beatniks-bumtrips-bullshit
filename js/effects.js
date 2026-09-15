// 1. Typewriter effect on the hero tagline — cycles through a
//    curated list of quotes pulled from the show's own descriptions
//    and brand-aligned lines. Each quote types in, holds for a
//    beat, then erases before the next one starts.
(function typewriter() {
  var el = document.getElementById('tagline-typewriter');
  if (!el) return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var QUOTES = [
    'Your secret audio dose of acid.',
    'The moment spirit makes its wild plunge into matter.',
    'Raw sounds, real voices, and the rhythm of thought.',
    'Field-recorded transmissions from Berlin \u21C4 Santa Cruz.',
    'Mysticism, poetry, art, music, total bullshit.',
    'How do you know when a place is alive?',
    'There are adventures around the world and other dimensions.',
    'An hour and a half on warm stone.',
    'Bats in the rafters. Pyramid power. Love you.',
    'You cannot know everything. But you can know what is inside.',
    'We record the future through fresh poetry.',
    'Listen at your own risk.'
  ];

  if (reduce) {
    // No typing animation; just cycle whole strings every 5 s.
    el.textContent = QUOTES[0];
    var ridx = 0;
    setInterval(function () {
      ridx = (ridx + 1) % QUOTES.length;
      el.textContent = QUOTES[ridx];
    }, 5000);
    return;
  }

  var qIdx = 0;
  var i = 0;
  var erasing = false;

  function tick() {
    var text = QUOTES[qIdx];
    if (!erasing) {
      // Typing forward.
      if (i <= text.length) {
        el.textContent = text.slice(0, i);
        i++;
        setTimeout(tick, 38 + Math.random() * 60);
      } else {
        // Fully typed — hold for 4.2 s so the eye can read it.
        erasing = true;
        setTimeout(tick, 4200);
      }
    } else {
      // Erasing backward, faster than typing.
      if (i > 0) {
        el.textContent = text.slice(0, i - 1);
        i--;
        setTimeout(tick, 18);
      } else {
        // Erased — move to the next quote after a brief breath.
        erasing = false;
        qIdx = (qIdx + 1) % QUOTES.length;
        setTimeout(tick, 300);
      }
    }
  }

  tick();
})();

// 2. Konami code easter egg: ↑↑↓↓←→←→BA reveals a transmission.
(function konami() {
  var seq = [38,38,40,40,37,39,37,39,66,65];
  var buf = [];
  var msg = document.getElementById('konami-msg');
  window.addEventListener('keydown', function (e) {
    buf.push(e.keyCode);
    if (buf.length > seq.length) buf.shift();
    if (buf.join(',') === seq.join(',')) {
      msg.textContent = '↳ transmission unlocked · carry the signal';
      msg.classList.add('show');
      setTimeout(function () { msg.classList.remove('show'); msg.textContent = ''; }, 4200);
      buf = [];
    }
  });
})();

// 3. Rare transmission glitch — toggle a class on <body> for ~120ms at random intervals.
(function glitch() {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;
  function fire() {
    document.body.classList.add('glitch-on');
    setTimeout(function () { document.body.classList.remove('glitch-on'); }, 110);
    setTimeout(fire, 18000 + Math.random() * 32000); // every 18–50s
  }
  setTimeout(fire, 9000);
})();

// 4. Acid flashbacks — rare full-page colour invert.
(function acid() {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;
  function fire() {
    document.body.classList.add('acid-on');
    setTimeout(function () { document.body.classList.remove('acid-on'); }, 720);
    setTimeout(fire, 28000 + Math.random() * 38000); // every 28–66s
  }
  setTimeout(fire, 14000);
})();

// 5. "Receiving" ticker — random signal phrases that flash in the corner.
(function receiving() {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;
  var phrases = [
    'RECEIVING · BERLIN ↔ SANTA CRUZ',
    'DECODING · 226 transmissions',
    'CARRIER · ON THE AIR',
    'SIGNAL · LOCKED',
    'SCANNING · FIELD FREQ',
    'LISTENING · SPIRIT IN THE WIRE'
  ];
  var node = document.createElement('div');
  node.className = 'receiving';
  node.setAttribute('aria-hidden', 'true');
  document.body.appendChild(node);
  function fire() {
    var p = phrases[Math.floor(Math.random() * phrases.length)];
    node.textContent = '↳ ' + p;
    node.classList.add('show');
    setTimeout(function () { node.classList.remove('show'); }, 1800);
    setTimeout(fire, 7000 + Math.random() * 9000);
  }
  setTimeout(fire, 5500);
})();
