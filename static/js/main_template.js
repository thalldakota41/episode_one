(function() {

    const searchInput = document.getElementById('search');
    const searchForm = document.getElementById('search-form');
    const searchResults = document.getElementById('search-results');

    // Mobile elements
    const mobileSearchToggle = document.getElementById('mobile-search-toggle');
    const mobileSearchBar = document.getElementById('mobile-search-bar');
    const mobileSearchInput = document.getElementById('mobile-search-input');
    const mobileSearchClose = document.getElementById('mobile-search-close');
    const mobileSearchResults = document.getElementById('mobile-search-results');
    const mobileNavDropdown = document.getElementById('mobile-nav-dropdown');
    const hamburger = document.querySelector('.navbar-toggler');

    // ---- DESKTOP SEARCH ----
    if (searchInput) {
        let debounceTimer = null;
        let currentResults = [];
        let selectedIndex = -1;

        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            clearTimeout(debounceTimer);
            if (query.length === 0) { closeDropdown(); return; }
            debounceTimer = setTimeout(function() {
                fetchResults(query, searchResults, currentResults);
            }, 150);
        });

        searchInput.addEventListener('keydown', function(e) {
            if (!searchResults.classList.contains('active')) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
                updateHighlight(searchResults, selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateHighlight(searchResults, selectedIndex);
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

        document.addEventListener('click', function(e) {
            if (searchForm && !searchForm.contains(e.target)) closeDropdown();
        });

        function closeDropdown() {
            searchResults.innerHTML = '';
            searchResults.classList.remove('active');
            selectedIndex = -1;
            currentResults = [];
        }
    }

    // ---- MOBILE HAMBURGER ----
    if (hamburger && mobileNavDropdown) {
        hamburger.addEventListener('click', function() {
            mobileNavDropdown.classList.toggle('open');
            // Close search if open
            if (mobileSearchBar) {
                mobileSearchBar.style.display = 'none';
                closeMobileDropdown();
            }
        });
    }

    // ---- MOBILE SEARCH ----
    if (mobileSearchToggle) {
        let mobileDebounceTimer = null;
        let mobileCurrentResults = [];
        let mobileSelectedIndex = -1;

        mobileSearchToggle.addEventListener('click', function() {
            if (mobileSearchBar.style.display === 'block') {
                mobileSearchBar.style.display = 'none';
                mobileSearchInput.value = '';
                closeMobileDropdown();
            } else {
                mobileSearchBar.style.display = 'block';
                // Close hamburger if open
                if (mobileNavDropdown) mobileNavDropdown.classList.remove('open');
                setTimeout(function() { mobileSearchInput.focus(); }, 50);
            }
        });

        mobileSearchClose.addEventListener('click', function() {
            mobileSearchBar.style.display = 'none';
            mobileSearchInput.value = '';
            closeMobileDropdown();
        });

        mobileSearchInput.addEventListener('input', function() {
            const query = this.value.trim();
            clearTimeout(mobileDebounceTimer);
            if (query.length === 0) { closeMobileDropdown(); return; }
            mobileDebounceTimer = setTimeout(function() {
                fetchResults(query, mobileSearchResults, mobileCurrentResults);
            }, 150);
        });

        mobileSearchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (mobileSelectedIndex >= 0 && mobileCurrentResults[mobileSelectedIndex]) {
                    navigateToShow(mobileCurrentResults[mobileSelectedIndex]);
                } else {
                    window.location.href = '/search/?search=' + encodeURIComponent(mobileSearchInput.value);
                }
            } else if (e.key === 'Escape') {
                mobileSearchBar.style.display = 'none';
                closeMobileDropdown();
            }
        });

        document.addEventListener('click', function(e) {
            if (mobileSearchBar &&
                mobileSearchBar.style.display === 'block' &&
                !mobileSearchBar.contains(e.target) &&
                !mobileSearchToggle.contains(e.target)) {
                mobileSearchBar.style.display = 'none';
                closeMobileDropdown();
            }
        });

        function closeMobileDropdown() {
            if (mobileSearchResults) {
                mobileSearchResults.innerHTML = '';
                mobileSearchResults.classList.remove('active');
            }
            mobileSelectedIndex = -1;
            mobileCurrentResults = [];
        }
    }

    // ---- SHARED FETCH + RENDER ----
    function fetchResults(query, resultsContainer, resultsArray) {
        fetch(`/search/?search=${encodeURIComponent(query)}`, {
            headers: { 'x-requested-with': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            resultsArray.length = 0;
            data.results.slice(0, 6).forEach(r => resultsArray.push(r));
            renderDropdown(resultsArray, query, resultsContainer);
        })
        .catch(() => {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.remove('active');
        });
    }

    function renderDropdown(results, query, container) {
        container.innerHTML = '';

        if (results.length === 0) {
            container.innerHTML = `<div class="search-no-results">No pilots found for <em>"${query}"</em></div>`;
            container.classList.add('active');
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
                updateHighlight(container, index);
            });

            container.appendChild(item);
        });

        const footer = document.createElement('div');
        footer.className = 'search-results-footer';
        footer.innerHTML = `<span>Press Enter to see all results for "<strong>${query}</strong>"</span>`;
        container.appendChild(footer);
        container.classList.add('active');
    }

    function updateHighlight(container, index) {
        const items = container.querySelectorAll('.search-result-item');
        items.forEach(function(item, i) {
            item.classList.toggle('highlighted', i === index);
        });
    }

    function navigateToShow(show) {
        window.location.href = `/show_page/${show.id}/`;
    }

})();

// Scroll animations
document.addEventListener('DOMContentLoaded', function() {
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right, .pop-in').forEach(function(el) {
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom >= 0) {
            el.classList.add('visible');
        } else {
            observer.observe(el);
        }
    });

    // Back to top
    window.addEventListener('scroll', function() {
        const backToTop = document.getElementById('back-to-top');
        if (window.scrollY > 500) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
    });
});