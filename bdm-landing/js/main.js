// MTS BDM Landing Page - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initNavigation();
    initScrollAnimations();
    initSearch();
    initFilterTabs();
    loadFeatures();
});

// Navigation scroll effect
function initNavigation() {
    const nav = document.querySelector('.nav');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
}

// Scroll animations with Intersection Observer
function initScrollAnimations() {
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // Observe all feature cards and sections
    document.querySelectorAll('.feature-card, .category-section').forEach(el => {
        el.classList.add('loading');
        observer.observe(el);
    });
}

// Search functionality
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        filterFeatures(searchTerm, null);
    });
}

// Filter tabs functionality
function initFilterTabs() {
    const tabs = document.querySelectorAll('.filter-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            tab.classList.add('active');
            
            const category = tab.dataset.category;
            const searchInput = document.getElementById('searchInput');
            const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
            
            filterFeatures(searchTerm, category);
        });
    });
}

// Filter features by search term and category
function filterFeatures(searchTerm, category) {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach(card => {
        const name = card.querySelector('.feature-name').textContent.toLowerCase();
        const description = card.querySelector('.feature-description').textContent.toLowerCase();
        const products = card.querySelector('.feature-products').textContent.toLowerCase();
        const cardCategory = card.dataset.category;
        
        const matchesSearch = !searchTerm || 
            name.includes(searchTerm) || 
            description.includes(searchTerm) || 
            products.includes(searchTerm);
        
        const matchesCategory = !category || category === 'all' || cardCategory === category;
        
        if (matchesSearch && matchesCategory) {
            card.style.display = 'block';
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 10);
        } else {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.display = 'none';
            }, 300);
        }
    });
}

// Load features from JSON and render
async function loadFeatures() {
    try {
        const response = await fetch('data/features.json');
        const data = await response.json();
        
        renderCategories(data);
        updateStats(data);
    } catch (error) {
        console.error('Error loading features:', error);
    }
}

// Render all categories and their features
function renderCategories(data) {
    const mainContent = document.getElementById('mainContent');
    if (!mainContent) return;

    const categoryIcons = getCategoryIcons();
    let globalFeatureIndex = 0;

    data.forEach((category, index) => {
        const section = document.createElement('section');
        section.className = 'category-section';
        section.id = `category-${index}`;
        
        const iconSvg = categoryIcons[category.category] || categoryIcons['default'];
        
        section.innerHTML = `
            <div class="category-header">
                <div class="category-icon">
                    ${iconSvg}
                </div>
                <h2 class="category-title">${escapeHtml(category.category)}</h2>
            </div>
            <div class="features-grid" id="grid-${index}"></div>
        `;
        
        mainContent.appendChild(section);
        
        const grid = section.querySelector(`#grid-${index}`);
        
        category.features.forEach(feature => {
            const card = document.createElement('div');
            card.className = 'feature-card loading';
            card.dataset.category = category.category;
            
            globalFeatureIndex++;
            
            card.innerHTML = `
                <span class="feature-number">${String(globalFeatureIndex).padStart(3, '0')}</span>
                <h3 class="feature-name">${escapeHtml(feature.name)}</h3>
                <p class="feature-description">${escapeHtml(feature.description)}</p>
                <div class="feature-products">
                    <span class="feature-products-label">Продукты:</span>
                    ${escapeHtml(feature.products)}
                </div>
            `;
            
            grid.appendChild(card);
        });
    });
    
    // Re-initialize scroll animations for new elements
    setTimeout(() => {
        initScrollAnimations();
    }, 100);
}

// Update statistics on hero section
function updateStats(data) {
    const totalFeatures = data.reduce((sum, cat) => sum + cat.features.length, 0);
    const totalCategories = data.length;
    
    const statNumber = document.querySelector('.stat-number');
    if (statNumber) {
        animateNumber(statNumber, 0, totalFeatures, 2000);
    }
    
    // Add more stats if elements exist
    const statItems = document.querySelectorAll('.stat-item');
    if (statItems[1]) {
        const catNumber = statItems[1].querySelector('.stat-number');
        if (catNumber) {
            animateNumber(catNumber, 0, totalCategories, 2000);
        }
    }
    
    if (statItems[2]) {
        const productsNumber = statItems[2].querySelector('.stat-number');
        if (productsNumber) {
            // Count unique products
            const allProducts = new Set();
            data.forEach(cat => {
                cat.features.forEach(f => {
                    f.products.split(',').forEach(p => {
                        allProducts.add(p.trim());
                    });
                });
            });
            animateNumber(productsNumber, 0, allProducts.size, 2000);
        }
    }
}

// Animate number counter
function animateNumber(element, start, end, duration) {
    const range = end - start;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(start + (range * easeOutQuart));
        
        element.textContent = current.toLocaleString('ru-RU');
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Get SVG icons for categories
function getCategoryIcons() {
    return {
        'АРХИТЕКТУРА И РАЗВЕРТЫВАНИЕ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
        `,
        'МОДЕЛИРОВАНИЕ ДАННЫХ И МЕТАДАННЫЕ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>
                <path d="M12 8v4M8.5 17.5L12 12l3.5 5.5"/>
            </svg>
        `,
        'ИНТЕГРАЦИЯ И ЗАГРУЗКА ДАННЫХ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
            </svg>
        `,
        'КАЧЕСТВО ДАННЫХ И СОПОСТАВЛЕНИЕ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
        `,
        'УПРАВЛЕНИЕ ПРОЦЕССАМИ И СТЬЮАРДСТВО': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12h6M12 9v6"/>
            </svg>
        `,
        'БЕЗОПАСНОСТЬ, КОМПЛАЕНС И АУДИТ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>
            </svg>
        `,
        'ПУБЛИКАЦИЯ, API И СОБЫТИЯ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 20V10M12 20V4M6 20v-6"/>
            </svg>
        `,
        'ИНТЕГРАЦИЯ, МОНИТОРИНГ И НАБЛЮДАЕМОСТЬ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 20V10M12 20V4M6 20v-6M2 12h20"/>
            </svg>
        `,
        'РАСШИРЯЕМОСТЬ И ЭКОСИСТЕМА': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
        `,
        'СПЕЦИАЛИЗИРОВАННЫЕ И ИССЛЕДОВАТЕЛЬСКИЕ ФУНКЦИИ': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>
            </svg>
        `,
        'default': `
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
        `
    };
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Smooth scroll to section
function scrollToSection(id) {
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Export for potential external use
window.bdmLanding = {
    filterFeatures,
    scrollToSection
};
