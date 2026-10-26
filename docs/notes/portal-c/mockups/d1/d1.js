// d1 progressive enhancement. Every page reads and posts fully without it.
(function () {
  // 1. Messages: mark the step on screen in the chip row (>= 640 px) and the phone "Jump to" control.
  var chipList = document.querySelector(".jump__list");
  var menu = document.querySelector(".jumpmenu");
  var label = menu && menu.querySelector(".jumpmenu__label");
  var links = [].slice.call(document.querySelectorAll(".jump__link, .jumpmenu__link"));
  var steps = [];
  links.forEach(function (a) {
    var el = document.getElementById(a.getAttribute("href").slice(1));
    if (el && steps.indexOf(el) < 0) steps.push(el);
  });
  if (steps.length && "IntersectionObserver" in window) {
    var visible = {};
    var mark = function () {
      var current = steps.filter(function (s) { return visible[s.id]; })[0];
      if (!current) return;
      links.forEach(function (a) {
        var on = a.getAttribute("href") === "#" + current.id;
        if (on) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
        if (on && label && a.classList.contains("jumpmenu__link")) label.textContent = label.dataset.lead + " " + a.textContent;
        if (on && chipList && a.classList.contains("jump__link")) {
          var bar = chipList.parentElement;
          if (a.offsetLeft < bar.scrollLeft || a.offsetLeft + a.offsetWidth > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = a.offsetLeft - 16;
        }
      });
    };
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      mark();
    }, { rootMargin: "-120px 0px -55% 0px" });
    steps.forEach(function (s) { io.observe(s); });
  }
  if (menu) menu.addEventListener("click", function (e) { if (e.target.closest(".jumpmenu__link")) menu.open = false; });

  // 2. A resting Save is aria-disabled; the first edit in its form turns it on.
  document.querySelectorAll('button[aria-disabled="true"][form]').forEach(function (btn) {
    var form = document.getElementById(btn.getAttribute("form"));
    btn.addEventListener("click", function (e) { if (btn.getAttribute("aria-disabled") === "true") e.preventDefault(); });
    if (form) form.addEventListener("input", function () { btn.removeAttribute("aria-disabled"); }, { once: true });
  });
})();
