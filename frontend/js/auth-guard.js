// ========== CENTRAL AUTHENTICATION GUARD ==========
(function() {
    const PUBLIC_PAGES = ['index.html', 'login.html', 'signup.html', 'admin-login.html'];
    // ✅ FIX: Added fallback to 'index.html' when pathname is empty or '/'
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    // Check if current page requires login
    if (!PUBLIC_PAGES.includes(currentPage)) {
        const authToken = localStorage.getItem('authToken');
        const currentUser = localStorage.getItem('currentUser');
        
        if (!authToken || !currentUser) {
            const returnUrl = encodeURIComponent(window.location.href);
            window.location.replace(`login.html?redirect=${returnUrl}`);
            return;
        }
    }
    
    // ========== UPDATE HEADER FOR LOGGED-IN USER ==========
    function updateHeaderUI() {
        const userStr = localStorage.getItem('currentUser');
        
        // Get elements
        const authButtonsDiv = document.querySelector('.header-buttons');
        const userMenuDiv = document.getElementById('userMenu');
        const userNameSpan = document.getElementById('userName');
        
        console.log('🔍 updateHeaderUI - userStr:', !!userStr);
        console.log('🔍 Elements found - authButtonsDiv:', !!authButtonsDiv, 'userMenuDiv:', !!userMenuDiv, 'userNameSpan:', !!userNameSpan);
        
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                console.log('✅ User found:', user.full_name);
                
                // Hide login/signup buttons (add hidden class, not style.display)
                if (authButtonsDiv) {
                    authButtonsDiv.classList.add('hidden');
                    console.log('✅ Added hidden class to authButtonsDiv');
                }
                
                // Show user menu (remove hidden class)
                if (userMenuDiv) {
                    userMenuDiv.classList.remove('hidden');
                    console.log('✅ Removed hidden class from userMenuDiv');
                }
                
                // Set username
                if (userNameSpan) {
                    const displayName = user.full_name || user.name || (user.email ? user.email.split('@')[0] : 'User');
                    userNameSpan.innerText = displayName;
                    console.log('✅ Set userName to:', displayName);
                }
                
                // Also update any other username displays
                const allUserNameSpans = document.querySelectorAll('.user-name-display, .greeting-name');
                allUserNameSpans.forEach(span => {
                    span.innerText = user.full_name || user.name || (user.email ? user.email.split('@')[0] : 'User');
                });
                
            } catch(e) {
                console.error('Error parsing user:', e);
            }
        } else {
            console.log('⚠️ No user found - showing login buttons');
            // User not logged in - show login/signup buttons
            if (authButtonsDiv) {
                authButtonsDiv.classList.remove('hidden');
                console.log('✅ Removed hidden class from authButtonsDiv');
            }
            if (userMenuDiv) {
                userMenuDiv.classList.add('hidden');
                console.log('✅ Added hidden class to userMenuDiv');
            }
        }
    }
    
    // ========== ENSURE ALL NAVIGATION LINKS WORK ==========
    function fixNavigationLinks() {
        // Make sure all nav links point to correct pages
        const navLinks = {
            'Home': 'index.html',
            'Thank Teacher': 'teacher_group_creation_start.html',
            'Celebrate Together': 'celebration_group_creation_start.html',
            'Find Groups': 'find_groups.html',
            'My Groups': 'student_dashboard.html',
            'Success Stories': 'success_stories.html'
        };
        
        // Update any navigation links that might be broken
        document.querySelectorAll('nav a, .nav-link, [onclick*="showPage"]').forEach(link => {
            const text = link.innerText.trim();
            if (navLinks[text] && !link.hasAttribute('data-fixed')) {
                link.setAttribute('data-fixed', 'true');
                // Remove existing onclick and replace with href
                link.removeAttribute('onclick');
                link.href = navLinks[text];
            }
        });
    }
    
    // ========== GLOBAL LOGOUT FUNCTION ==========
    window.logout = function() {
        console.log('🚪 Logging out...');
        localStorage.removeItem('authToken');
        localStorage.removeItem('token');
        localStorage.removeItem('currentUser');
        localStorage.removeItem('user');
        localStorage.removeItem('isLoggedIn');
        window.location.href = 'index.html';
    };
    
    // ========== FORCE CHECK ON PAGE LOAD ==========
    function forceLoginCheck() {
        const token = localStorage.getItem('authToken');
        const userData = localStorage.getItem('currentUser');
        
        console.log('🔍 FORCE LOGIN CHECK - Token:', !!token, 'UserData:', !!userData);
        
        if (token && userData) {
            try {
                const user = JSON.parse(userData);
                console.log('✅ Force login successful for:', user.full_name);
                updateHeaderUI();
            } catch(e) {
                console.error('Force login error:', e);
            }
        } else {
            console.log('🔍 No token found, checking public page requirement');
            updateHeaderUI();
        }
    }
    
    // Run when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            forceLoginCheck();
            fixNavigationLinks();
        });
    } else {
        forceLoginCheck();
        fixNavigationLinks();
    }
    
    // Also run after a short delay for dynamically loaded content
    setTimeout(forceLoginCheck, 500);
    setTimeout(fixNavigationLinks, 500);
    
    // Listen for storage changes (if user logs in from another tab)
    window.addEventListener('storage', function(e) {
        if (e.key === 'currentUser' || e.key === 'authToken') {
            console.log('🔄 Storage changed, updating UI...');
            forceLoginCheck();
        }
    });
})();