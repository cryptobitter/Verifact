/**
 * Verifact Global Navbar Controller
 * Handles active route detection, keyboard accessibility, and responsive hamburger drawer.
 */
export function initGlobalNavbar() {
  const currentPath = window.location.pathname.toLowerCase();
  
  // 1. Determine active key from current URL
  let activeNav = 'overview';
  if (currentPath.includes('worklist') || currentPath.includes('findings') || currentPath.includes('sign-off')) {
    activeNav = 'worklist';
  } else if (currentPath.includes('upload') || currentPath.includes('privacy') || currentPath.includes('scan-in-progress')) {
    activeNav = 'intake';
  } else if (currentPath.includes('viewer')) {
    activeNav = 'viewer';
  } else if (currentPath.includes('analytics') || currentPath.includes('audit-log')) {
    activeNav = 'analytics';
  } else if (currentPath.includes('about') || currentPath.includes('how-it-works')) {
    activeNav = 'docs';
  }

  // 2. Set active states on desktop and mobile links
  const navLinks = document.querySelectorAll('.nav-link[data-nav]');
  navLinks.forEach(link => {
    const navKey = link.getAttribute('data-nav');
    if (navKey === activeNav) {
      link.setAttribute('aria-current', 'page');
      link.classList.add('nav-link-active');
    } else {
      link.removeAttribute('aria-current');
      link.classList.remove('nav-link-active');
    }
  });

  // 3. Hamburger Menu Toggle Logic
  const menuBtn = document.getElementById('mobile-menu-btn');
  const menuPanel = document.getElementById('mobile-menu-panel');
  const hamburgerIcon = document.getElementById('hamburger-icon');

  if (menuBtn && menuPanel) {
    // Toggle menu
    const toggleMenu = (open) => {
      const isExpanded = open !== undefined ? open : menuBtn.getAttribute('aria-expanded') === 'true';
      const newState = !isExpanded;
      
      menuBtn.setAttribute('aria-expanded', String(newState));
      if (newState) {
        menuPanel.classList.remove('hidden');
        if (hamburgerIcon) {
          hamburgerIcon.classList.remove('ph-list');
          hamburgerIcon.classList.add('ph-x');
        }
      } else {
        menuPanel.classList.add('hidden');
        if (hamburgerIcon) {
          hamburgerIcon.classList.remove('ph-x');
          hamburgerIcon.classList.add('ph-list');
        }
      }
    };

    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleMenu();
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menuBtn.getAttribute('aria-expanded') === 'true') {
        toggleMenu(false);
        menuBtn.focus();
      }
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (menuBtn.getAttribute('aria-expanded') === 'true' && !menuPanel.contains(e.target) && !menuBtn.contains(e.target)) {
        toggleMenu(false);
      }
    });

    // Close when mobile link is clicked
    menuPanel.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => toggleMenu(false));
    });
  }
}

// Auto-run if loaded as standard script
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobalNavbar);
  } else {
    initGlobalNavbar();
  }
}
