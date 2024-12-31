from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib import messages
from .models import Poll, Choice, Vote
from .forms import PollAddForm, EditPollForm, ChoiceAddForm
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings  # To access your email settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.forms import inlineformset_factory
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from rest_framework import viewsets, permissions
from .serializers import PollSerializer, ChoiceSerializer, VoteSerializer
from rest_framework.response import Response
from rest_framework.decorators import action


@login_required()
def polls_list(request):
    all_polls = Poll.objects.all()
    search_term = ""
    
    # Add user filter
    if "user" in request.GET:
        username = request.GET["user"]
        all_polls = all_polls.filter(owner__username=username)
    
    # Add default ordering
    all_polls = all_polls.order_by('-pub_date')
    
    if "name" in request.GET:
        all_polls = all_polls.order_by("text")

    if "date" in request.GET:
        all_polls = all_polls.order_by("-pub_date")

    if "vote" in request.GET:
        all_polls = all_polls.annotate(Count("vote")).order_by("-vote__count")

    if "search" in request.GET:
        search_term = request.GET["search"]
        all_polls = all_polls.filter(text__icontains=search_term)

    paginator = Paginator(all_polls, 6)
    page = request.GET.get("page")
    polls = paginator.get_page(page)

    get_dict_copy = request.GET.copy()
    params = get_dict_copy.pop("page", True) and get_dict_copy.urlencode()

    context = {
        "polls": polls,
        "params": params,
        "search_term": search_term,
    }
    return render(request, "polls/polls_list.html", context)


@login_required()
def dashboard(request):
    polls = Poll.objects.all()
    poll_data = []

    for poll in polls:
        unique_voters = Vote.objects.filter(poll=poll).values("user").distinct().count()
        poll_data.append({"question": poll.text, "unique_voters": unique_voters})

    context = {"poll_data": poll_data}
    return render(request, "polls/dashboard.html", context)


@login_required()
def list_by_user(request):
    all_polls = Poll.objects.filter(owner=request.user)
    paginator = Paginator(all_polls, 7)  # Show 7 contacts per page

    page = request.GET.get("page")
    polls = paginator.get_page(page)

    context = {
        "polls": polls,
    }
    return render(request, "polls/polls_list.html", context)


@login_required(login_url='accounts:login')
def polls_add(request):
    if request.method == "POST":
        form = PollAddForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.owner = request.user
            poll.save()
            Choice(poll=poll, choice_text=form.cleaned_data["choice1"]).save()
            Choice(poll=poll, choice_text=form.cleaned_data["choice2"]).save()

            messages.success(
                request,
                "Poll & Choices added successfully.",
                extra_tags="alert alert-success alert-dismissible fade show",
            )

            return redirect("polls:list")
    else:
        form = PollAddForm()
    context = {
        "form": form,
    }
    return render(request, "polls/add_poll.html", context)


