from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class RoleBasedAuthBackend(ModelBackend):
    """
    Custom authentication backend:
    - Admins log in with username/password normally.
    - Students log in using student_number + password.
    - Instructors log in using instructor_number + password.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check admin login first (username)
            user = User.objects.filter(username=username).first()
            if user and user.check_password(password):
                return user

            # If not admin, try student_number
            user = User.objects.filter(student_number=username, role=User.Role.STUDENT).first()
            if user and user.check_password(password):
                return user

            # If not student, try instructor_number
            user = User.objects.filter(instructor_number=username, role=User.Role.INSTRUCTOR).first()
            if user and user.check_password(password):
                return user

        except User.DoesNotExist:
            return None
        return None
