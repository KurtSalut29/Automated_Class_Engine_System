from django.urls import path
from . import views
from .views import public_schedule_view

urlpatterns = [
    # ==============================
    # AUTH & DASHBOARD
    # ==============================
    path('', views.auth_view, name='auth_page'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_redirect, name='home_redirect'),

    # ==============================
    # ADMIN DASHBOARD
    # ==============================
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ==============================
    # USER MANAGEMENT
    # ==============================
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/users/add/', views.add_user, name='add_user'),
    path('admin/users/<int:user_id>/', views.view_user_profile, name='view_user_profile'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('admin/users/<int:user_id>/approve/', views.approve_user, name='approve_user'),
    path('admin/users/<int:user_id>/activate/', views.activate_user, name='activate_user'),
    path('admin/users/<int:user_id>/deactivate/', views.deactivate_user, name='deactivate_user'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin/users/bulk_action/', views.bulk_user_action, name='bulk_user_action'),

    # ==============================
    # CURRICULUM MANAGEMENT
    # ==============================
    path('admin/curriculum/', views.manage_curriculum, name='manage_curriculum'),

    # ==============================
    # SUBJECT MANAGEMENT
    # ==============================
    path('admin/subjects/', views.manage_subjects, name='manage_subjects'),
    path("admin/subject/edit/<int:subject_id>/", views.edit_subject, name="edit_subject"),
    path('admin/subject/delete/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('admin/api/subject/<int:subject_id>/', views.get_subject_api, name='get_subject_api'),
    path('admin/subject/edit/<int:subject_id>/', views.edit_manage_subjects, name='edit_manage_subjects'),
    path('delete-subject/', views.delete_subject, name='delete_subject'),



    # ==============================
    # SECTION MANAGEMENT
    # ==============================
    path('admin/sections/', views.manage_sections, name='manage_sections'),
    path('admin/sections/department/<int:department_id>/', views.manage_sections, name='manage_sections_by_department'),
    path('admin/sections/edit/<int:section_id>/', views.edit_section, name='edit_section'),
    path('admin/sections/delete/<int:section_id>/', views.delete_section, name='delete_section'),

    # ==============================
    # INSTRUCTOR MANAGEMENT
    # ==============================
    path('admin/instructors/', views.manage_instructors, name='manage_instructors'),
    path('admin/instructors/delete/<int:instructor_id>/', views.delete_instructor, name='delete_instructor'),

    # ==============================
    # ROOM MANAGEMENT
    # ==============================
    path('admin/rooms/', views.manage_rooms, name='manage_rooms'),
    path('admin/rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('admin/rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),

    # ==============================
    # ANNOUNCEMENTS
    # ==============================
    path('admin/announcements/', views.manage_announcements, name='manage_announcements'),

    # ==============================
    # SCHEDULING
    # ==============================
    path('admin/schedules/', views.manage_schedules, name='manage_schedules'),
    path('admin/curriculum/assign_schedule/<int:cs_id>/', views.assign_schedule, name='assign_schedule'),
    path('admin/generate_timetable/', views.generate_timetable, name='generate_timetable'),
    path('admin/validate_slot/', views.validate_slot, name='validate_slot'),
    path('edit_schedule/<int:schedule_id>/', views.edit_schedule, name='edit_schedule'),
    path('delete_schedule/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),


    # ==============================
    #INSTRUCTOR DASHBOARDS
    # ==============================
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),


    # ==============================
    # DYNAMIC AJAX ENDPOINTS
    # ==============================
    path('get_courses/<int:dept_id>/', views.get_courses, name='get_courses'),
    path('get_courses_section/<int:dept_id>/', views.get_courses_section, name='get_courses_section'),
    path('get_sections/<int:course_id>/', views.get_sections, name='get_sections'),
    path('get_sections_by_course/<int:course_id>/', views.get_sections_by_course, name='get_sections_by_course'),
    path('admin/api/subject/<int:subject_id>/', views.get_subject_api, name='get_subject_api'),


    path('public/schedule/', public_schedule_view, name='public_schedule'),
    path('api/room-schedule/<int:room_id>/', views.room_schedule_api, name='room_schedule_api'),
    path('check-room-availability/', views.check_room_availability, name='check_room_availability'),
    path('google409907f111977f19.html', views.google_verification, name='google_verification'),
    path('sitemap.xml/', views.sitemap_view, name='sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),

]
