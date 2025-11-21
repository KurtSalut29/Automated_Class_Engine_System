// Dashboard script
document.addEventListener("DOMContentLoaded", () => {
  const counters = document.querySelectorAll(".counter");
  counters.forEach((counter) => {
    const updateCount = () => {
      const target = +counter.getAttribute("data-target");
      const current = +counter.innerText;
      const increment = Math.ceil(target / 80);
      if (current < target) {
        counter.innerText = current + increment;
        setTimeout(updateCount, 30);
      } else {
        counter.innerText = target;
      }
    };
    updateCount();
  });

  // Function to create a small doughnut chart
  const createMiniChart = (id, value, color) => {
    const ctx = document.getElementById(id).getContext("2d");
    new Chart(ctx, {
      type: "doughnut",
      data: {
        datasets: [
          {
            data: [value, 100 - value],
            backgroundColor: [color, "#e9ecef"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        cutout: "75%",
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        rotation: -90,
        circumference: 180,
      },
    });
  };

  // Replace these with your Django context variables
  const totals = {
    instructors: parseInt(
      document
        .querySelector("#chart_instructors")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
    sections: parseInt(
      document
        .querySelector("#chart_sections")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
    schedules: parseInt(
      document
        .querySelector("#chart_schedules")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
    subjects: parseInt(
      document
        .querySelector("#chart_subjects")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
    rooms: parseInt(
      document
        .querySelector("#chart_rooms")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
    prospectus: parseInt(
      document
        .querySelector("#chart_prospectus")
        .closest(".stat-card")
        .querySelector(".counter").dataset.target
    ),
  };

  // Mini doughnut charts (color-coded)
  createMiniChart("chart_instructors", totals.instructors % 100, "#1cc88a");
  createMiniChart("chart_sections", totals.sections % 100, "#36b9cc");
  createMiniChart("chart_schedules", totals.schedules % 100, "#f6c23e");
  createMiniChart("chart_subjects", totals.subjects % 100, "#e74a3b");
  createMiniChart("chart_rooms", totals.rooms % 100, "#858796");
  createMiniChart("chart_prospectus", totals.prospectus % 100, "#5a5c69");
});
//End of dashboard script

document.addEventListener("DOMContentLoaded", () => {
  // -----------------------------
  // Toast / Notification Setup
  // -----------------------------
  const toastContainer = document.createElement("div");
  toastContainer.id = "toastContainer";
  toastContainer.className = "toast-container";
  const toast = document.createElement("div");
  toast.id = "toastMessage";
  toast.className = "toast";
  toastContainer.appendChild(toast);
  document.body.appendChild(toastContainer);

  function showToast(message, type = "success") {
    toast.innerText = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
      toast.className = "toast";
    }, 3000);
  }

  // -----------------------------
  // Search Filter
  // -----------------------------
  const searchInput = document.getElementById("searchInput");
  const tableRows = document.querySelectorAll("#usersTable tr");

  searchInput?.addEventListener("input", function () {
    const filter = this.value.toLowerCase();
    tableRows.forEach((row) => {
      const name = row.children[2]?.innerText.toLowerCase() || "";
      const email = row.children[3]?.innerText.toLowerCase() || "";
      const role = row.children[4]?.innerText.toLowerCase() || "";
      row.style.display =
        name.includes(filter) || email.includes(filter) || role.includes(filter)
          ? ""
          : "none";
    });
  });

  // -----------------------------
  // Role Filter Buttons
  // -----------------------------
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const role = btn.dataset.role.toLowerCase();
      tableRows.forEach((row) => {
        row.style.display =
          role === "all" || row.dataset.role.toLowerCase() === role
            ? ""
            : "none";
      });
    });
  });

  // -----------------------------
  // Select All + Row Highlight
  // -----------------------------
  const headerCheckbox = document.getElementById("headerCheckbox");
  const rowCheckboxes = document.querySelectorAll(".rowCheckbox");

  headerCheckbox?.addEventListener("change", () => {
    rowCheckboxes.forEach((cb) => {
      cb.checked = headerCheckbox.checked;
      cb.closest("tr")?.classList.toggle("selected", headerCheckbox.checked);
    });
  });

  rowCheckboxes.forEach((cb) => {
    cb.addEventListener("change", () => {
      cb.closest("tr")?.classList.toggle("selected", cb.checked);
      headerCheckbox.checked = Array.from(rowCheckboxes).every(
        (r) => r.checked
      );
    });
  });

  // -----------------------------
  // Bulk Actions
  // -----------------------------
 
  // -----------------------------
  // CSRF Helper
  // -----------------------------
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});

// -----------------------------
// Highlight active role from URL
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
  const currentRole = new URLSearchParams(window.location.search).get("role");
  if (currentRole) {
    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.classList.remove("active");
      if (btn.dataset.role.toLowerCase() === currentRole.toLowerCase())
        btn.classList.add("active");
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");
  const tableRows = document.querySelectorAll("#usersTable tr");

  // Search filter
  searchInput?.addEventListener("input", function () {
    const filter = this.value.toLowerCase();
    tableRows.forEach((row) => {
      const name = row.children[2]?.innerText.toLowerCase() || "";
      const email = row.children[3]?.innerText.toLowerCase() || "";
      const role = row.children[4]?.innerText.toLowerCase() || "";
      row.style.display =
        name.includes(filter) || email.includes(filter) || role.includes(filter)
          ? ""
          : "none";
    });
  });

  // Filter buttons
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const role = btn.dataset.role.toLowerCase();
      tableRows.forEach((row) => {
        row.style.display =
          role === "all" || row.dataset.role.toLowerCase() === role
            ? ""
            : "none";
      });
    });
  });

  // Select all + row highlight
  const headerCheckbox = document.getElementById("headerCheckbox");
  const rowCheckboxes = document.querySelectorAll(".rowCheckbox");

  headerCheckbox?.addEventListener("change", () => {
    rowCheckboxes.forEach((cb) => {
      cb.checked = headerCheckbox.checked;
      cb.closest("tr")?.classList.toggle("selected", headerCheckbox.checked);
    });
  });

  rowCheckboxes.forEach((cb) => {
    cb.addEventListener("change", () => {
      cb.closest("tr")?.classList.toggle("selected", cb.checked);
      headerCheckbox.checked = Array.from(rowCheckboxes).every(
        (r) => r.checked
      );
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
    const toasts = document.querySelectorAll(".toast");
    toasts.forEach((toast, index) => {
        // Delay each toast slightly if you want staggered appearance
        toast.style.animationDelay = `${index * 0.2}s`;

        // Remove each toast after animation (4s)
        toast.addEventListener("animationend", () => {
            toast.remove();
        });
    });
});