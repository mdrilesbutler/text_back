// d1 progressive enhancement (the page reads and posts fully without it).
// Messages: the jump chip of the step on screen is marked current and kept in view.
(function () {
  var jump = document.querySelector(".jump__list");
  if (!jump || !("IntersectionObserver" in window)) return;
  var chips = {};
  jump.querySelectorAll("a[href^='#']").forEach(function (a) { chips[a.getAttribute("href").slice(1)] = a; });
  var steps = Object.keys(chips).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  var visible = {};
  function mark() {
    var current = null;
    steps.forEach(function (s) { if (visible[s.id] && !current) current = s.id; });
    if (!current) return;
    Object.keys(chips).forEach(function (id) {
      if (id === current) chips[id].setAttribute("aria-current", "location");
      else chips[id].removeAttribute("aria-current");
    });
    var c = chips[current], bar = jump.parentElement;
    if (c.offsetLeft < bar.scrollLeft || c.offsetLeft + c.offsetWidth > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = c.offsetLeft - 16;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
    mark();
  }, { rootMargin: "-120px 0px -55% 0px" });
  steps.forEach(function (s) { io.observe(s); });
})();
