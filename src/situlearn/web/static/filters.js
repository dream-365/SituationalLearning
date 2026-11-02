(() => {
  "use strict";

  const form = document.querySelector(".filters");
  if (!form) return;

  let timer = null;

  function submitFilters() {
    if (typeof form.requestSubmit === "function") {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  form.addEventListener("change", (event) => {
    if (event.target instanceof HTMLSelectElement) {
      submitFilters();
    }
  });

  const search = form.querySelector('input[type="search"]');
  if (!search) return;

  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(submitFilters, 350);
  });

  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      clearTimeout(timer);
      submitFilters();
    }
  });
})();
