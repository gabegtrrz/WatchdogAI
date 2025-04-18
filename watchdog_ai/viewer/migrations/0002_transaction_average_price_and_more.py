# Generated by Django 5.2 on 2025-04-06 21:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="average_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="procurement_officer",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
