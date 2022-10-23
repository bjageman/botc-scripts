# Generated by Django 3.2.14 on 2022-07-09 15:10

from django.db import migrations, models

from scripts.views import count_character
from scripts.characters import CharacterType


def update_existing_script_number_fields(apps, schema_editor):
    ScriptVersion = apps.get_model("scripts", "scriptversion")
    for script in ScriptVersion.objects.all():
        script.num_townsfolk = count_character(script.content, CharacterType.TOWNSFOLK)
        script.num_outsiders = count_character(script.content, CharacterType.OUTSIDER)
        script.num_minions = count_character(script.content, CharacterType.MINION)
        script.num_demons = count_character(script.content, CharacterType.DEMON)
        script.num_fabled = count_character(script.content, CharacterType.FABLED)
        script.num_travellers = count_character(script.content, CharacterType.TRAVELLER)
        script.save()


class Migration(migrations.Migration):

    dependencies = [
        ("scripts", "0015_auto_20220616_2142"),
    ]

    operations = [
        migrations.AddField(
            model_name="scriptversion",
            name="num_demons",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scriptversion",
            name="num_fabled",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scriptversion",
            name="num_minions",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scriptversion",
            name="num_outsiders",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scriptversion",
            name="num_townsfolk",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="scriptversion",
            name="num_travellers",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.RunPython(
            update_existing_script_number_fields, reverse_code=migrations.RunPython.noop
        ),
    ]
