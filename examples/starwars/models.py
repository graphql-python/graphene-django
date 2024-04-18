from django.db import models


class Character(models.Model):
    name = models.CharField(max_length=50)
    ship = models.ForeignKey(
        "Ship",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="characters",
    )

    def __str__(self):
        return self.name


class Faction(models.Model):
    name = models.CharField(max_length=50)
    hero = models.ForeignKey(Character, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Ship(models.Model):
    name = models.CharField(max_length=50)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, related_name="ships")

    def __str__(self):
        return self.name
