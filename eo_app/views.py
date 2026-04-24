from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import requests
import threading
from .models import Creator, Tag, Show, Comment, StaffFavorite, CreatorOfTheMonth, InfluentialShow, FeaturedShow, Article
from django.db.models import Count, Q, F, Max, ExpressionWrapper
from django.core.paginator import Paginator
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
from .forms import CommentForm
from django.core.mail import send_mail
from django.core.cache import cache
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import os

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "default_email@example.com")
api_key = os.environ.get('API_KEY')


def main(request):
    pk = Show.objects.all()
    return render(request, 'main.html', {'pk': pk})


def _get_staff_favorites():
    return StaffFavorite.objects.select_related('show').prefetch_related('show__creators').all()[:10]


def get_featured_show():
    from django.utils import timezone
    today = timezone.now().date()

    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    active_featured = FeaturedShow.objects.filter(
        featured_date__gte=week_start,
        is_active=True
    ).select_related('show').first()

    if active_featured:
        return active_featured.show

    recently_featured_ids = FeaturedShow.objects.order_by(
        '-featured_date'
    ).values_list('show_id', flat=True)[:20]

    candidate = Show.objects.exclude(
        id__in=recently_featured_ids
    ).filter(
        tmdb_poster_path__isnull=False
    ).order_by('?').first()

    if not candidate:
        candidate = Show.objects.filter(
            tmdb_poster_path__isnull=False
        ).order_by('?').first()

    if candidate:
        FeaturedShow.objects.filter(is_active=True).update(is_active=False)
        FeaturedShow.objects.create(show=candidate, is_active=True)
        return candidate

    return None


def all_staff_favorites(request):
    staff_favorites = StaffFavorite.objects.select_related('show').prefetch_related('show__creators').all()
    return render(request, 'all_staff_favorites.html', {'staff_favorites': staff_favorites})


def get_creators_of_the_month():
    creators_with_shows = Creator.objects.annotate(
        show_count=Count('shows')
    ).filter(show_count__gt=0)

    pool = list(creators_with_shows)

    if len(pool) < 10:
        random_creators = pool
    else:
        random_creators = random.sample(pool, 10)

    result = []
    for creator_obj in random_creators:
        if creator_obj.tmdb_profile_path:
            creator_image_url = f"https://image.tmdb.org/t/p/w500/{creator_obj.tmdb_profile_path}"
            has_image = True
        elif creator_obj.image:
            creator_image_url = creator_obj.image.url
            has_image = True
        else:
            creator_image_url = None
            has_image = False

        class CreatorDisplay:
            pass

        cotm = CreatorDisplay()
        cotm.creator_id = creator_obj.id
        cotm.creator_image = creator_image_url
        cotm.has_image = has_image
        cotm.creator_name = creator_obj.name
        cotm.current_scripts = creator_obj.shows.all()
        result.append(cotm)

    return result


