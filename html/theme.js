// theme.js
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