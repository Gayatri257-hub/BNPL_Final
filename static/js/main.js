/**
 * SmartPay — Global JS Utilities
 * Cart updater, flash dismiss, smooth scroll, active nav highlighter
 */

document.addEventListener('DOMContentLoaded', function () {

  // 1. CART COUNT UPDATER
  // Fetch cart count from server and update navbar badge
  const cartBadge = document.getElementById('cartCount');
  if (cartBadge) {
    fetch('/api/cart-count', { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && data.count !== undefined) {
          cartBadge.textContent = data.count;
          cartBadge.style.display = data.count > 0 ? 'flex' : 'none';
        }
      })
      .catch(() => { /* silently fail — session count already rendered server-side */ });
  }

  // 2. FLASH MESSAGE AUTO-DISMISS
  const flashMessages = document.querySelectorAll('.flash');
  flashMessages.forEach(flash => {
    // Auto-remove after 4 seconds
    setTimeout(() => {
      flash.style.transition = 'opacity .4s, transform .4s';
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-8px)';
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  });

  // 3. SMOOTH SCROLL FOR ANCHOR LINKS
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const navHeight = document.querySelector('.navbar')?.offsetHeight || 70;
        const targetTop = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 16;
        window.scrollTo({ top: targetTop, behavior: 'smooth' });
      }
    });
  });

  // 4. ACTIVE NAV LINK HIGHLIGHTER
  // Highlights the nav link whose href matches the current URL path
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(link => {
    const linkPath = link.getAttribute('href');
    if (linkPath && linkPath !== '/' && currentPath.startsWith(linkPath)) {
      link.classList.add('active');
      link.style.color = 'var(--primary-dark)';
    } else if (linkPath === '/' && currentPath === '/') {
      link.classList.add('active');
      link.style.color = 'var(--primary-dark)';
    }
  });

});