def index(request):
    search_query = request.GET.get('search')
    shows = Show.objects.all().order_by('-created').prefetch_related('creators', 'tags')[:10]

    if search_query:
        shows = Show.objects.filter(
            Q(creators__name__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(tags__genre__icontains=search_query)
        ).distinct().prefetch_related('creators', 'tags')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        results = []
        for show in shows[:6]:
            results.append({
                'id': show.id,
                'title': show.title,
                'poster': f"https://image.tmdb.org/t/p/w500/{show.tmdb_poster_path}" if show.tmdb_poster_path else None,
                'creators': [{'id': c.id, 'name': c.name} for c in show.creators.all()],
            })
        return JsonResponse({'results': results})

    staff_favorites = _get_staff_favorites()
    creators_of_the_month = get_creators_of_the_month()
    featured_show = get_featured_show()
    influential_shows = InfluentialShow.objects.select_related('show').prefetch_related('show__creators', 'show__tags').all()[:10]

    return render(request, 'index.html', {
        'shows': shows,
        'staff_favorites': staff_favorites,
        'creators_of_the_month': creators_of_the_month,
        'influential_shows': influential_shows,
        'featured_show': featured_show,
    })


def search(request):
    search_query = request.GET.get('search')
    shows = Show.objects.all().order_by('title')

    if search_query:
        shows = shows.filter(
            Q(title__icontains=search_query) |
            Q(creators__name__icontains=search_query) |
            Q(tags__genre__icontains=search_query)
        ).distinct().order_by('title')

    shows = shows.prefetch_related('creators', 'tags')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        results = []
        for show in shows[:6]:
            results.append({
                'id': show.id,
                'title': show.title,
                'poster': f"https://image.tmdb.org/t/p/w500/{show.tmdb_poster_path}" if show.tmdb_poster_path else None,
                'creators': [{'id': c.id, 'name': c.name} for c in show.creators.all()],
            })
        return JsonResponse({'results': results})

    paginate_by = 15
    shows_page = paginate_shows(request, shows, paginate_by)

    context = {
        'search_term': search_query,
        'results': shows_page,
    }
    return render(request, 'search_results.html', context)


def paginate_shows(request, shows, paginate_by):
    paginator = Paginator(shows, paginate_by)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def rest_of_influential_shows(request):
    influential_shows = InfluentialShow.objects.select_related('show').prefetch_related('show__creators').all()
    return render(request, 'influential_shows.html', {'influential_shows': influential_shows})


def creator_page(request, id):
    creator_obj = get_object_or_404(Creator, id=id)

    if creator_obj.tmdb_profile_path:
        creator_image_url = f"https://image.tmdb.org/t/p/w500/{creator_obj.tmdb_profile_path}"
        has_image = True
    elif creator_obj.image:
        creator_image_url = creator_obj.image.url
        has_image = True
    else:
        creator_image_url = None
        has_image = False

    similar_creators = list(
        Creator.objects.annotate(
            matching_tags=Count('shows__tags', filter=Q(shows__tags__in=creator_obj.shows.values('tags')))
        ).exclude(id=creator_obj.id).order_by('-matching_tags')
    )

    if creator_obj.gender == 'F':
        female_creators = [c for c in similar_creators if c.gender == 'F']
        other_creators = [c for c in similar_creators if c.gender == 'O']
        male_creators = [c for c in similar_creators if c.gender == 'M']

        weighted_pool = (female_creators * 3) + (other_creators * 2) + male_creators
        random.shuffle(weighted_pool)

        seen = set()
        similar_creators = []
        for c in weighted_pool:
            if c.id not in seen:
                seen.add(c.id)
                similar_creators.append(c)
    else:
        random.shuffle(similar_creators)

    similar_creators = similar_creators[:10]

    recom_creators = {}
    for c in similar_creators:
        recom_creators[c.id] = {
            'name': c.name,
            'profile_path': c.tmdb_profile_path,
            'creator_obj': c,
            'has_image': bool(c.tmdb_profile_path or c.image),
        }

    show_data_list = []
    for show in creator_obj.shows.all():
        poster_url = (
            f"https://image.tmdb.org/t/p/w500/{show.tmdb_poster_path}"
            if show.tmdb_poster_path
            else "/static/images/default_creator_image.jpg"
        )
        show_data_list.append({'id': show.id, 'show': show.title, 'poster_url': poster_url})

    context = {
        "creator": creator_obj,
        "creator_info": {'biography': creator_obj.tmdb_biography},
        "creator_image": creator_image_url,
        "has_image": has_image,
        "recom_creators": recom_creators,
        "show_data_list": show_data_list,
    }
    return render(request, "creator_page.html", context)


def show_page(request, id):
    show_obj = get_object_or_404(Show, id=id)

    show_info = {
        'poster_path': show_obj.tmdb_poster_path or '',
        'overview': show_obj.tmdb_overview or show_obj.description or '',
        'id': show_obj.tmdb_id,
    }

    show_tags = show_obj.tags.values_list('id', flat=True)

    pool = list(
        Show.objects
        .filter(tags__in=show_tags)
        .exclude(id=show_obj.id)
        .annotate(match_count=Count('tags'))
        .order_by('-match_count')
        .prefetch_related('creators')[:50]
    )

    if pool:
        max_matches = pool[0].match_count
        high_tier = [s for s in pool if s.match_count >= max_matches * 0.75]
        mid_tier = [s for s in pool if max_matches * 0.5 <= s.match_count < max_matches * 0.75]
        low_tier = [s for s in pool if s.match_count < max_matches * 0.5]

        random.shuffle(high_tier)
        random.shuffle(mid_tier)
        random.shuffle(low_tier)

        weighted = (high_tier[:3] + mid_tier[:2] + low_tier[:1])
        random.shuffle(weighted)
        recommended = weighted[:7]
    else:
        recommended = []

    if len(recommended) < 7:
        needed = 7 - len(recommended)
        existing_ids = [s.id for s in recommended] + [show_obj.id]
        fallback = list(
            Show.objects
            .exclude(id__in=existing_ids)
            .order_by('-created')
            .prefetch_related('creators')[:needed]
        )
        recommended += fallback

    recom_data = {}
    for rec in recommended:
        creator_name = rec.creators.first().name if rec.creators.exists() else ''
        recom_data[rec.title] = {
            'poster_path': rec.tmdb_poster_path or '',
            'id': rec.id,
            'creator': creator_name,
        }

    context = {
        'show': show_obj,
        'show_info': show_info,
        'recom_data': recom_data,
    }
    return render(request, 'show_page.html', context)


def about(request):
    return render(request, 'about.html')


def comment(request):
    return render(request, 'comment.html')


def send_emails_async(subject, email_message, confirmation_subject, confirmation_message, user_email):
    try:
        send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [EMAIL_HOST_USER], fail_silently=False)
        send_mail(confirmation_subject, confirmation_message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=True)
    except Exception as e:
        print(f"Email error: {e}")


