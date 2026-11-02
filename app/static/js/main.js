/**
 * TindaMind - Client-Side Shell Controller
 * Handles mobile sidebar drawer transitions and flash message auto-dismissal.
 */

document.addEventListener('DOMContentLoaded', function () {
    // ----------------------------------------------------
    // 1. Mobile Navigation Sidebar Drawer Toggle
    // ----------------------------------------------------
    const sidebar = document.getElementById('app-sidebar');
    const toggleBtn = document.getElementById('mobile-sidebar-toggle');
    const closeBtn = document.getElementById('mobile-sidebar-close');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');

    function openSidebar() {
        if (sidebar && backdrop) {
            sidebar.classList.remove('-translate-x-full');
            sidebar.classList.add('translate-x-0');
            backdrop.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
        }
    }

    function closeSidebar() {
        if (sidebar && backdrop) {
            sidebar.classList.remove('translate-x-0');
            sidebar.classList.add('-translate-x-full');
            backdrop.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', openSidebar);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeSidebar);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    // ----------------------------------------------------
    // 2. Flash Message Auto-Dismissal (4 Seconds)
    // ----------------------------------------------------
    const alertItems = document.querySelectorAll('.flash-alert-item');
    alertItems.forEach(function (alertElement) {
        setTimeout(function () {
            alertElement.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alertElement.style.opacity = '0';
            alertElement.style.transform = 'translateY(-8px)';
            setTimeout(function () {
                alertElement.remove();
            }, 500);
        }, 4000);
    });
});