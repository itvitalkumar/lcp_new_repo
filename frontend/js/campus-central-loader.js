// ============================================================
// CAMPUS CENTRAL - COMBINED LOADER
// Loads header, footer, and initializes all components
// ============================================================

// Load header and footer
function loadHeader() {
    fetch('/components/header.html')
        .then(response => response.text())
        .then(data => {
            const el = document.getElementById('header-placeholder');
            if (el) el.innerHTML = data;
            if (typeof updateHeaderUI === 'function') setTimeout(updateHeaderUI, 100);
        })
        .catch(e => console.error('Header load error:', e));
}

function loadFooter() {
    fetch('/components/footer.html')
        .then(response => response.text())
        .then(data => {
            const el = document.getElementById('footer-placeholder');
            if (el) el.innerHTML = data;
        })
        .catch(e => console.error('Footer load error:', e));
}

// Initialize Retune (if in development)
function initRetune() {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        // Retune will be initialized separately via retune-init.js
        console.log('🔧 Development mode - Retune ready');
    }
}

// Start everything
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadHeader();
        loadFooter();
        initRetune();
    });
} else {
    loadHeader();
    loadFooter();
    initRetune();
}