def comment_submit(request):
    if request.method == "POST":
        # Honeypot check — bots fill this in, humans don't
        if request.POST.get('website', ''):
            return redirect(reverse('index'))
        
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save()
            subject = 'New User Message'
            email_message = f'You have received a new message from {comment.name} ({comment.email}).\n\nMessage: {comment.message}'
            confirmation_subject = 'Thanks for reaching out to Episode One!'
            confirmation_message = f'Hi {comment.name},\n\nThanks for reaching out to Episode One! We\'ve received your message and will get back to you soon.\n\nHere\'s a copy of your message:\n\n{comment.message}\n\nBest,\nThe Episode One Team'

            thread = threading.Thread(
                target=send_emails_async,
                args=(subject, email_message, confirmation_subject, confirmation_message, comment.email)
            )
            thread.daemon = True
            thread.start()

            return redirect(reverse('thankyou'))
    return redirect(reverse('index'))

def thankyou(request):
    return render(request, 'thankyou.html')


def _get_feed_image(entry):
    # Try media content
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url', '')
    # Try media thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url', '')
    # Try enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enclosure in entry.enclosures:
            if 'image' in enclosure.get('type', ''):
                return enclosure.get('url', '')
    # Try extracting image from content HTML
    content = ''
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].get('value', '')
    elif hasattr(entry, 'summary'):
        content = entry.summary or ''
    if content:
        import re
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if match:
            url = match.group(1)
            if url.startswith('http'):
                return url
    return None


