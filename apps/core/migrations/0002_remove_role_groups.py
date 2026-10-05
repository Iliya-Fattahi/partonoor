"""
The site has exactly one manager (a superuser) — there is no role system.

Earlier builds seeded three permission Groups (Content/Project/Article Manager)
via a data migration in the now-removed `accounts` app. On a database that ran
that migration those Groups still exist; delete them so no unused roles or
permissions are left behind. On a fresh database this is a no-op.
"""
from django.db import migrations

OLD_ROLE_GROUPS = ["Content Manager", "Project Manager", "Article Manager"]


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=OLD_ROLE_GROUPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(remove_role_groups, migrations.RunPython.noop)]
