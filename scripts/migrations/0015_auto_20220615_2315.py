# Generated by Django 3.2.13 on 2022-06-15 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0014_comment_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character_id', models.CharField(max_length=20)),
                ('character_name', models.CharField(max_length=20)),
                ('ability', models.TextField()),
                ('first_night_reminder', models.TextField(blank=True, null=True)),
                ('other_night_reminder', models.TextField(blank=True, null=True)),
                ('global_reminders', models.CharField(blank=True, max_length=10, null=True)),
                ('reminders', models.TextField(blank=True, null=True)),
                ('type', models.CharField(choices=[('Townsfolk', 'Townsfolk'), ('Outsider', 'Outsider'), ('Minion', 'Minion'), ('Demon', 'Demon'), ('Traveller', 'Traveller'), ('Fabled', 'Fabled')], max_length=10)),
                ('edition', models.CharField(choices=[(0, 'Base'), (1, '+ Kickstarter'), (2, '+ Unreleased')], max_length=20)),
                ('first_night_position', models.IntegerField()),
                ('other_night_position', models.IntegerField()),
                ('image_url', models.CharField(max_length=100)),
                ('modifies_setup', models.BooleanField(default=False)),
            ],
            options={
                'permissions': [('update_characters', 'Can update character information')],
            },
        ),
        migrations.CreateModel(
            name='Translation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character_id', models.CharField(max_length=20)),
                ('character_name', models.CharField(max_length=20)),
                ('ability', models.TextField()),
                ('first_night_reminder', models.TextField(blank=True, null=True)),
                ('other_night_reminder', models.TextField(blank=True, null=True)),
                ('global_reminders', models.CharField(blank=True, max_length=10, null=True)),
                ('reminders', models.TextField(blank=True, null=True)),
                ('language', models.CharField(max_length=10)),
                ('friendly_language', models.CharField(max_length=20)),
            ],
            options={
                'permissions': [('update_translation', 'Can update a translation')],
            },
        ),
        migrations.AddIndex(
            model_name='translation',
            index=models.Index(fields=['language', 'character_id'], name='scripts_tra_languag_477f19_idx'),
        ),
        migrations.AddConstraint(
            model_name='translation',
            constraint=models.UniqueConstraint(fields=('language', 'character_id'), name='character_language'),
        ),
    ]
