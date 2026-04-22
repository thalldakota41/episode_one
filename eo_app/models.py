from django.db import models


class Creator(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    name = models.CharField(unique=True, max_length=200)
    description = models.TextField(blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to='creators/', blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='O')
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tmdb_id = models.IntegerField(blank=True, null=True)
    tmdb_profile_path = models.CharField(max_length=200, blank=True, null=True)
    tmdb_biography = models.TextField(blank=True, null=True)
    tmdb_last_fetched = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    genre = models.CharField(unique=True, max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.genre


class CreatorOfTheMonth(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        unique_together = ('month', 'year', 'creator')

    def __str__(self):
        return f"Creator of the Month: {self.creator.name}"


class Show(models.Model):
    title = models.CharField(max_length=200)
    count = models.IntegerField()
    script = models.FileField(blank=True, null=True, upload_to="screenplays")
    poster = models.ImageField(blank=True, null=True, upload_to="posters")
    description = models.TextField(blank=True, null=True)
    creators = models.ManyToManyField(Creator, related_name='shows')
    tags = models.ManyToManyField(Tag, related_name='shows')
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tmdb_id = models.IntegerField(blank=True, null=True)
    tmdb_poster_path = models.CharField(max_length=200, blank=True, null=True)
    tmdb_overview = models.TextField(blank=True, null=True)
    tmdb_last_fetched = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment from {self.name}"


class StaffFavorite(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Staff Favorite: {self.show.title}"


class InfluentialShow(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        unique_together = ('month', 'year', 'show')

    def __str__(self):
        return f"Influential Show: {self.show.title}"


class FeaturedShow(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    featured_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-featured_date']

    def __str__(self):
        return f"Featured: {self.show.title} ({self.featured_date})"


class Article(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    CATEGORY_CHOICES = [
        ('television', 'Television'),
        ('writers', 'Writers'),
        ('craft', 'Craft'),
        ('industry', 'Industry'),
        ('pilots', 'Pilots'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.CharField(max_length=100, default='Episode One')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='television')
    cover_image = models.ImageField(upload_to='articles/', blank=True, null=True)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    @property
    def reading_time(self):
        word_count = len(self.body.split())
        return max(1, round(word_count / 200))