@login_required
def polls_edit(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    if request.user != poll.owner:
        return redirect("home")
        
    ChoiceFormSet = inlineformset_factory(
        Poll, 
        Choice,
        fields=('choice_text',),
        extra=1,
        can_delete=True
    )
    
    if request.method == 'POST':
        form = EditPollForm(request.POST, instance=poll)
        formset = ChoiceFormSet(request.POST, instance=poll)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(
                request,
                "Poll Updated successfully.",
                extra_tags="alert alert-success alert-dismissible fade show",
            )
            return redirect('polls:list')
    else:
        form = EditPollForm(instance=poll)
        formset = ChoiceFormSet(instance=poll)
    
    return render(request, 'polls/poll_edit.html', {
        'form': form,
        'choice_formset': formset,
        'poll': poll
    })


@login_required
def polls_delete(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if request.user != poll.owner:
        return redirect("home")
    poll.delete()
    messages.success(
        request,
        "Poll Deleted successfully.",
        extra_tags="alert alert-success alert-dismissible fade show",
    )
    return redirect("polls:list")


@login_required
def add_choice(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if request.user != poll.owner:
        return redirect("home")

    if request.method == "POST":
        form = ChoiceAddForm(request.POST)
        if form.is_valid:
            new_choice = form.save(commit=False)
            new_choice.poll = poll
            new_choice.save()
            messages.success(
                request,
                "Choice added successfully.",
                extra_tags="alert alert-success alert-dismissible fade show",
            )
            return redirect("polls:edit", poll.id)
    else:
        form = ChoiceAddForm()
    context = {
        "form": form,
    }
    return render(request, "polls/add_choice.html", context)


@login_required
def choice_edit(request, choice_id):
    choice = get_object_or_404(Choice, pk=choice_id)
    poll = get_object_or_404(Poll, pk=choice.poll.id)
    if request.user != poll.owner:
        return redirect("home")

    if request.method == "POST":
        form = ChoiceAddForm(request.POST, instance=choice)
        if form.is_valid:
            new_choice = form.save(commit=False)
            new_choice.poll = poll
            new_choice.save()
            messages.success(
                request,
                "Choice Updated successfully.",
                extra_tags="alert alert-success alert-dismissible fade show",
            )
            return redirect("polls:edit", poll.id)
    else:
        form = ChoiceAddForm(instance=choice)
    context = {
        "form": form,
        "edit_choice": True,
        "choice": choice,
    }
    return render(request, "polls/add_choice.html", context)


@login_required
def choice_delete(request, choice_id):
    choice = get_object_or_404(Choice, pk=choice_id)
    poll = get_object_or_404(Poll, pk=choice.poll.id)
    if request.user != poll.owner:
        return redirect("home")
    choice.delete()
    messages.success(
        request,
        "Choice Deleted successfully.",
        extra_tags="alert alert-success alert-dismissible fade show",
    )
    return redirect("polls:edit", poll.id)


def poll_detail(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    poll._request_user = request.user
    
    if not poll.active:
        return render(request, "polls/poll_result.html", {"poll": poll})
    
    # Add last_update timestamp to help with reconnection
    context = {
        "poll": poll,
        "share_url": request.build_absolute_uri(),
        "last_update": timezone.now().timestamp()
    }
    return render(request, "polls/poll_detail.html", context)


@login_required(login_url='accounts:login')
def poll_vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    
    # Prevent self-voting
    if request.user == poll.owner:
        messages.error(
            request,
            "You cannot vote on your own poll!",
            extra_tags='alert alert-warning alert-dismissible fade show'
        )
        return redirect('polls:detail', poll_id=poll_id)
    
    # Check if user has already voted
    if Vote.objects.filter(user=request.user, poll=poll).exists():
        messages.error(
            request,
            "You have already voted on this poll!",
            extra_tags='alert alert-warning alert-dismissible fade show'
        )
        return redirect('polls:detail', poll_id=poll_id)
    
    if request.method == 'POST':
        try:
            choice = poll.choice_set.get(pk=request.POST['choice'])
            Vote.objects.create(user=request.user, poll=poll, choice=choice)

            try:
                # Try to broadcast the update
                choices_data = []
                total_votes = poll.get_vote_count
                for poll_choice in poll.choice_set.all():
                    choice_votes = poll_choice.get_vote_count
                    choices_data.append({
                        'id': poll_choice.id,
                        'votes': choice_votes,
                        'percentage': round((choice_votes / total_votes * 100), 1) if total_votes > 0 else 0
                    })

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'poll_{poll_id}',
                    {
                        'type': 'poll_update',
                        'data': {
                            'choices': choices_data
                        }
                    }
                )
            except Exception:
                # If real-time update fails, just continue
                pass

            messages.success(
                request,
                "Your vote has been recorded!",
                extra_tags='alert alert-success alert-dismissible fade show'
            )
            return redirect('polls:detail', poll_id=poll_id)
            
        except (KeyError, Choice.DoesNotExist):
            messages.error(
                request,
                "You didn't select a choice.",
                extra_tags='alert alert-warning alert-dismissible fade show'
            )
            return render(request, 'polls/poll_detail.html', {
                'poll': poll,
            })
    
    return render(request, 'polls/poll_detail.html', {'poll': poll})


@login_required
def end_poll(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if request.user != poll.owner:
        return redirect("home")

    if poll.active is True:
        poll.active = False
        poll.save()
        return render(request, "polls/poll_result.html", {"poll": poll})
    else:
        return render(request, "polls/poll_result.html", {"poll": poll})


def poll_results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    votes = Vote.objects.filter(poll=poll).select_related('choice', 'user')
    
    # Calculate vote percentages
    total_votes = votes.count()
    choices_with_stats = []
    
    for choice in poll.choice_set.all():
        choice_votes = votes.filter(choice=choice).count()
        percentage = (choice_votes / total_votes * 100) if total_votes > 0 else 0
        choices_with_stats.append({
            'choice': choice,
            'votes': choice_votes,
            'percentage': round(percentage, 1)
        })
    
    context = {
        'poll': poll,
        'choices_with_stats': choices_with_stats,
        'total_votes': total_votes,
    }
    return render(request, 'polls/poll_results.html', context)


class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        choice = self.get_object()
        user = request.user
        
        # Check if user already voted for this poll
        if Vote.objects.filter(choice__poll=choice.poll, user=user).exists():
            return Response({'detail': 'You have already voted in this poll.'}, status=400)
        
        vote = Vote.objects.create(choice=choice, poll=choice.poll, user=user)
        serializer = VoteSerializer(vote)
        return Response(serializer.data)


class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
