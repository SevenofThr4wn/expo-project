/**
 * UI utilities — theme toggle + sidebar collapse, both persisted to localStorage.
 */
(function () {
    const THEME_KEY   = 'faceid-theme';
    const SIDEBAR_KEY = 'faceid-sidebar';

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        const btn  = document.getElementById('themeToggle');
        if (!btn) return;
        btn.title  = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
        btn.querySelector('.icon-moon').style.display = theme === 'light' ? 'none' : '';
        btn.querySelector('.icon-sun').style.display  = theme === 'light' ? '' : 'none';
    }

    function applySidebar(collapsed) {
        document.body.classList.toggle('sidebar-collapsed', collapsed);
        localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0');
        const btn = document.getElementById('sidebarToggle');
        if (btn) btn.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
    }

    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(localStorage.getItem(THEME_KEY) || 'dark');
        applySidebar(localStorage.getItem(SIDEBAR_KEY) === '1');

        document.getElementById('themeToggle')?.addEventListener('click', () => {
            const cur = document.documentElement.getAttribute('data-theme') || 'dark';
            applyTheme(cur === 'dark' ? 'light' : 'dark');
        });

        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            applySidebar(!document.body.classList.contains('sidebar-collapsed'));
        });
    });
})();
