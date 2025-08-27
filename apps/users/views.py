from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

def home(request):
    """
    Renders the home page with different content for authenticated vs unauthenticated users.
    """
    context = {
        'user': request.user,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'home.html', context)

def login_view(request):
    """
    Handles user login with form validation and error handling.
    """
    # Redirect if user is already logged in
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Basic validation
        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'users/login.html')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next parameter or home
            next_url = request.GET.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'users/login.html')

def logout_view(request):
    """
    Handles user logout with confirmation message.
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'You have been successfully logged out, {username}.')
    else:
        messages.info(request, 'You are not currently logged in.')
    
    return redirect('home')

@login_required
def profile_view(request):
    """
    Displays user profile information (requires login).
    """
    return render(request, 'users/profile.html') 