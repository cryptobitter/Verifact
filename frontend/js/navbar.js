/**
 * Verifact Global Navbar Controller
 * Handles active route detection, user identity sync, authenticated vs unauthenticated states,
 * and responsive hamburger drawer.
 */

function getInitials(name) {
  if (!name) return 'DR';
  const clean = name.replace(/^Dr\.\s*/i, '').trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'DR';
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatRole(role) {
  if (!role) return 'Attending Radiologist';
  const r = role.toLowerCase();
  if (r === 'radiologist') return 'Attending Radiologist';
  if (r === 'resident') return 'Radiology Resident';
  if (r === 'admin') return 'System Administrator';
  return role.charAt(0).toUpperCase() + role.slice(1);
}

export function isUserLoggedIn() {
  return !!sessionStorage.getItem('verifact_user') || !!sessionStorage.getItem('verifact_token');
}

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
  } else if (currentPath.includes('profile')) {
    activeNav = 'profile';
  }

  // 2. Set active states on desktop and mobile links
  const navLinks = document.querySelectorAll('.nav-link[data-nav]');
  navLinks.forEach(link => {
    const navKey = link.getAttribute('data-nav');
    if (navKey === activeNav) {
      link.setAttribute('aria-current', 'page');
      link.classList.add('nav-link-active');
      link.style.color = '#C8512D';
      link.style.borderBottom = '2px solid #C8512D';
    } else {
      link.removeAttribute('aria-current');
      link.classList.remove('nav-link-active');
      link.style.borderBottom = 'none';
    }
  });

  // 3. User Identity & Dropdown Enhancement
  syncUserIdentity();
  setupUserDropdown();

  // 4. Hamburger Menu Toggle Logic
  setupMobileMenu();
}

function syncUserIdentity() {
  let user = null;
  try {
    const raw = sessionStorage.getItem('verifact_user');
    if (raw) user = JSON.parse(raw);
  } catch (e) {}

  if (!user) return; // If logged out, setupUserDropdown handles rendering Sign In buttons

  const fullName = user.full_name || 'Dr. Elena Vance';
  const roleDisplay = formatRole(user.role);
  const emailDisplay = user.email || 'e.vance@stanford.edu';
  const initials = getInitials(fullName);

  // Desktop avatar & labels
  const avatarEls = document.querySelectorAll('#nav-user-avatar, .nav-user-avatar');
  avatarEls.forEach(el => { el.textContent = initials; el.setAttribute('title', fullName); });

  const nameEls = document.querySelectorAll('#nav-user-name, .nav-user-name');
  nameEls.forEach(el => { el.textContent = fullName; el.setAttribute('title', fullName); });

  const roleEls = document.querySelectorAll('#nav-user-role, .nav-user-role');
  roleEls.forEach(el => { el.textContent = roleDisplay; el.setAttribute('title', roleDisplay); });

  // Dropdown header
  const dropName = document.getElementById('dropdown-user-name');
  if (dropName) dropName.textContent = fullName;
  const dropEmail = document.getElementById('dropdown-user-email');
  if (dropEmail) dropEmail.textContent = emailDisplay;

  // Mobile drawer avatar & labels
  const mobAvatar = document.getElementById('mobile-nav-user-avatar');
  if (mobAvatar) mobAvatar.textContent = initials;
  const mobName = document.getElementById('mobile-nav-user-name');
  if (mobName) mobName.textContent = fullName;
  const mobRole = document.getElementById('mobile-nav-user-role');
  if (mobRole) mobRole.textContent = roleDisplay;
}

