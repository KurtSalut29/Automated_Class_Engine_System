/**
 * Global Dark Mode System
 * Include this file in ALL your HTML pages to enable system-wide dark mode
 * Place this in: static/scheduler/js/darkmode.js
 */

(function() {
    'use strict';

    // CRITICAL: Apply dark mode IMMEDIATELY before anything renders
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    
    if (isDarkMode) {
        // Apply to HTML first to prevent flash
        document.documentElement.classList.add('dark-mode');
        
        // Apply to body immediately if it exists
        if (document.body) {
            document.body.classList.add('dark-mode');
        }
    }

    // Also apply when DOM is ready (backup)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyDarkMode);
    } else {
        applyDarkMode();
    }

    function applyDarkMode() {
        const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
        
        if (darkModeEnabled) {
            document.body.classList.add('dark-mode');
            document.documentElement.classList.add('dark-mode');
            
            // Update toggle switch if it exists on current page
            const darkModeToggle = document.getElementById('darkModeToggle');
            if (darkModeToggle) {
                darkModeToggle.classList.add('active');
            }
            
            console.log('✅ Dark mode applied to this page');
        } else {
            console.log('☀️ Light mode active');
        }
    }

    // Listen for storage changes from other tabs/windows
    window.addEventListener('storage', function(e) {
        if (e.key === 'darkMode') {
            if (e.newValue === 'true') {
                document.body.classList.add('dark-mode');
                document.documentElement.classList.add('dark-mode');
                const toggle = document.getElementById('darkModeToggle');
                if (toggle) toggle.classList.add('active');
                console.log('✅ Dark mode enabled from another tab');
            } else {
                document.body.classList.remove('dark-mode');
                document.documentElement.classList.remove('dark-mode');
                const toggle = document.getElementById('darkModeToggle');
                if (toggle) toggle.classList.remove('active');
                console.log('☀️ Light mode enabled from another tab');
            }
        }
    });

    // Global toggle function
    window.toggleDarkMode = function() {
        const body = document.body;
        const html = document.documentElement;
        const toggle = document.getElementById('darkModeToggle');
        
        body.classList.toggle('dark-mode');
        html.classList.toggle('dark-mode');
        
        if (toggle) {
            toggle.classList.toggle('active');
        }
        
        // Save preference
        const isDark = body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark);
        
        // Dispatch custom event for other scripts to listen to
        const event = new CustomEvent('darkmodechange', { 
            detail: { isDarkMode: isDark } 
        });
        window.dispatchEvent(event);
        
        console.log('🌓 Dark mode:', isDark ? 'ON ✅' : 'OFF ☀️');
        console.log('localStorage value:', localStorage.getItem('darkMode'));
    };

    // Debug function - call this to check status
    window.checkDarkMode = function() {
        console.log('=== DARK MODE DEBUG ===');
        console.log('localStorage darkMode:', localStorage.getItem('darkMode'));
        console.log('body has dark-mode class:', document.body.classList.contains('dark-mode'));
        console.log('html has dark-mode class:', document.documentElement.classList.contains('dark-mode'));
        console.log('Current page:', window.location.pathname);
        console.log('=====================');
    };

})();