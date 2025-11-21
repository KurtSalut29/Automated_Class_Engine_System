from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from .models import User

def admin_required(function):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == User.Role.ADMIN,
        login_url='/login/'
    )
    return actual_decorator(function)

def instructor_required(function):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == User.Role.INSTRUCTOR,
        login_url='/login/'
    )
    return actual_decorator(function)

def student_required(function):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == User.Role.STUDENT,
        login_url='/login/'
    )
    return actual_decorator(function)

def role_required(allowed_roles):
    def decorator(function):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in allowed_roles:
                return function(request, *args, **kwargs)
            return HttpResponseForbidden("You don't have permission to access this page.")
        return wrapper
    return decorator