from django.core.management.base import BaseCommand, CommandError

from offers.salling import SallingClient, SallingError


class Command(BaseCommand):
    help = "Verify Salling Group authentication and optionally anti-food-waste access."

    def add_arguments(self, parser):
        parser.add_argument("--zip", dest="zip_code")

    def handle(self, *args, **options):
        try:
            client = SallingClient()
            stores = client.stores(country="dk", fields="id,name", per_page=1)
            self.stdout.write(
                f"Stores API: authenticated; received {len(stores.items)} normalized result(s)."
            )
            if options["zip_code"]:
                offers = client.food_waste(zip_code=options["zip_code"])
                self.stdout.write(
                    "Anti Food Waste API: authenticated; "
                    f"received {len(offers.items)} normalized offer(s)."
                )
        except SallingError as error:
            raise CommandError(f"Salling Group verification failed: {type(error).__name__}") from error
        self.stdout.write(self.style.SUCCESS("Salling Group verification succeeded."))
