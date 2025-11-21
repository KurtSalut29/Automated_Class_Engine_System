from .models import Announcement
from class_scheduling_system.scheduler import models

def announcements(request):
    """
    Pass latest announcements for the user's role to templates.
    Admins see all announcements.
    """
    if request.user.is_authenticated:
        user_role = request.user.role
        announcements = Announcement.objects.filter(
            models.Q(target_roles__icontains=user_role) |
            models.Q(target_roles='') |
            models.Q(target_roles__isnull=True)
        ).order_by('-created_at')[:5]
        return {'announcements': announcements}
    return {'announcements': []}
