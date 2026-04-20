
from django.test import TestCase, Client
from django.urls import reverse
from .models import Creator, Tag, Show, Comment, StaffFavorite, CreatorOfTheMonth, InfluentialShow
from datetime import date


class CreatorModelTest(TestCase):
    def setUp(self):
        self.creator = Creator.objects.create(
            name='Test Creator',
            gender='M',
        )

    def test_creator_str(self):
        self.assertEqual(str(self.creator), 'Test Creator')

    def test_creator_default_gender(self):
        creator = Creator.objects.create(name='Another Creator')
        self.assertEqual(creator.gender, 'O')

    def test_creator_unique_name(self):
        with self.assertRaises(Exception):
            Creator.objects.create(name='Test Creator')


class TagModelTest(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(genre='Drama')

    def test_tag_str(self):
        self.assertEqual(str(self.tag), 'Drama')

    def test_tag_unique_genre(self):
        with self.assertRaises(Exception):
            Tag.objects.create(genre='Drama')


class ShowModelTest(TestCase):
    def setUp(self):
        self.creator = Creator.objects.create(name='Test Creator')
        self.tag = Tag.objects.create(genre='Drama')
        self.show = Show.objects.create(
            title='Test Show',
            count=60,
        )
        self.show.creators.add(self.creator)
        self.show.tags.add(self.tag)

    def test_show_str(self):
        self.assertEqual(str(self.show), 'Test Show')

    def test_show_has_creator(self):
        self.assertIn(self.creator, self.show.creators.all())

    def test_show_has_tag(self):
        self.assertIn(self.tag, self.show.tags.all())


class CommentModelTest(TestCase):
    def setUp(self):
        self.comment = Comment.objects.create(
            name='Test User',
            email='test@test.com',
            message='Test message'
        )

    def test_comment_str(self):
        self.assertEqual(str(self.comment), 'Comment from Test User')


class StaffFavoriteModelTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(title='Test Show', count=60)
        self.staff_favorite = StaffFavorite.objects.create(show=self.show)

    def test_staff_favorite_str(self):
        self.assertEqual(str(self.staff_favorite), 'Staff Favorite: Test Show')


class InfluentialShowModelTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(title='Test Show', count=60)
        self.influential_show = InfluentialShow.objects.create(
            show=self.show,
            month=1,
            year=2026
        )

    def test_influential_show_str(self):
        self.assertEqual(str(self.influential_show), 'Influential Show: Test Show')

    def test_unique_together(self):
        with self.assertRaises(Exception):
            InfluentialShow.objects.create(
                show=self.show,
                month=1,
                year=2026
            )


class ViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.creator = Creator.objects.create(
            name='Test Creator',
            gender='M',
        )
        self.tag = Tag.objects.create(genre='Drama')
        self.show = Show.objects.create(
            title='Test Show',
            count=60,
        )
        self.show.creators.add(self.creator)
        self.show.tags.add(self.tag)
        self.staff_favorite = StaffFavorite.objects.create(show=self.show)
        self.influential_show = InfluentialShow.objects.create(
            show=self.show,
            month=1,
            year=2026
        )

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about.html')

    def test_comment_page(self):
        response = self.client.get(reverse('comment'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comment.html')

    def test_news_page(self):
        response = self.client.get(reverse('news'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'news.html')

    def test_reviews_page(self):
        response = self.client.get(reverse('reviews'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reviews.html')

    def test_search_page(self):
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search_results.html')

    def test_search_with_query(self):
        response = self.client.get(reverse('search'), {'search': 'Test Show'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Show')

    def test_show_page(self):
        response = self.client.get(reverse('show_page', args=[self.show.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_page.html')

    def test_show_page_404(self):
        response = self.client.get(reverse('show_page', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_creator_page(self):
        response = self.client.get(reverse('creator', args=[self.creator.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'creator_page.html')

    def test_creator_page_404(self):
        response = self.client.get(reverse('creator', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_all_staff_favorites_page(self):
        response = self.client.get(reverse('all_staff_favorites'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'all_staff_favorites.html')

    def test_influential_shows_page(self):
        response = self.client.get(reverse('influential_shows'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'influential_shows.html')

    def test_comment_submit_valid(self):
        response = self.client.post(reverse('comment_submit'), {
            'name': 'Test User',
            'email': 'test@test.com',
            'message': 'Test message'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)

    def test_comment_submit_invalid(self):
        response = self.client.post(reverse('comment_submit'), {
            'name': '',
            'email': 'notanemail',
            'message': ''
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_search_ajax(self):
        response = self.client.get(
            reverse('search'),
            {'search': 'Test'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')