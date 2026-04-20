from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import requests
import threading
from .models import Creator, Tag, Show, Comment, StaffFavorite, CreatorOfTheMonth, InfluentialShow, FeaturedShow
from django.db.models import Count, Q, F, Max, ExpressionWrapper
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
from .forms import CommentForm
from django.core.mail import send_mail
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
        results = [
            {'title': show.title, 'poster': show.poster.url if show.poster else None}
            for show in shows
        ]
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
        results = [
            {'title': show.title, 'poster': show.poster.url if show.poster else None}
            for show in shows
        ]
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
        recommended = weighted[:6]
    else:
        recommended = []

    if len(recommended) < 6:
        needed = 6 - len(recommended)
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


def news(request):
    return render(request, 'news.html')


def reviews(request):
    return render(request, 'reviews.html')


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
            Q(creators__name__icontains=search)
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