// ============================================================
// HEADER LOADER - Dynamically loads header.html
// ============================================================

function loadHeader() {
    fetch('/components/header.html')
        .then(response => response.text())
        .then(data => {
            const headerPlaceholder = document.getElementById('header-placeholder');
            if (headerPlaceholder) {
                headerPlaceholder.innerHTML = data;
                
                // Re-run auth guard to update login/logout buttons
                if (typeof updateHeaderUI === 'function') {
                    setTimeout(updateHeaderUI, 100);
                }
                if (typeof fixNavigationLinks === 'function') {
                    setTimeout(fixNavigationLinks, 100);
                }
            }
        })
        .catch(error => console.error('Error loading header:', error));
}

function loadFooter() {
    fetch('/components/footer.html')
        .then(response => response.text())
        .then(data => {
            const footerPlaceholder = document.getElementById('footer-placeholder');
            if (footerPlaceholder) {
                footerPlaceholder.innerHTML = data;
            }
        })
        .catch(error => console.error('Error loading footer:', error));
}

// Load components when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadHeader();
        loadFooter();
    });
} else {
    loadHeader();
    loadFooter();
}
