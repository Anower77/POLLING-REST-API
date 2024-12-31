from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import EmailConfirmation
from rest_framework import viewsets, permissions
from .serializers import UserSerializer, UserProfileSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            redirect_url = request.GET.get('next', 'home')
            return redirect(redirect_url)
        else:
            messages.error(
                request, 
                "Username Or Password is incorrect!",
                extra_tags='alert alert-warning alert-dismissible fade show'
            )

    return render(request, 'accounts/login.html')


def logout_user(request):
    logout(request)
    return redirect('home')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Save the user but don't activate yet
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                
                # Create email confirmation token
                confirmation = EmailConfirmation.objects.create(user=user)
                
                # Build confirmation link
                confirm_url = request.build_absolute_uri(
                    f'/accounts/confirm/{confirmation.token}/'
                )
                
                # Prepare email
                context = {
                    'user': user,
                    'confirm_url': confirm_url
                }
                html_message = render_to_string('accounts/confirmation_email.html', context)
                plain_message = strip_tags(html_message)
                
                try:
                    # Debug information
                    logger.info(f"Attempting to send email to {user.email}")
                    logger.info(f"Using email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}")
                    
                    # Send confirmation email
                    send_mail(
                        subject='Confirm your Modern Polling Registration',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    
                    logger.info(f"Email sent successfully to {user.email}")
                    messages.success(
                        request,
                        'Registration successful! Please check your email to confirm your account.',
                        extra_tags='alert alert-success alert-dismissible fade show'
                    )
                    return redirect('accounts:login')
                    
                except BadHeaderError:
                    user.delete()
                    logger.error("Invalid header found in email")
                    messages.error(
                        request,
                        'Invalid email header. Please try again.',
                        extra_tags='alert alert-danger alert-dismissible fade show'
                    )
                except Exception as e:
                    user.delete()
                    logger.error(f"Failed to send email: {str(e)}")
                    messages.error(
                        request,
                        'Failed to send confirmation email. Please try again.',
                        extra_tags='alert alert-danger alert-dismissible fade show'
                    )
            
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(
                    request,
                    'Registration failed. Please try again.',
                    extra_tags='alert alert-danger alert-dismissible fade show'
                )
    
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def confirm_email(request, token):
    confirmation = get_object_or_404(EmailConfirmation, token=token, is_confirmed=False)
    
    # Activate user
    user = confirmation.user
    user.is_active = True
    user.save()
    
    # Mark confirmation as complete
    confirmation.is_confirmed = True
    confirmation.save()
    
    messages.success(
        request,
        'Email confirmed! You can now login to your account.',
        extra_tags='alert alert-success alert-dismissible fade show'
    )
    return redirect('accounts:login')


def logout_view(request):
    logout(request)
    messages.success(
        request, 
        "You have been successfully logged out!", 
        extra_tags='alert alert-success alert-dismissible fade show'
    )
    return redirect('home')


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['get', 'put'], permission_classes=[permissions.IsAuthenticated])
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)


def test_email(request):
    try:
        send_mail(
            subject='Test Email',
            message='This is a test email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],  # Send to yourself
            fail_silently=False,
        )
        return HttpResponse("Test email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Failed to send email: {str(e)}")
