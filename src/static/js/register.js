/**
 * register.js — src/static/js/register.js
 *
 * 1. Очистка формы при закрытии модалки
 * 2. HTMX: после загрузки регионов/городов — снять disabled
 * 3. Четыре селекта для даты рождения → скрытый input birth_date (YYYY-MM-DD)
 */

(function () {
  "use strict";

  // ─── 1. Очистка формы при закрытии модалки ────────────────────────────────
  function clearRegisterForm() {
    var form = document.querySelector("#register-modal form");
    if (!form) return;
    form.reset();

    var rs = document.getElementById("id_region_select");
    var cs = document.getElementById("id_city_select");
    if (rs) { rs.innerHTML = '<option value="">Select region</option>'; rs.disabled = true; }
    if (cs) { cs.innerHTML = '<option value="">Select city</option>';   cs.disabled = true; }

    ["bd_day", "bd_month", "bd_year", "id_birth_date"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = "";
    });

    form.querySelectorAll(".border-red-400").forEach(function (el) {
      el.classList.remove("border-red-400", "focus:border-red-500", "focus:ring-red-100");
      el.classList.add("border-slate-300");
    });
    form.querySelectorAll("p.text-red-600").forEach(function (el) { el.textContent = ""; });
    var feedback = document.getElementById("username-feedback");
    if (feedback) feedback.innerHTML = "";
  }

  document.addEventListener("click", function (e) {
    if (
      e.target.closest('[data-modal-close="register-modal"]') ||
      e.target.closest('[data-modal-backdrop]')
    ) {
      setTimeout(clearRegisterForm, 300);
    }
  });

  // ─── 2. HTMX: после загрузки регионов/городов ─────────────────────────────
  // innerHTML-свап не меняет DOM-элемент — тот же <select>, просто новые <option>.
  // Снимаем disabled и сбрасываем зависимые селекты.
  document.addEventListener("htmx:afterSettle", function (e) {
    var target = e.detail && e.detail.target;
    if (!target) return;

    if (target.id === "id_region_select") {
      target.disabled = target.options.length <= 1;
      // Сбрасываем город
      var cs = document.getElementById("id_city_select");
      if (cs) { cs.innerHTML = '<option value="">Select city</option>'; cs.disabled = true; }
    }

    if (target.id === "id_city_select") {
      target.disabled = target.options.length <= 1;
    }
  });

  // При сбросе страны — чистим регион и город
  document.addEventListener("change", function (e) {
    if (e.target && e.target.id === "id_country" && !e.target.value) {
      var rs = document.getElementById("id_region_select");
      var cs = document.getElementById("id_city_select");
      if (rs) { rs.innerHTML = '<option value="">Select region</option>'; rs.disabled = true; }
      if (cs) { cs.innerHTML = '<option value="">Select city</option>';   cs.disabled = true; }
    }
  });

  // ─── 3. Дата рождения ──────────────────────────────────────────────────────
  function initBirthDate() {
    var bdDay    = document.getElementById("bd_day");
    var bdMonth  = document.getElementById("bd_month");
    var bdYear   = document.getElementById("bd_year");
    var bdHidden = document.getElementById("id_birth_date");
    if (!bdDay || !bdMonth || !bdYear || !bdHidden) return;

    for (var d = 1; d <= 31; d++) {
      var opt = document.createElement("option");
      opt.value = d; opt.textContent = d;
      bdDay.appendChild(opt);
    }
    var currentYear = new Date().getFullYear();
    for (var y = currentYear; y >= currentYear - 100; y--) {
      var optY = document.createElement("option");
      optY.value = y; optY.textContent = y;
      bdYear.appendChild(optY);
    }

    var existing = bdHidden.value;
    if (existing && /^\d{4}-\d{2}-\d{2}$/.test(existing)) {
      var parts = existing.split("-");
      bdYear.value  = parseInt(parts[0], 10);
      bdMonth.value = parseInt(parts[1], 10);
      bdDay.value   = parseInt(parts[2], 10);
    }

    function syncHidden() {
      var y = bdYear.value, m = bdMonth.value, d = bdDay.value;
      bdHidden.value = (y && m && d)
        ? y + "-" + (m.length === 1 ? "0" + m : m) + "-" + (String(d).length < 2 ? "0" + d : d)
        : "";
    }
    bdDay.addEventListener("change", syncHidden);
    bdMonth.addEventListener("change", syncHidden);
    bdYear.addEventListener("change", syncHidden);
  }

  // ─── Инициализация ─────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    // form_invalid: восстанавливаем состояние disabled
    var rs = document.getElementById("id_region_select");
    var cs = document.getElementById("id_city_select");
    if (rs) rs.disabled = rs.options.length <= 1;
    if (cs) cs.disabled = cs.options.length <= 1;
    initBirthDate();
  });

})();