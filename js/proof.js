// 7. Header proof rotator — one social-proof item visible at a time,
//    crossfade between swaps. Only claim verifiable facts here.
(function proof() {
  var el = document.getElementById('dial-proof');
  if (!el) return;
  var ITEMS = [ // keep ≤24 chars — the dial must fit a 360px-wide phone
    'SPOTIFY ★5.0 · 9 RATINGS',
    '9/9 RATINGS · FIVE STARS',
    'ON THE AIR SINCE 2020'
  ];
  var i = 0;
  setInterval(function () {
    el.classList.add('out');
    setTimeout(function () {
      i = (i + 1) % ITEMS.length;
      el.textContent = ITEMS[i];
      el.classList.remove('out');
    }, 320);
  }, 6000);
})();
