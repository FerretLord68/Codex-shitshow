const navButton = document.querySelector(".nav-toggle");
const nav = document.querySelector("#main-nav");
if (navButton && nav) {
  navButton.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    navButton.setAttribute("aria-expanded", String(open));
  });
}

function csrfToken() {
  return document.cookie.split("; ").find((row) => row.startsWith("__Host-mealhouse_csrf="))?.split("=")[1] || "";
}

document.querySelectorAll(".shopping-check").forEach((checkbox) => {
  checkbox.addEventListener("change", async () => {
    const previous = !checkbox.checked;
    checkbox.disabled = true;
    const body = new URLSearchParams({checked: String(checkbox.checked), version: checkbox.dataset.version});
    const response = await fetch(`/shopping/items/${checkbox.dataset.id}/toggle/`, {
      method: "POST",
      credentials: "same-origin",
      headers: {"X-CSRFToken": decodeURIComponent(csrfToken()), "Content-Type": "application/x-www-form-urlencoded"},
      body,
    });
    const live = document.querySelector("#shopping-live");
    if (response.ok) {
      const data = await response.json();
      checkbox.dataset.version = data.version;
      checkbox.closest("li").classList.toggle("checked", data.checked);
      if (live) live.textContent = document.documentElement.lang === "da" ? "Ændringen er gemt." : "Change saved.";
    } else {
      checkbox.checked = previous;
      if (live) live.textContent = document.documentElement.lang === "da"
        ? "Listen blev ændret af en anden. Genindlæs siden."
        : "Another person changed the list. Reload the page.";
    }
    checkbox.disabled = false;
  });
});

