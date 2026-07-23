(function () {
  const searchInput = document.querySelector("#globalSearch");
  const rows = () => Array.from(document.querySelectorAll("[data-asset-row]"));
  const filterDrawer = document.querySelector("#filterDrawer");
  const assetModal = document.querySelector("#assetModal");
  let activeSegment = "all";

  document.querySelector(".user-button")?.addEventListener("click", (event) => {
    const button = event.currentTarget;
    const menu = document.querySelector("#userDropdown");
    const isOpen = menu?.classList.toggle("is-open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  document.addEventListener("click", (event) => {
    const userMenu = event.target.closest(".user-menu");
    if (userMenu) return;
    document.querySelector("#userDropdown")?.classList.remove("is-open");
    document.querySelector(".user-button")?.setAttribute("aria-expanded", "false");
  });

  function selectedValues(selector) {
    return Array.from(document.querySelectorAll(selector))
      .filter((input) => input.checked)
      .map((input) => input.value);
  }

  function matchesSegment(row) {
    if (activeSegment === "all") return true;
    if (activeSegment === "critical") return ["Atencao", "Offline", "Sem coleta"].includes(row.dataset.status);
    return row.dataset.type === activeSegment;
  }

  function applyFilters() {
    const query = (searchInput?.value || "").trim().toLowerCase();
    const statuses = selectedValues("[data-filter-status]");
    const types = selectedValues("[data-filter-type]");
    let visible = 0;

    rows().forEach((row) => {
      const text = (row.dataset.search || "").toLowerCase();
      const ok =
        text.includes(query) &&
        statuses.includes(row.dataset.status) &&
        types.includes(row.dataset.type) &&
        matchesSegment(row);
      row.hidden = !ok;
      if (ok) visible += 1;
    });

    document.querySelectorAll("[data-visible-count]").forEach((node) => {
      node.textContent = `Mostrando ${visible} ativo${visible === 1 ? "" : "s"} filtrado${visible === 1 ? "" : "s"}`;
    });
  }

  searchInput?.addEventListener("input", applyFilters);

  document.querySelectorAll("[data-segment], .segmented button").forEach((button) => {
    button.addEventListener("click", () => {
      const value = button.dataset.segment || button.textContent.trim().toLowerCase();
      const normalized = {
        todos: "all",
        notebooks: "notebook",
        desktops: "desktop",
        criticos: "critical",
      }[value] || value;
      activeSegment = normalized;
      button.closest(".segmented")?.querySelectorAll("button").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      applyFilters();
    });
  });

  document.querySelectorAll("[data-filter-status], [data-filter-type]").forEach((input) => {
    input.addEventListener("change", applyFilters);
  });

  document.querySelectorAll(".js-open-filters").forEach((button) => {
    button.addEventListener("click", () => {
      filterDrawer?.classList.add("is-open");
      filterDrawer?.setAttribute("aria-hidden", "false");
    });
  });

  document.querySelectorAll(".js-close-filters").forEach((button) => {
    button.addEventListener("click", () => {
      filterDrawer?.classList.remove("is-open");
      filterDrawer?.setAttribute("aria-hidden", "true");
      applyFilters();
    });
  });

  document.querySelector("#clearFilters")?.addEventListener("click", () => {
    document.querySelectorAll("[data-filter-status], [data-filter-type]").forEach((input) => {
      input.checked = true;
    });
    applyFilters();
  });

  document.querySelectorAll(".js-open-asset-modal").forEach((button) => {
    button.addEventListener("click", () => {
      assetModal?.classList.add("is-open");
      assetModal?.setAttribute("aria-hidden", "false");
      assetModal?.querySelector("input")?.focus();
    });
  });

  document.querySelectorAll(".js-close-modal").forEach((button) => {
    button.addEventListener("click", () => {
      assetModal?.classList.remove("is-open");
      assetModal?.setAttribute("aria-hidden", "true");
    });
  });

  document.querySelectorAll(".js-export-soon").forEach((button) => {
    button.addEventListener("click", () => {
      button.classList.add("is-pulsing");
      button.textContent = "Exportar em breve";
      window.setTimeout(() => {
        button.classList.remove("is-pulsing");
        button.textContent = "Exportar";
      }, 1800);
    });
  });

  document.addEventListener("click", (event) => {
    const menuButton = event.target.closest(".js-row-menu");
    if (!menuButton) return;
    menuButton.classList.toggle("is-active");
  });

  applyFilters();
})();
