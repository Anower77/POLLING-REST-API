from faker import Faker
from django.contrib.auth.models import User
from polls.models import Poll, Choice  # Adjust this import based on your app name
import random

fake = Faker()

def seed_users(num_entries=30):
    for _ in range(num_entries):
        User.objects.create_user(
            username=fake.user_name(),
            email=fake.email(),
            password='password123'
        )
    print(f'{num_entries} users created!')

def seed_polls(num_entries=30):
    users = User.objects.all()
    for _ in range(num_entries):
        poll = Poll.objects.create(
            owner=random.choice(users),
            text=fake.sentence(nb_words=6),
            pub_date=fake.date_time_this_year()
        )
        # Create 3-5 choices for each poll
        for _ in range(random.randint(3, 5)):
            Choice.objects.create(
                poll=poll,
                choice_text=fake.word(),
                votes=random.randint(0, 100)
            )
    print(f'{num_entries} polls created!')

def seed_all(num_entries=30):
    seed_users(num_entries)
    seed_polls(num_entries) 