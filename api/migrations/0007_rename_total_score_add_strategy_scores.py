from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_rename_api_tables"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stockdata",
            old_name="total_score",
            new_name="strategy_one_score",
        ),
        migrations.AddField(
            model_name="stockdata",
            name="strategy_two_score",
            field=models.DecimalField(decimal_places=6, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name="stockdata",
            name="strategy_three_score",
            field=models.DecimalField(decimal_places=6, max_digits=15, null=True),
        ),
        migrations.RemoveField(
            model_name="stockdata",
            name="direction",
        ),
    ]
