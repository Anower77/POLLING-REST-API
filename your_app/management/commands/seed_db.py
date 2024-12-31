from django.core.management.base import BaseCommand
from your_app.seeder import seed_all

class Command(BaseCommand):
    help = 'Seed database with sample data'

    def add_arguments(self, parser):
        parser.add_argument('--entries', type=int, default=30)

    def handle(self, *args, **kwargs):
        num_entries = kwargs['entries']
        seed_all(num_entries)
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded database with {num_entries} entries')) 