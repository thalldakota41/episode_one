(function() {

    // Search autocomplete
    const searchInput = $('#search');
    const searchResultsContainer = $('#search-results');

    searchInput.autocomplete({
        source: function(request, response) {
            const searchQuery = request.term.trim();

            if (searchQuery === '') {
                searchResultsContainer.empty();
                return;
            }

            $.ajax({
                url: '/search/',
                method: 'GET',
                data: { search: searchQuery },
                success: function(data) {
                    if (data.results.length > 0) {
                        const formattedResults = data.results.slice(0, 5).map(function(show) {
                            return {
                                label: show.title,
                                value: show.title,
                                poster: show.poster
                            };
                        });
                        response(formattedResults);
                    } else {
                        response([]);
                    }
                },
                error: function(error) {
                    console.error('Error:', error);
                    response([]);
                }
            });
        },

        create: function() {
            $(this).data('ui-autocomplete')._renderItem = function(ul, item) {
                const showHtml = `
                    <div class="show-result">
                        <img src="${item.poster}" alt="${item.label} Poster">
                        <h3>${item.label}</h3>
                    </div>
                `;
                return $('<li>').append(showHtml).appendTo(ul);
            };
        },

        minLength: 0
    });

    $('#search').keydown(function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            $('#search-form').submit();
        }
    });

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