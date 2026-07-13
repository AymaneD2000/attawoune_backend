from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_seed_attawoune_curriculum'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursegrade',
            name='is_published',
            field=models.BooleanField(default=False, verbose_name='Publié'),
        ),
        migrations.AddField(
            model_name='coursegrade',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