function setupUserDropdown() {
  let user = null;
  try {
    const raw = sessionStorage.getItem('verifact_user');
    if (raw) user = JSON.parse(raw);
  } catch(e) {}

  const headerRight = document.querySelector('#global-navbar .flex.items-center.gap-2, #global-navbar .flex.items-center.gap-3');
  if (!headerRight) return;

  // Locate the user block or previous auth buttons container
  let container = document.getElementById('user-menu-container') || document.getElementById('nav-logged-out-container');

  if (!user) {
    // --- LOGGED OUT STATE ---
    // If user block exists, replace it with clean "Sign in" & "Create account" actions
    if (!document.getElementById('nav-logged-out-container')) {
      const existingUserBlock = Array.from(headerRight.children).find(child => 
        child.id === 'user-menu-container' || (child.querySelector('.rounded-full') && !child.tagName.toLowerCase().includes('a') && !child.tagName.toLowerCase().includes('button'))
      );

      const authBlock = document.createElement('div');
      authBlock.id = 'nav-logged-out-container';
      authBlock.className = 'flex items-center gap-2';
      authBlock.innerHTML = `
        <a href="/login.html" class="px-3 py-1.5 rounded-lg border border-[#EADFD3] hover:border-[#C8512D] text-[#1F1612] hover:text-[#C8512D] hover:bg-[#FAF6F1] text-xs sm:text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8512D]">
          Sign in
        </a>
        <a href="/signup.html" class="hidden sm:inline-flex px-3 py-1.5 rounded-lg bg-[#C8512D] hover:bg-[#B04624] text-white text-xs sm:text-sm font-semibold transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8512D]">
          Create account
        </a>
      `;

      if (existingUserBlock) {
        existingUserBlock.replaceWith(authBlock);
      } else {
        headerRight.insertBefore(authBlock, headerRight.firstChild);
      }
    }
    return;
  }

  // --- LOGGED IN STATE ---
  const fullName = user.full_name || 'Dr. Elena Vance';
  const roleDisplay = formatRole(user.role);
  const emailDisplay = user.email || 'e.vance@stanford.edu';
  const initials = getInitials(fullName);

  const loggedOutBlock = document.getElementById('nav-logged-out-container');
  if (loggedOutBlock) {
    const wrapper = document.createElement('div');
    wrapper.className = 'relative';
    wrapper.id = 'user-menu-container';
    loggedOutBlock.replaceWith(wrapper);
    container = wrapper;
  } else if (!container) {
    const existingUserBlock = Array.from(headerRight.children).find(child => 
      child.querySelector('.rounded-full') && !child.tagName.toLowerCase().includes('a') && !child.tagName.toLowerCase().includes('button')
    );
    if (existingUserBlock) {
      const wrapper = document.createElement('div');
      wrapper.className = 'relative';
      wrapper.id = 'user-menu-container';
      existingUserBlock.replaceWith(wrapper);
      container = wrapper;
    }
  }

  if (container) {
    container.innerHTML = `
      <button id="user-menu-btn" type="button" aria-expanded="false" aria-haspopup="true" class="flex items-center gap-2.5 pl-2 py-1 pr-1.5 rounded-lg hover:bg-[#FAF6F1] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8512D]">
        <div id="nav-user-avatar" class="w-9 h-9 rounded-full bg-[#FBE3D6] border border-[#EADFD3] text-[#C8512D] font-semibold text-xs flex items-center justify-center shrink-0 shadow-inner" title="${fullName}">
          ${initials}
        </div>
        <div class="hidden xl:flex flex-col text-left max-w-[140px]">
          <span id="nav-user-name" class="text-sm font-semibold text-[#1F1612] truncate leading-tight" title="${fullName}">${fullName}</span>
          <span id="nav-user-role" class="text-[12px] text-[#6B5B52] truncate leading-tight" title="${roleDisplay}">${roleDisplay}</span>
        </div>
        <svg class="w-3.5 h-3.5 text-[#6B5B52] hidden xl:inline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
      </button>
      <div id="user-menu-dropdown" class="hidden absolute right-0 mt-2 w-56 bg-white rounded-xl border border-[#EADFD3] shadow-[0_4px_20px_rgba(58,31,20,0.12)] py-1.5 z-50">
        <div class="px-4 py-2 border-b border-[#EADFD3]">
          <div id="dropdown-user-name" class="text-xs font-semibold text-[#1F1612] truncate">${fullName}</div>
          <div id="dropdown-user-email" class="text-[11px] text-[#6B5B52] truncate">${emailDisplay}</div>
        </div>
        <a href="/profile.html" class="flex items-center gap-2.5 px-4 py-2 text-sm text-[#1F1612] hover:text-[#C8512D] hover:bg-[#FFF4E8] transition-colors">
          <svg class="w-4 h-4 text-[#C8512D]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
          <span>My Profile</span>
        </a>
        <button type="button" id="signout-btn" class="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-[#D92D20] hover:bg-[#FDE8E8] transition-colors text-left">
          <svg class="w-4 h-4 text-[#D92D20]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
          <span>Sign out</span>
        </button>
      </div>
    `;

    const btn = container.querySelector('#user-menu-btn');
    const dropdown = container.querySelector('#user-menu-dropdown');

    if (btn && dropdown) {
      const toggleDropdown = (open) => {
        const isExpanded = open !== undefined ? open : btn.getAttribute('aria-expanded') === 'true';
        const newState = !isExpanded;
        btn.setAttribute('aria-expanded', String(newState));
        if (newState) {
          dropdown.classList.remove('hidden');
        } else {
          dropdown.classList.add('hidden');
        }
      };

      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown();
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') {
          toggleDropdown(false);
          btn.focus();
        }
      });

      document.addEventListener('click', (e) => {
        if (btn.getAttribute('aria-expanded') === 'true' && !container.contains(e.target)) {
          toggleDropdown(false);
        }
      });
    }

    const signoutBtn = container.querySelector('#signout-btn');
    if (signoutBtn) {
      signoutBtn.addEventListener('click', () => {
        if (typeof window.authLogout === 'function') {
          window.authLogout();
        } else {
          sessionStorage.clear();
          localStorage.removeItem('verifact_token');
          window.location.href = '/login.html';
        }
      });
    }
  }
}

