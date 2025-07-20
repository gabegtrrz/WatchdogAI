from django.shortcuts import render

def home(request):
    """
    Renders the home page with user type selection.
    """
    return render(request, 'home.html') 