document.addEventListener("click", function (event) {

    const tab = event.target.closest("[data-account-tab]");

    if (!tab) return;

    const group = tab.closest("[data-account-tabs]");

    group.querySelectorAll("[data-account-tab]").forEach(btn => {

        btn.classList.remove(
            "text-blue-600",
            "border-blue-600"
        );

        btn.classList.add(
            "text-slate-500",
            "border-transparent"
        );

    });

    tab.classList.remove(
        "text-slate-500",
        "border-transparent"
    );

    tab.classList.add(
        "text-blue-600",
        "border-blue-600"
    );

});

document.addEventListener('DOMContentLoaded', function() {
  // ----- Переключение вкладок (табы) -----
  document.querySelectorAll('[data-tabs]').forEach(group => {
    const tabs = group.querySelectorAll('.tab-btn');
    const panes = group.closest('section').querySelectorAll('.tab-pane');

    tabs.forEach(btn => {
      btn.addEventListener('click', function(e) {
        const target = this.dataset.target;
        tabs.forEach(b => {
          b.classList.remove('text-blue-600', 'border-blue-600');
          b.classList.add('text-slate-500', 'border-transparent');
        });
        this.classList.add('text-blue-600', 'border-blue-600');
        this.classList.remove('text-slate-500', 'border-transparent');

        panes.forEach(p => p.classList.add('hidden'));
        document.getElementById(target).classList.remove('hidden');
      });
    });
  });

  // ----- Автоматическая подсветка пунктов меню при скролле (как в settings) -----
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.account-nav-link');

  // Функция, определяющая, какая секция сейчас в области видимости (сверху)
  function updateActiveLink() {
    let currentId = '';
    // Определяем верхнюю границу окна + небольшой отступ (например, 120px, чтобы учитывать sticky header)
    const scrollY = window.scrollY + 120;

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionBottom = sectionTop + section.offsetHeight;
      // Если верхняя граница окна находится внутри секции
      if (scrollY >= sectionTop && scrollY < sectionBottom) {
        currentId = section.id;
      }
    });

    // Если ни одна секция не совпала (например, в самом верху), берём первую
    if (!currentId && sections.length > 0) {
      currentId = sections[0].id;
    }

    // Убираем is-active у всех ссылок, затем добавляем той, у которой href совпадает с #currentId
    navLinks.forEach(link => link.classList.remove('is-active'));
    if (currentId) {
      const activeLink = document.querySelector(`.account-nav-link[href="#${currentId}"]`);
      if (activeLink) {
        activeLink.classList.add('is-active');
      }
    }
  }

  // Вызываем при загрузке и при скролле
  window.addEventListener('scroll', updateActiveLink);
  window.addEventListener('resize', updateActiveLink);
  // Также сразу после загрузки, чтобы подсветить начальный раздел
  setTimeout(updateActiveLink, 100);

  // ----- Дополнительно: если кликнуть по ссылке, она тоже становится активной (но скролл переопределит) -----
  navLinks.forEach(link => {
    link.addEventListener('click', function() {
      navLinks.forEach(l => l.classList.remove('is-active'));
      this.classList.add('is-active');
    });
  });
});

// Переключатель на вкладку при перехоже через url
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get("friends_tab");

    console.log("tab =", tab);

    const button = document.querySelector(`[data-tab="${tab}"]`);

    console.log("button =", button);

    if (button) {
        button.click();
    }
});