def _is_scripted_tv(entry):
    SCRIPTED_KEYWORDS = [
        'drama', 'comedy', 'series', 'pilot', 'showrunner', 'writer',
        'screenplay', 'teleplay', 'scripted', 'limited series', 'miniseries',
        'network', 'streaming', 'netflix', 'hbo', 'hulu', 'amazon',
        'apple tv', 'peacock', 'paramount+', 'fx', 'amc', 'abc', 'nbc',
        'cbs', 'wga', 'writers guild', 'episode', 'season', 'renewed',
        'cancelled', 'canceled', 'premiere', 'finale', 'showtime',
        'anthology', 'cable drama', 'prestige tv', 'creator', 'developed by',
    ]

    REALITY_KEYWORDS = [
        'reality', 'bachelor', 'bachelorette', 'survivor', 'big brother',
        'real housewives', 'dancing with the stars', 'american idol',
        'the voice', 'talent show', 'competition show', 'dating show',
        'game show', 'unscripted', 'kardashian', 'jersey shore',
        'love island', 'top chef', 'project runway', 'drag race',
        'amazing race', 'bachelor in paradise', 'below deck',
        'vanderpump', 'bravo', 'mtv reality',
    ]

    text = (
        entry.get('title', '') + ' ' +
        entry.get('summary', '')
    ).lower()

    if any(keyword in text for keyword in REALITY_KEYWORDS):
        return False

    return any(keyword in text for keyword in SCRIPTED_KEYWORDS)


def _fetch_feed(feed):
    try:
        parsed = feedparser.parse(feed['url'])
        articles = []
        for entry in parsed.entries[:10]:
            if _is_scripted_tv(entry):
                articles.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'source': feed['source'],
                    'published': entry.get('published', ''),
                    'image': _get_feed_image(entry),
                })
        return articles
    except Exception as e:
        print(f"Feed error for {feed['source']}: {e}")
        return []


def news(request):
    cached_articles = cache.get('news_articles')
    if cached_articles:
        return render(request, 'news.html', {'articles': cached_articles})

    feeds = [
        {'source': 'TVLine', 'url': 'https://tvline.com/feed/'},
        {'source': 'IndieWire', 'url': 'https://www.indiewire.com/t/tv/feed'},
        {'source': 'Deadline', 'url': 'https://deadline.com/v/television/feed/'},
        {'source': 'The Wrap', 'url': 'https://thewrap.com/feed/'},
        {'source': 'New York Times', 'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Television.xml'},
        {'source': 'BBC', 'url': 'https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml'},
        {'source': 'TV Series Finale', 'url': 'https://tvseriesfinale.com/feed/'},
    ]

    articles = []

    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(_fetch_feed, feed): feed for feed in feeds}
        for future in as_completed(futures):
            articles.extend(future.result())

    articles.sort(key=lambda x: x['published'], reverse=True)

    cache.set('news_articles', articles, 60 * 30)

    return render(request, 'news.html', {'articles': articles})


def reviews(request):
    articles = Article.objects.filter(status='published').order_by('-published_at')
    return render(request, 'reviews.html', {'articles': articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, status='published')

    related_articles = Article.objects.filter(
        status='published'
    ).exclude(id=article.id).order_by('-published_at')[:3]

    context = {
        'article': article,
        'related_articles': related_articles,
    }
    return render(request, 'article_detail.html', context)


def browse(request):
    tags = Tag.objects.all().order_by('genre')
    context = {
        'tags': tags,
    }
    return render(request, 'browse.html', context)


def browse_shows(request):
    page = request.GET.get('page', 1)
    genre = request.GET.get('genre', '')
    search = request.GET.get('search', '')

    shows = Show.objects.all().order_by('-created').prefetch_related('creators', 'tags')

    if genre:
        shows = shows.filter(tags__genre__iexact=genre).distinct()

    if search:
        shows = shows.filter(
            Q(title__icontains=search) |
            Q(creators__name__icontains=search) |
            Q(tags__genre__icontains=search)
        ).distinct()

    paginator = Paginator(shows, 24)
    page_obj = paginator.get_page(page)

    results = []
    for show in page_obj:
        results.append({
            'id': show.id,
            'title': show.title,
            'poster': f"https://image.tmdb.org/t/p/w500/{show.tmdb_poster_path}" if show.tmdb_poster_path else None,
            'creators': [{'id': c.id, 'name': c.name} for c in show.creators.all()],
            'has_more': page_obj.has_next(),
        })

    return JsonResponse({
        'results': results,
        'has_more': page_obj.has_next(),
        'total': paginator.count,
        'genre': genre,
        'search': search,
    })