function setupMobileMenu() {
  const menuBtn = document.getElementById('mobile-menu-btn');
  const menuPanel = document.getElementById('mobile-menu-panel');
  const hamburgerIcon = document.getElementById('hamburger-icon');

  if (menuBtn && menuPanel) {
    let user = null;
    try {
      const raw = sessionStorage.getItem('verifact_user');
      if (raw) user = JSON.parse(raw);
    } catch(e) {}

    // Check if mobile panel footer exists; if so, replace or initialize it
    let mobileFooter = menuPanel.querySelector('.mobile-auth-footer');
    if (!mobileFooter) {
      mobileFooter = document.createElement('div');
      mobileFooter.className = 'mobile-auth-footer mt-4 pt-3 border-t border-[#EADFD3] flex flex-col gap-2.5';
      menuPanel.appendChild(mobileFooter);
    }

    if (!user) {
      mobileFooter.innerHTML = `
        <a href="/login.html" class="w-full flex items-center justify-center py-2 px-3 rounded-lg border border-[#C8512D] text-[#C8512D] hover:bg-[#FBE3D6] text-sm font-semibold transition-colors">
          Sign in
        </a>
        <a href="/signup.html" class="w-full flex items-center justify-center py-2 px-3 rounded-lg bg-[#C8512D] hover:bg-[#B04624] text-white text-sm font-semibold transition-colors shadow-sm">
          Create account
        </a>
      `;
    } else {
      const fullName = user.full_name || 'Dr. Elena Vance';
      const roleDisplay = formatRole(user.role);
      const initials = getInitials(fullName);

      mobileFooter.innerHTML = `
        <a href="/profile.html" class="flex items-center justify-between p-2 rounded-lg hover:bg-[#FFF4E8] transition-colors">
          <div class="flex items-center gap-2">
            <div id="mobile-nav-user-avatar" class="w-8 h-8 rounded-full bg-[#FBE3D6] border border-[#EADFD3] text-[#C8512D] font-semibold text-xs flex items-center justify-center">
              ${initials}
            </div>
            <div class="flex flex-col">
              <span id="mobile-nav-user-name" class="text-xs font-semibold text-[#1F1612]">${fullName}</span>
              <span id="mobile-nav-user-role" class="text-[11px] text-[#6B5B52]">${roleDisplay}</span>
            </div>
          </div>
          <span class="text-xs text-[#C8512D] font-semibold">My Profile &rarr;</span>
        </a>
        <button type="button" id="mobile-signout-btn" class="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-[#D92D20]/30 text-[#D92D20] hover:bg-[#FDE8E8] text-xs font-semibold transition-colors">
          <span>Sign out</span>
        </button>
      `;

      const mobSignoutBtn = mobileFooter.querySelector('#mobile-signout-btn');
      if (mobSignoutBtn) {
        mobSignoutBtn.addEventListener('click', () => {
          if (typeof window.authLogout === 'function') {
            window.authLogout();
          } else {
            sessionStorage.clear();
            localStorage.removeItem('verifact_token');
            window.location.href = '/login.html';
          }
        });
      }
    }

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

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menuBtn.getAttribute('aria-expanded') === 'true') {
        toggleMenu(false);
        menuBtn.focus();
      }
    });

    document.addEventListener('click', (e) => {
      if (menuBtn.getAttribute('aria-expanded') === 'true' && !menuPanel.contains(e.target)) {
        toggleMenu(false);
      }
    });

    menuPanel.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => toggleMenu(false));
    });
  }
}

// Auto-run if loaded as standard script or module
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobalNavbar);
  } else {
    initGlobalNavbar();
  }
}
