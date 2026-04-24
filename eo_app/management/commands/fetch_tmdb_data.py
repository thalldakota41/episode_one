import os
import requests
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from eo_app.models import Creator, Show

API_KEY = os.environ.get('API_KEY')

class Command(BaseCommand):
    help = 'Fetches and caches TMDB data for all Creators and Shows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refetch-creator',
            type=str,
            help='Force re-fetch TMDB data for a specific creator by name',
        )
        parser.add_argument(
            '--refetch-show',
            type=str,
            help='Force re-fetch TMDB data for a specific show by title',
        )

    def handle(self, *args, **options):
        if options['refetch_creator']:
            self.refetch_creator(options['refetch_creator'])
        elif options['refetch_show']:
            self.refetch_show(options['refetch_show'])
        else:
            self.fetch_creators()
            self.fetch_shows()

    def refetch_creator(self, name):
        try:
            creator = Creator.objects.get(name__iexact=name)
            creator.tmdb_id = None
            creator.save()
            self.stdout.write(f"Cleared TMDB data for {creator.name}, re-fetching...")
            self._fetch_single_creator(creator)
        except Creator.DoesNotExist:
            self.stdout.write(f"Creator '{name}' not found in database")

    def refetch_show(self, title):
        try:
            show = Show.objects.get(title__iexact=title)
            show.tmdb_id = None
            show.save()
            self.stdout.write(f"Cleared TMDB data for {show.title}, re-fetching...")
            self._fetch_single_show(show)
        except Show.DoesNotExist:
            self.stdout.write(f"Show '{title}' not found in database")

    def fetch_creators(self):
        creators = Creator.objects.filter(tmdb_id__isnull=True)
        self.stdout.write(f"Fetching TMDB data for {creators.count()} creators...")
        for creator in creators:
            self._fetch_single_creator(creator)
            time.sleep(0.25)

    def fetch_shows(self):
        shows = Show.objects.filter(tmdb_id__isnull=True)
        self.stdout.write(f"Fetching TMDB data for {shows.count()} shows...")
        for show in shows:
            self._fetch_single_show(show)
            time.sleep(0.25)

    def _find_best_creator_match(self, results, creator):
        # Get all show titles this creator has in our database
        our_show_titles = set(
            creator.shows.values_list('title', flat=True)
        )

        # First priority — match by show title in known_for
        for result in results:
            known_for = result.get('known_for', [])
            for known in known_for:
                known_title = known.get('name') or known.get('title', '')
                if known_title in our_show_titles:
                    self.stdout.write(f"  matched {creator.name} via show '{known_title}'")
                    return result

        # Second priority — match by known_for_department = Writing
        writing_results = [
            r for r in results
            if r.get('known_for_department', '').lower() == 'writing'
        ]
        if writing_results:
            self.stdout.write(f"  matched {creator.name} via Writing department")
            return writing_results[0]

        # Third priority — match by known_for_department = Directing
        directing_results = [
            r for r in results
            if r.get('known_for_department', '').lower() == 'directing'
        ]
        if directing_results:
            self.stdout.write(f"  matched {creator.name} via Directing department")
            return directing_results[0]

        # Last resort — fall back to first result
        self.stdout.write(f"  no good match for {creator.name}, using first result")
        return results[0] if results else {}

    def _find_best_show_match(self, results, show):
        # Get all creator names for this show from our database
        our_creator_names = set(
            show.creators.values_list('name', flat=True)
        )

        # Loop through TMDB results and check if any creator names match
        for result in results:
            result_name = result.get('name', '')
            # Check if the show title matches closely
            if result_name.lower() == show.title.lower():
                return result

        # Fall back to first result
        self.stdout.write(f"  no exact match for {show.title}, using first result")
        return results[0] if results else {}

    def _fetch_single_creator(self, creator):
        try:
            resp = requests.get(
                'https://api.themoviedb.org/3/search/person',
                params={'api_key': API_KEY, 'query': creator.name},
                timeout=5
            ).json()

            results = resp.get('results', [])
            if not results:
                self.stdout.write(f"  ✗ {creator.name} — not found on TMDB")
                return

            result = self._find_best_creator_match(results, creator)
            tmdb_id = result.get('id')

            if tmdb_id:
                detail = requests.get(
                    f'https://api.themoviedb.org/3/person/{tmdb_id}',
                    params={'api_key': API_KEY},
                    timeout=5
                ).json()

                creator.tmdb_id = tmdb_id
                creator.tmdb_profile_path = result.get('profile_path', '')
                creator.tmdb_biography = detail.get('biography', '')
                creator.tmdb_last_fetched = timezone.now()
                creator.save()
                self.stdout.write(f"  ✓ {creator.name} — TMDB ID: {tmdb_id}")
            else:
                self.stdout.write(f"  ✗ {creator.name} — not found on TMDB")

        except Exception as e:
            self.stdout.write(f"  ERROR for {creator.name}: {e}")

    def _fetch_single_show(self, show):
        try:
            resp = requests.get(
                'https://api.themoviedb.org/3/search/tv',
                params={'api_key': API_KEY, 'query': show.title},
                timeout=5
            ).json()

            results = resp.get('results', [])
            if not results:
                self.stdout.write(f"  ✗ {show.title} — not found on TMDB")
                return

            result = self._find_best_show_match(results, show)
            tmdb_id = result.get('id')

            if tmdb_id:
                show.tmdb_id = tmdb_id
                show.tmdb_poster_path = result.get('poster_path', '')
                show.tmdb_overview = result.get('overview', '')
                show.tmdb_last_fetched = timezone.now()
                show.save()
                self.stdout.write(f"  ✓ {show.title} — TMDB ID: {tmdb_id}")
            else:
                self.stdout.write(f"  ✗ {show.title} — not found on TMDB")

        except Exception as e:
            self.stdout.write(f"  ERROR for {show.title}: {e}")