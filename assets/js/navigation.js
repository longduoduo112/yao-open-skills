const searchInput = document.querySelector("#search");
const filters = Array.from(document.querySelectorAll(".filter"));
const cards = Array.from(document.querySelectorAll(".card"));
const categories = Array.from(document.querySelectorAll(".category"));
const navMenu = document.querySelector(".nav-menu");
let activeFilter = "all";

function normalize(value) {
  return value.toLowerCase().trim();
}

function applyFilters() {
  const query = normalize(searchInput.value);

  cards.forEach((card) => {
    const familyMatch = activeFilter === "all" || card.dataset.family === activeFilter;
    const text = normalize(`${card.innerText} ${card.dataset.search || ""}`);
    const searchMatch = !query || text.includes(query);
    card.classList.toggle("is-hidden", !(familyMatch && searchMatch));
  });

  categories.forEach((category) => {
    const visibleCards = category.querySelectorAll(".card:not(.is-hidden)");
    category.classList.toggle("is-hidden", visibleCards.length === 0);
  });
}

function setActiveFilter(filterName) {
  activeFilter = filterName;
  filters.forEach((item) => {
    item.setAttribute("aria-pressed", String(item.dataset.filter === filterName));
  });
  applyFilters();
}

filters.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveFilter(button.dataset.filter);
  });
});

searchInput.addEventListener("input", applyFilters);

document.querySelectorAll("[data-show-all]").forEach((link) => {
  link.addEventListener("click", () => {
    searchInput.value = "";
    setActiveFilter("all");
  });
});

document.querySelectorAll("[data-filter-link]").forEach((link) => {
  link.addEventListener("click", () => {
    searchInput.value = "";
    setActiveFilter(link.dataset.filterLink);
    link.closest("details").removeAttribute("open");
  });
});

document.addEventListener("click", (event) => {
  if (navMenu.open && !navMenu.contains(event.target)) {
    navMenu.removeAttribute("open");
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    navMenu.removeAttribute("open");
  }
});

applyFilters();
