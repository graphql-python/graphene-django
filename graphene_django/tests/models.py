from django.db import models
from django.utils.translation import gettext_lazy as _

CHOICES = ((1, "this"), (2, _("that")))


class Person(models.Model):
    name = models.CharField(max_length=30)


class Pet(models.Model):
    name = models.CharField(max_length=30)
    age = models.PositiveIntegerField()
    owner = models.ForeignKey(
        "Person", on_delete=models.CASCADE, null=True, blank=True, related_name="pets"
    )


class FilmDetails(models.Model):
    location = models.CharField(max_length=30)
    film = models.OneToOneField(
        "Film",
        on_delete=models.CASCADE,
        related_name="details",
        null=True,
        blank=True,
    )


class Film(models.Model):
    genre = models.CharField(
        max_length=2,
        help_text="Genre",
        choices=[("do", "Documentary"), ("ac", "Action"), ("ot", "Other")],
        default="ot",
    )
    reporters = models.ManyToManyField("Reporter", related_name="films")


class DoeReporterManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(last_name="Doe")


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    pets = models.ManyToManyField("self")
    a_choice = models.IntegerField(choices=CHOICES, null=True, blank=True)
    objects = models.Manager()
    doe_objects = DoeReporterManager()
    fans = models.ManyToManyField(Person)

    reporter_type = models.IntegerField(
        "Reporter Type",
        null=True,
        blank=True,
        choices=[(1, "Regular"), (2, "CNN Reporter")],
    )

    def __str__(self):  # __unicode__ on Python 2
        return f"{self.first_name} {self.last_name}"

    def __init__(self, *args, **kwargs):
        """
        Override the init method so that during runtime, Django
        can know that this object can be a CNNReporter by casting
        it to the proxy model. Otherwise, as far as Django knows,
        when a CNNReporter is pulled from the database, it is still
        of type Reporter. This was added to test proxy model support.
        """
        super().__init__(*args, **kwargs)
        if self.reporter_type == 2:  # quick and dirty way without enums
            self.__class__ = CNNReporter

    def some_method(self):
        return 123


class CNNReporterManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(reporter_type=2)


class CNNReporter(Reporter):
    """
    This class is a proxy model for Reporter, used for testing
    proxy model support
    """

    class Meta:
        proxy = True

    objects = CNNReporterManager()


class APNewsReporter(Reporter):
    """
    This class only inherits from Reporter for testing multi table inheritance
    similar to what you'd see in django-polymorphic
    """

    alias = models.CharField(max_length=30)
    objects = models.Manager()


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField(auto_now_add=True)
    pub_date_time = models.DateTimeField(auto_now_add=True)
    reporter = models.ForeignKey(
        Reporter, on_delete=models.CASCADE, related_name="articles"
    )
    editor = models.ForeignKey(
        Reporter, on_delete=models.CASCADE, related_name="edited_articles_+"
    )
    lang = models.CharField(
        max_length=2,
        help_text="Language",
        choices=[("es", "Spanish"), ("en", "English")],
        default="es",
    )
    importance = models.IntegerField(
        "Importance",
        null=True,
        blank=True,
        choices=[(1, "Very important"), (2, "Not as important")],
    )

    def __str__(self):  # __unicode__ on Python 2
        return self.headline

    class Meta:
        ordering = ("headline",)
