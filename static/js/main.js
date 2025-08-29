/**
 * Main JavaScript file for optimized UI performance
 */

// Define performance metrics tracking
const PerfMetrics = {
    // Track page loading performance
    trackPageLoad: function () {
        if (window.performance && window.performance.timing) {
            window.addEventListener('load', function () {
                setTimeout(function () {
                    const timing = window.performance.timing;
                    const pageLoadTime = timing.loadEventEnd - timing.navigationStart;
                    console.log('Page load time: ' + pageLoadTime + 'ms');
                }, 0);
            });
        }
    },

    // Initialize performance tracking
    init: function () {
        this.trackPageLoad();
    }
};

// Lazy load images that are not in the viewport
const LazyLoader = {
    // Process all elements with data-src attribute
    processLazyElements: function () {
        const lazyImages = document.querySelectorAll('img[data-src]');

        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });

            lazyImages.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for browsers without IntersectionObserver
            lazyImages.forEach(img => {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            });
        }
    },

    // Initialize lazy loading
    init: function () {
        // Process immediately if DOM is already loaded
        if (document.readyState === 'complete') {
            this.processLazyElements();
        } else {
            // Otherwise wait for DOMContentLoaded
            window.addEventListener('DOMContentLoaded', () => {
                this.processLazyElements();
            });
        }
    }
};

// Responsive navbar handler
const NavbarHandler = {
    init: function () {
        // Handle navbar dropdown on smaller screens
        const navbarToggler = document.querySelector('.navbar-toggler');
        if (navbarToggler) {
            navbarToggler.addEventListener('click', function () {
                // Apply smooth animation for dropdown
                const navbarCollapse = document.querySelector('.navbar-collapse');
                if (navbarCollapse.classList.contains('show')) {
                    navbarCollapse.style.transition = 'height 0.3s ease';
                }
            });
        }
    }
};

// Initialize all modules when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    PerfMetrics.init();
    LazyLoader.init();
    NavbarHandler.init();
});
