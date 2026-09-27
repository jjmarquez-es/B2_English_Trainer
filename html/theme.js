// theme.js // SISTEMA DE TEMAS Y NAVEGACIÓN ACTIVA
(function() {
    const cachedTheme = localStorage.getItem('neural_theme') || 'cyberpunk';
    document.documentElement.setAttribute('data-theme', cachedTheme);
})();

function applyTheme(themeName) {
    const validThemes = ['cyberpunk', 'matrix', 'university', 'synthwave'];
    const chosen = validThemes.includes(themeName) ? themeName : 'cyberpunk';
    
    document.documentElement.setAttribute('data-theme', chosen);
    localStorage.setItem('neural_theme', chosen);

    const select = document.getElementById('theme-select');
    if (select && select.value !== chosen) {
        select.value = chosen;
    }
}

function changeActiveTheme(themeName) {
    applyTheme(themeName);
    if (typeof userState !== 'undefined') {
        userState.theme = themeName;
        if (typeof persistState === 'function') {
            persistState();
        }
    }
}

// DETECCIÓN AUTOMÁTICA DE LA PÁGINA ACTUAL E ILUMINACIÓN DEL BOTÓN
document.addEventListener('DOMContentLoaded', () => {
    let currentPage = window.location.pathname.split('/').pop().split('?')[0].split('#')[0];
    if (!currentPage || currentPage === '') {
        currentPage = 'index.html';
    }

    // 1. Iluminar en cabeceras superiores (.nav-actions)
    document.querySelectorAll('.nav-actions a').forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            const targetPage = href.split('/').pop().split('?')[0].split('#')[0];
            if (targetPage === currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        }
    });

    // 2. Iluminar en barras laterales (.sidebar)
    document.querySelectorAll('.sidebar a.nav-category-btn, .sidebar a.category-btn').forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            const targetPage = href.split('/').pop().split('?')[0].split('#')[0];
            if (targetPage === currentPage) {
                link.classList.add('active');
            }
        }
    });
});