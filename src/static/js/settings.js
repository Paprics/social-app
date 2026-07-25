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

// ─── Bio counter ──────────────────────────────────────────────────────────────

const bioTextarea = document.querySelector('textarea[name="bio"]');
const bioCount    = document.getElementById('bio-count');

if (bioTextarea && bioCount) {
  bioTextarea.addEventListener('input', () => {
    bioCount.textContent = bioTextarea.value.length;
  });
}

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