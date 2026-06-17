(function () {
  var progressBar = document.querySelector(".progress-bar");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".side-toc a"));
  var sections = navLinks
    .map(function (link) { return document.querySelector(link.getAttribute("href")); })
    .filter(Boolean);

  function updateProgress() {
    var scrollTop = window.scrollY || document.documentElement.scrollTop;
    var height = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    var pct = Math.min(100, Math.max(0, (scrollTop / height) * 100));
    if (progressBar) progressBar.style.transform = "scaleX(" + pct / 100 + ")";

    var active = sections[0];
    sections.forEach(function (section) {
      if (section.getBoundingClientRect().top <= 112) active = section;
    });
    navLinks.forEach(function (link) {
      link.setAttribute("aria-current", active && link.getAttribute("href") === "#" + active.id ? "true" : "false");
    });
  }

  function installCopyButtons() {
    Array.prototype.slice.call(document.querySelectorAll("[data-copy-source]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var target = document.querySelector(button.getAttribute("data-copy-source"));
        if (!target || !navigator.clipboard) return;
        navigator.clipboard.writeText(target.innerText).then(function () {
          var old = button.innerText;
          button.innerText = button.getAttribute("data-copied-label") || "已复制";
          window.setTimeout(function () { button.innerText = old; }, 1200);
        });
      });
    });
  }

  function setLanguage(lang) {
    document.documentElement.lang = lang;
    Array.prototype.slice.call(document.querySelectorAll("[data-set-lang]")).forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-set-lang") === lang ? "true" : "false");
    });
    updateProgress();
  }

  function installLanguageSwitch() {
    var initial = document.documentElement.lang === "en" ? "en" : "zh-CN";
    Array.prototype.slice.call(document.querySelectorAll("[data-set-lang]")).forEach(function (button) {
      button.addEventListener("click", function () {
        setLanguage(button.getAttribute("data-set-lang") || "zh-CN");
      });
    });
    setLanguage(initial);
  }

  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  installCopyButtons();
  installLanguageSwitch();
  updateProgress();
})();
