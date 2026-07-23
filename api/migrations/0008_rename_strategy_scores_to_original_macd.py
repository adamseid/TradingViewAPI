from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_rename_total_score_add_strategy_scores"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stockdata",
            old_name="strategy_one_score",
            new_name="original_score",
        ),
        migrations.RenameField(
            model_name="stockdata",
            old_name="strategy_two_score",
            new_name="macd_score",
        ),
    ]
