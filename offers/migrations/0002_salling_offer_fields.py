from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("offers", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="offerprovider",
            name="kind",
            field=models.CharField(
                choices=[
                    ("mock", "Mock"),
                    ("manual", "Manual import"),
                    ("api", "Official API"),
                    ("feed", "Official feed"),
                    ("salling_group", "Salling Group"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="groceryoffer", name="discount_amount", field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        migrations.AddField(model_name="groceryoffer", name="discount_percentage", field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
        migrations.AddField(model_name="groceryoffer", name="quantity", field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
        migrations.AddField(model_name="groceryoffer", name="raw_source_timestamp", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="groceryoffer", name="unit", field=models.CharField(blank=True, max_length=50)),
    ]
