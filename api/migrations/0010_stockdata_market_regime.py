from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0009_rename_original_macd_scores_to_strategy_scores"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockdata",
            name="market_regime",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
