from django.db import models
from django.utils import timezone

class CategorySelection(models.Model):
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, blank=True, null=True)
    selected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.subcategory or 'All'} @ {self.selected_at.strftime('%Y-%m-%d %H:%M:%S')}"
