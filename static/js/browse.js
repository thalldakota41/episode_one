(function() {

    let currentPage = 1;
    let currentGenre = '';
    let currentSearch = '';
    let isLoading = false;
    let hasMore = true;
    let searchTimer = null;

    const grid = document.getElementById('browse-grid');
    const loading = document.getElementById('browse-loading');
    const endMessage = document.getElementById('browse-end');
    const resultsCount = document.getElementById('results-count');
    const scrollTrigger = document.getElementById('scroll-trigger');
    const searchInput = document.getElementById('browse-search-input');

    // Initial load
    loadShows(true);

    // Genre tag clicks
    document.querySelectorAll('.genre-tag').forEach(function(tag) {
        tag.addEventListener('click', function() {
            document.querySelectorAll('.genre-tag').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentGenre = this.dataset.genre;
            currentSearch = searchInput.value.trim();
            resetAndLoad();
        });
    });

    // Search input — real time AJAX with debounce
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {
            currentSearch = searchInput.value.trim();
            resetAndLoad();
        }, 300);
    });

    // Infinite scroll using Intersection Observer
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting && !isLoading && hasMore) {
                loadShows(false);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px 200px 0px'
    });

    observer.observe(scrollTrigger);

    function resetAndLoad() {
        currentPage = 1;
        hasMore = true;
        grid.innerHTML = '';
        endMessage.classList.remove('active');
        loadShows(true);
    }

    function loadShows(reset) {
        if (isLoading) return;
        isLoading = true;
        loading.classList.add('active');

        const params = new URLSearchParams({
            page: currentPage,
            genre: currentGenre,
            search: currentSearch,
        });

        fetch(`/browse/shows/?${params.toString()}`)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                isLoading = false;
                loading.classList.remove('active');

                // Update results count
                if (currentPage === 1) {
                    const genreText = currentGenre ? ` in <strong>${currentGenre}</strong>` : '';
                    const searchText = currentSearch ? ` for "<strong>${currentSearch}</strong>"` : '';
                    resultsCount.innerHTML = `Showing <strong>${data.total}</strong> pilots${genreText}${searchText}`;
                }

                // Render cards
                data.results.forEach(function(show, index) {
                    const card = createCard(show, index);
                    grid.appendChild(card);
                });

                // Update state
                hasMore = data.has_more;
                if (hasMore) {
                    currentPage++;
                } else {
                    if (data.total > 0) {
                        endMessage.classList.add('active');
                    }
                }

                // No results
                if (data.total === 0) {
                    grid.innerHTML = '<p class="browse-no-results">No pilots found. Try a different genre or search term.</p>';
                }
            })
            .catch(function(error) {
                console.error('Error loading shows:', error);
                isLoading = false;
                loading.classList.remove('active');
            });
    }

    function createCard(show, index) {
        const card = document.createElement('a');
        card.href = `/show_page/${show.id}/`;
        card.className = 'browse-card';
        card.style.animationDelay = `${(index % 24) * 0.03}s`;

        const creatorName = show.creators.length > 0 ? show.creators[0].name : '';

        if (show.poster) {
            card.innerHTML = `
                <img src="${show.poster}" alt="${show.title} Poster" loading="lazy">
                <div class="browse-card-overlay">
                    <p class="browse-card-title">${show.title}</p>
                    ${creatorName ? `<p class="browse-card-creator">${creatorName}</p>` : ''}
                </div>
            `;
        } else {
            card.innerHTML = `
                <div class="browse-card-no-image">
                    <p>Coming Soon</p>
                </div>
                <div class="browse-card-overlay">
                    <p class="browse-card-title">${show.title}</p>
                    ${creatorName ? `<p class="browse-card-creator">${creatorName}</p>` : ''}
                </div>
            `;
        }

        return card;
    }

})();