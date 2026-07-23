from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_rename_strategy_scores_to_original_macd"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stockdata",
            old_name="original_score",
            new_name="original_strategy_score",
        ),
        migrations.RenameField(
            model_name="stockdata",
            old_name="macd_score",
            new_name="macd_strategy_score",
        ),
    ]
