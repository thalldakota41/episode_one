(function() {

    const searchInput = document.getElementById('search');
    const searchForm = document.getElementById('search-form');
    const searchResults = document.getElementById('search-results');

    if (!searchInput) return;

    let debounceTimer = null;
    let currentResults = [];
    let selectedIndex = -1;

    // Listen for input
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        clearTimeout(debounceTimer);

        if (query.length === 0) {
            closeDropdown();
            return;
        }

        debounceTimer = setTimeout(function() {
            fetchResults(query);
        }, 150);
    });

    // Keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
        if (!searchResults.classList.contains('active')) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
            updateHighlight();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateHighlight();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && currentResults[selectedIndex]) {
                navigateToShow(currentResults[selectedIndex]);
            } else {
                searchForm.submit();
            }
        } else if (e.key === 'Escape') {
            closeDropdown();
            searchInput.blur();
        }
    });

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!searchForm.contains(e.target)) {
            closeDropdown();
        }
    });

    function fetchResults(query) {
        fetch(`/search/?search=${encodeURIComponent(query)}`, {
            headers: { 'x-requested-with': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            currentResults = data.results.slice(0, 6);
            selectedIndex = -1;
            renderDropdown(currentResults, query);
        })
        .catch(() => closeDropdown());
    }

    function renderDropdown(results, query) {
        searchResults.innerHTML = '';

        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="search-no-results">
                    No pilots found for <em>"${query}"</em>
                </div>
            `;
            searchResults.classList.add('active');
            return;
        }

        results.forEach(function(show, index) {
            const item = document.createElement('a');
            item.href = `/show_page/${show.id}/`;
            item.className = 'search-result-item';
            item.dataset.index = index;

            item.innerHTML = `
                <div class="search-result-poster">
                    ${show.poster
                        ? `<img src="${show.poster}" alt="${show.title}">`
                        : `<div class="search-result-no-poster"></div>`
                    }
                </div>
                <div class="search-result-info">
                    <span class="search-result-title">${show.title}</span>
                    ${show.creators && show.creators.length > 0
                        ? `<span class="search-result-creator">${show.creators.map(c => c.name).join(', ')}</span>`
                        : ''
                    }
                </div>
                <div class="search-result-arrow">→</div>
            `;

            item.addEventListener('mouseenter', function() {
                selectedIndex = index;
                updateHighlight();
            });

            searchResults.appendChild(item);
        });

        // View all results footer
        const footer = document.createElement('div');
        footer.className = 'search-results-footer';
        footer.innerHTML = `<span>Press Enter to see all results for "<strong>${query}</strong>"</span>`;
        searchResults.appendChild(footer);

        searchResults.classList.add('active');
    }

    function updateHighlight() {
        const items = searchResults.querySelectorAll('.search-result-item');
        items.forEach(function(item, i) {
            item.classList.toggle('highlighted', i === selectedIndex);
        });
    }

    function navigateToShow(show) {
        window.location.href = `/show_page/${show.id}/`;
    }

    function closeDropdown() {
        searchResults.innerHTML = '';
        searchResults.classList.remove('active');
        selectedIndex = -1;
        currentResults = [];
    }

})();

// Scroll animations using Intersection Observer
document.addEventListener('DOMContentLoaded', function() {
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px 0px 0px'
    });

    document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right, .pop-in').forEach(function(el) {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom >= 0) {
            el.classList.add('visible');
        } else {
            observer.observe(el);
        }
    });

    // Back to top button
    window.addEventListener('scroll', function() {
        const backToTop = document.getElementById('back-to-top');
        if (window.scrollY > 500) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
    });
});