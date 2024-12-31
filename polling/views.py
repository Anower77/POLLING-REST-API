from django.shortcuts import render
from polls.models import Poll, Vote

def home(request):
    # Get total counts
    total_polls = Poll.objects.count()
    total_votes = Vote.objects.count()
    total_completed_polls = Poll.objects.filter(active=False).count()
    
    # Calculate percentages for circular progress bars
    max_polls = max(total_polls, 1)  # Avoid division by zero
    total_polls_percentage = (total_polls / max_polls) * 100
    total_votes_percentage = (total_votes / max_polls) * 100
    completed_polls_percentage = (total_completed_polls / max_polls) * 100
    
    context = {
        'total_polls': total_polls,
        'total_votes': total_votes,
        'total_completed_polls': total_completed_polls,
        'total_polls_percentage': total_polls_percentage,
        'total_votes_percentage': total_votes_percentage,
        'completed_polls_percentage': completed_polls_percentage,
    }
    return render(request, 'home.html', context)