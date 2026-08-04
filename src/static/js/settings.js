/**
 * settings.js — loaded only on /settings/
 */

// ─── Toast ────────────────────────────────────────────────────────────────────

window.settingsToast = function (event) {
  const toast = document.getElementById('settings-toast');
  if (!toast) return;

  let ok = event.detail.successful;
  let message = ok ? 'Changes saved' : 'Something went wrong';

  try {
    const triggerHeader = event.detail.xhr.getResponseHeader('HX-Trigger');
    if (triggerHeader) {
      const parsed = JSON.parse(triggerHeader);
      if (parsed.settingsToast) {
        ok      = parsed.settingsToast.ok      ?? ok;
        message = parsed.settingsToast.message ?? message;
      }
    }
  } catch (_) { /* ignore */ }

  showToast(toast, ok, message);
};

function showToast(el, ok, message) {
  el.className = [
    'fixed top-6 right-6 z-50 flex items-center gap-3 px-4 py-3',
    'rounded-xl border shadow text-sm font-medium transition duration-200',
    ok
      ? 'bg-white border-green-200 text-green-700'
      : 'bg-white border-red-200 text-red-600',
  ].join(' ');

  const icon = ok
    ? `<svg class="w-5 h-5 shrink-0 text-green-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
         <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
       </svg>`
    : `<svg class="w-5 h-5 shrink-0 text-red-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
         <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
       </svg>`;

  el.innerHTML = icon + `<span>${message}</span>`;
  el.classList.remove('hidden');

  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.classList.add('opacity-0');
    setTimeout(() => {
      el.classList.add('hidden');
      el.classList.remove('opacity-0');
    }, 300);
  }, 3000);
}

// ─── Bio, STATUS counter ──────────────────────────────────────────────────────────────

document.querySelectorAll("[data-counter]").forEach(field => {
    const counter = document.getElementById(field.dataset.counter);

    if (!counter) return;

    const updateCounter = () => {
        counter.textContent = field.value.length;
    };

    field.addEventListener("input", updateCounter);

    // Обновить при загрузке страницы
    updateCounter();
});

// ─── Avatar preview ───────────────────────────────────────────────────────────
// БАГ #5 ИСПРАВЛЕН: одна функция, правильные ID, проверка размера

window.previewAvatar = function (input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];

  if (file.size > 5 * 1024 * 1024) {
    alert('File is too large. Maximum size is 5 MB.');
    input.value = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    const preview     = document.getElementById('avatar-preview');
    const placeholder = document.getElementById('avatar-placeholder');
    if (preview) {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
    }
    if (placeholder) {
      placeholder.classList.add('hidden');
    }
  };
  reader.readAsDataURL(file);
};

// ─── Sidebar active highlight ─────────────────────────────────────────────────

const navLinks = document.querySelectorAll('.settings-nav-link');
const sections = Array.from(document.querySelectorAll('section[id]'));

function setActiveLink() {
  const scrollY = window.scrollY + 120;
  let currentId = sections[0]?.id;
  for (const section of sections) {
    if (section.offsetTop <= scrollY) currentId = section.id;
  }
  for (const link of navLinks) {
    const href = link.getAttribute('href');
    link.classList.toggle('is-active', href === `#${currentId}`);
  }
}

window.addEventListener('scroll', setActiveLink, { passive: true });
setActiveLink();

// ─── Delete account ───────────────────────────────────────────────────────────

window.confirmDeleteAccount = function () {
  if (window.confirm('Are you sure you want to permanently delete your account? This action cannot be undone.')) {
    window.location.href = '/settings/delete-account/';
  }
};

// ─── Geo cascade: country → regions (через HTMX — обрабатывается автоматически) ──
// HTMX сам слушает change на #country-select и #region-select — дополнительный
// JS для этого НЕ нужен. Старый fetch-код удалён.

// ─── Avatar preview (js-атрибут вместо onchange) ─────────────────────────────

const avatarInput = document.querySelector('[js-avatar-input]');
if (avatarInput) {
  avatarInput.addEventListener('change', function () {
    if (!this.files || !this.files[0]) return;
    const file = this.files[0];
    if (file.size > 5 * 1024 * 1024) {
      alert('File is too large. Maximum size is 5 MB.');
      this.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const preview     = document.getElementById('avatar-preview');
      const placeholder = document.getElementById('avatar-placeholder');
      if (preview) { preview.src = e.target.result; preview.classList.remove('hidden'); }
      if (placeholder) { placeholder.classList.add('hidden'); }
    };
    reader.readAsDataURL(file);
  });
}

// ─── Delete account (js-атрибут вместо onclick) ──────────────────────────────

const deleteBtn = document.querySelector('[js-delete-account]');
if (deleteBtn) {
  deleteBtn.addEventListener('click', () => {
    if (window.confirm('Are you sure you want to permanently delete your account? This action cannot be undone.')) {
      window.location.href = '/settings/delete-account/';
    }
  });
}

// ─── Flatpickr — date of birth ────────────────────────────────────────────────
// Flatpickr грузится как обычный <script> в extra_head, поэтому window.flatpickr доступен.
// Максимальная дата — 18 лет назад от сегодня.

const birthInput = document.getElementById('birth-date-picker');
if (birthInput && typeof flatpickr !== 'undefined') {
  const today = new Date();
  const maxDate = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());

  flatpickr(birthInput, {
    dateFormat: 'Y-m-d',       // формат, который ждёт Django (birth_date field)
    maxDate: maxDate,           // нельзя выбрать дату моложе 18 лет
    defaultDate: birthInput.value || null,
    disableMobile: false,       // на мобильных показывает нативный picker
    allowInput: false,          // только через календарь, не руками
    locale: {
      firstDayOfWeek: 1,        // неделя с понедельника
    },
  });
} else if (birthInput) {
  // Flatpickr не загрузился — fallback: обычный date input
  console.warn('settings.js: flatpickr not loaded, falling back to native date input');
  birthInput.type = 'date';
}