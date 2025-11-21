from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User,
    Department,
    Course,
    Curriculum,
    Subject,
    Instructor,
    Section,
    Schedule,
)

# ===============================
# ✅ Custom User Admin
# ===============================
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'get_full_name',
        'role',
        'instructor_number',
        'is_approved',
        'is_active',
    )
    list_filter = ('role', 'is_approved', 'is_active')
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email',
        'instructor_number',
    )
    ordering = ('role', 'username')
    readonly_fields = ('last_login', 'date_joined')
    actions = ['approve_users', 'deactivate_users']

    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Additional Info'), {
            'fields': (
                'role',
                'instructor_number',
                'middle_name',
                'is_approved',
            )
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Additional Info'), {
            'fields': (
                'role',
                'instructor_number',
                'middle_name',
                'is_approved',
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    @admin.action(description='Approve selected users')
    def approve_users(self, request, queryset):
        updated = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f"{updated} user(s) approved and activated.")


    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")


# ===============================
# ✅ Department
# ===============================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


# ===============================
# ✅ Course
# ===============================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'department')
    list_filter = ('department',)
    search_fields = ('course_code', 'course_name')


# ===============================
# ✅ Curriculum
# ===============================
@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'is_active', 'created_at')
    list_filter = ('course', 'is_active')
    search_fields = ('name', 'course__course_name')


# ===============================
# ✅ Subject
# ===============================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_code', 'subject_name', 'units', 'lecture_units', 'lab_units')
    search_fields = ('subject_code', 'subject_name')


# ===============================
# ✅ Instructor
# ===============================
@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    list_filter = ('department',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


# ===============================
# ✅ Section
# ===============================
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('section_name', 'course', 'year_level')
    list_filter = ('course', 'year_level')
    search_fields = ('section_name', 'course__course_name')


# ===============================
# ✅ Schedule
# ===============================
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('section', 'subject', 'instructor', 'day', 'room')
    list_filter = ('day', 'section__course')
    search_fields = ('section__section_name', 'subject__subject_code', 'instructor__user__username')
