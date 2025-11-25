# scheduler/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import (
    AdminRegistrationForm,
    InstructorRegistrationForm,
    CustomLoginForm,
    CurriculumSubjectForm,
    CurriculumForm,
    SemesterForm,
    YearLevelForm,
    CourseForm,
    DepartmentForm,
    SubjectForm,
    SchoolYearLevelForm,
)
from .models import Section, Schedule, Subject, Room, Announcement, Curriculum, CurriculumRevision, Instructor, User, Course, YearLevel, Semester, CurriculumSubject, Department, SchoolYearLevel, RoomAvailability
import datetime
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Section 
from django.db.models import Q
from scheduler.models import User, Instructor, Department
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

def get_available_times(room):
    """Get available time slots for a room"""
    occupied_times = []
    for subject in room.subjects.all():
        if subject.start_time and subject.end_time:
            time_str = f"{subject.start_time.strftime('%I:%M %p')} - {subject.end_time.strftime('%I:%M %p')}"
            occupied_times.append(time_str)
    
    if not occupied_times:
        return "All day available"
    
    return f"Occupied: {', '.join(occupied_times[:2])}{'...' if len(occupied_times) > 2 else ''}"

from django.db import models

from django.contrib.auth import get_user_model, authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CustomLoginForm, AdminRegistrationForm, InstructorRegistrationForm
from .models import Instructor

User = get_user_model()

# ---------------- AUTH VIEW (LOGIN & REGISTRATION) ----------------
def auth_view(request):
    # ==============================
    # INIT FORMS
    # ==============================
    login_form = CustomLoginForm(request, data=request.POST or None)
    instructor_form = InstructorRegistrationForm(request.POST or None, prefix='instructor')

    # Check if an admin account already exists
    admin_exists = User.objects.filter(role=User.Role.ADMIN).exists()
    admin_form = None
    if not admin_exists:
        admin_form = AdminRegistrationForm(request.POST or None, prefix='admin')

    # ====================================================
    # 🔐 LOGIN HANDLER
    # ====================================================
    if request.method == 'POST' and 'login_submit' in request.POST:
        role = request.POST.get('role', 'INSTRUCTOR')  # Default to instructor/admin
        login_form = CustomLoginForm(request, data=request.POST)

        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Check correct role
                if user.role != role:
                    messages.error(request, "Incorrect role selected for this account.")
                    return redirect('auth_page')

                # Check approval
                if user.is_instructor() and not user.is_approved:
                    messages.error(request, "Your instructor account is not yet approved by admin.")
                    return redirect('auth_page')
                if user.is_admin() and not user.is_active:
                    messages.error(request, "Admin account is inactive.")
                    return redirect('auth_page')

                login(request, user)
                messages.success(request, f"Welcome, {user.first_name or user.username}!")
                return redirect('home_redirect')
            else:
                messages.error(request, "Invalid username or password.")
                return redirect('auth_page')

    # ====================================================
    # 🧑‍💼 ADMIN REGISTRATION (only if no admin exists)
    # ====================================================
    elif request.method == 'POST' and 'admin_submit' in request.POST and not admin_exists:
        if admin_form.is_valid():
            admin_user = admin_form.save(commit=False)
            admin_user.role = User.Role.ADMIN
            admin_user.is_approved = True
            admin_user.is_active = True
            admin_user.save()
            messages.success(request, "Admin registered successfully. You can now log in.")
            return redirect('auth_page')
        else:
            messages.error(request, f"Error creating Admin account: {admin_form.errors}")

    # ====================================================
    # 👨‍🏫 INSTRUCTOR REGISTRATION
    # ====================================================
    elif request.method == 'POST' and 'instructor_submit' in request.POST:
        if instructor_form.is_valid():
            instructor_user = instructor_form.save(commit=False)
            instructor_user.role = User.Role.INSTRUCTOR
            instructor_user.is_approved = False  # Needs admin approval
            instructor_user.is_active = True
            instructor_user.save()

            # Create instructor profile
            department = instructor_form.cleaned_data.get('department')
            Instructor.objects.create(user=instructor_user, department=department)

            messages.success(request, "Instructor registered successfully! Wait for admin approval.")
            return redirect('auth_page')
        else:
            print("INSTRUCTOR FORM ERRORS:", instructor_form.errors)
            messages.error(request, f"Error creating Instructor account: {instructor_form.errors}")

    # ====================================================
    # 📦 CONTEXT
    # ====================================================
    context = {
        'login_form': login_form,
        'instructor_form': instructor_form,
    }

    # Only send admin_form if no admin exists
    if admin_form:
        context['admin_form'] = admin_form

    return render(request, 'auth/auth.html', context)

# ---------------- HOME REDIRECT AFTER LOGIN ----------------
@login_required
def home_redirect(request):
    user = request.user
    print("DEBUG: Logged in user role:", user.role)  # 👈 Add this

    if user.is_superuser or user.is_admin():
        return redirect('admin_dashboard')
    elif user.is_instructor():
        return redirect('instructor_dashboard')
    return redirect('admin_dashboard')

from django.db.models import Sum
from collections import defaultdict

@login_required
def instructor_dashboard(request):
    # Check if user has an instructor profile
    if not hasattr(request.user, 'instructor_profile'):
        return render(request, 'scheduler/instructor/dashboard.html', {
            'error': "You are not registered as an instructor."
        })

    instructor = request.user.instructor_profile

    # Fetch all schedules for this instructor
    schedules = Schedule.objects.filter(instructor=instructor).select_related(
        'subject', 
        'section', 
        'room', 
        'section__course', 
        'section__course__department',
        'subject__curriculum'
    ).order_by('day', 'time_start')

    print(f"\n{'='*60}")
    print(f"INSTRUCTOR DASHBOARD DEBUG")
    print(f"{'='*60}")
    print(f"Instructor: {instructor.user.get_full_name()}")
    print(f"Total schedules found: {schedules.count()}")
    for sched in schedules:
        print(f"  - {sched.subject.subject_code} | {sched.day} | {sched.time_start}-{sched.time_end} | Section: {sched.section.section_name}")
    print(f"{'='*60}\n")

    # Organize schedules by section, year level, and semester
    section_schedule_groups = []
    schedules_by_section = defaultdict(list)
    
    for sched in schedules:
        # Get semester info from CurriculumSubject
        curriculum_subject = CurriculumSubject.objects.filter(
            subject=sched.subject,
            curriculum=sched.subject.curriculum
        ).select_related('semester__year_level').first()
        
        if curriculum_subject:
            year_level = curriculum_subject.year_level.year
            semester_num = curriculum_subject.semester.semester_number
            semester_name = curriculum_subject.semester.name
        else:
            # Fallback if no curriculum subject found
            year_level = getattr(sched.section, 'year_level', 1)
            semester_num = 1
            semester_name = "1st Semester"
        
        # Group by section, year, and semester
        key = (sched.section, year_level, semester_num, semester_name)
        schedules_by_section[key].append(sched)

    # Sort by year and semester
    sorted_keys = sorted(schedules_by_section.keys(), key=lambda x: (x[1], x[2]))  # Sort by year then semester

    for (section, year_level, semester_num, semester_name), section_schedules in [(k, schedules_by_section[k]) for k in sorted_keys]:
        # Collect unique time slots
        time_slots = sorted(set(
            f"{s.time_start.strftime('%H:%M')}-{s.time_end.strftime('%H:%M')}" 
            for s in section_schedules
        ))

        # Map day -> time_slot -> list of schedules
        days_dict = {
            day: {slot: [] for slot in time_slots} 
            for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        }
        
        for s in section_schedules:
            slot = f"{s.time_start.strftime('%H:%M')}-{s.time_end.strftime('%H:%M')}"
            days_dict[s.day][slot].append(s)

        section_schedule_groups.append({
            'section': section,
            'year_level': year_level,
            'semester_num': semester_num,
            'semester_name': semester_name,
            'slots': time_slots,
            'days': days_dict,
            'total_subjects': len(set(s.subject for s in section_schedules))
        })

    # Summary Cards
    total_subjects = schedules.values('subject').distinct().count()
    total_sections = schedules.values('section').distinct().count()
    total_seconds = sum(
        (sched.time_end.hour * 3600 + sched.time_end.minute * 60) -
        (sched.time_start.hour * 3600 + sched.time_start.minute * 60)
        for sched in schedules
    )
    total_hours = round(total_seconds / 3600, 2)

    # Latest Announcements
    announcements = Announcement.objects.all().order_by('-created_at')[:5]

    context = {
        'instructor': instructor,
        'section_schedule_groups': section_schedule_groups,
        'days_of_week': ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        'total_subjects': total_subjects,
        'total_sections': total_sections,
        'total_hours': total_hours,
        'announcements': announcements,
    }

    return render(request, 'scheduler/instructor/dashboard.html', context)


# ---------------- ADMIN DASHBOARD ----------------
@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    context = {
        'total_instructors': User.objects.filter(role=User.Role.INSTRUCTOR).count(),
        'total_schedules': Schedule.objects.count(),
        'total_subjects': Subject.objects.count(),
        'total_rooms': Room.objects.count(),
        'total_sections': Section.objects.count(),
        'total_prospectus': Curriculum.objects.count(),

        # RECENT DATA
        'recent_instructors': User.objects.filter(role=User.Role.INSTRUCTOR).order_by('-id')[:5],
        'recent_sections': Section.objects.order_by('-id')[:5],
        'recent_subjects': Subject.objects.order_by('-id')[:5],
        'recent_schedules': Schedule.objects.order_by('-id')[:5],
        'recent_rooms': Room.objects.order_by('-id')[:5],
        'recent_curriculums': Curriculum.objects.order_by('-id')[:5],
        'recent_announcements': Announcement.objects.order_by('-created_at')[:5],
    }

    return render(request, 'scheduler/admin/admin_dashboard.html', context)

def edit_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)
    courses = Course.objects.all()

    if request.method == 'POST':
        course_id = request.POST.get('course')
        section_name = request.POST.get('section_name')
        year_level = request.POST.get('year_level')

        if course_id and section_name and year_level:
            section.course_id = course_id
            section.section_name = section_name
            section.year_level = year_level
            section.save()
            messages.success(request, "Section updated successfully!")
            return redirect('manage_sections')
        else:
            messages.error(request, "All fields are required!")

    return render(request, 'scheduler/admin/edit_section.html', {
        'section': section,
        'courses': courses,
    })

def delete_section(request, section_id):
    section = get_object_or_404(Section, id=section_id)

    if request.method == "POST":
        section.delete()
        messages.success(request, f"Section {section.section_name} has been deleted.")
        return redirect("manage_sections")

    return redirect("manage_sections")

# ---------------- USER MANAGEMENT (ADMIN) ----------------
@login_required
def manage_users(request):
    """
    Manage users view - handles bulk actions and single user deletion
    """
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    


    if request.method == "POST":
        action = request.POST.get("action")
        
        # Handle single user deletion from modal
        if action == 'delete_single':
            user_id = request.POST.get("user_id")
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    user_name = f"{user.first_name} {user.last_name}"
                    user.delete()
                    messages.success(request, f"User '{user_name}' deleted successfully.")
                except User.DoesNotExist:
                    messages.error(request, "User not found.")
            else:
                messages.error(request, "Invalid user ID.")
            return redirect('manage_users')
        
        # Handle bulk actions (only if action is provided)
        user_ids = request.POST.getlist("user_ids")
        
        if action:  # Only process if an action was actually selected
            users = User.objects.filter(id__in=user_ids)
            
            if not user_ids:  # Check if any user IDs were selected
                messages.error(request, "Please select at least one user.")
            else:
                user_details = [f"{u.first_name} {u.last_name} ({u.role.title()})" for u in users]
                
                if action == 'activate':
                    inactive_users = users.filter(is_active=False)
                    if inactive_users.exists():
                        inactive_details = [f"{u.first_name} {u.last_name} ({u.role.title()})" for u in inactive_users]
                        inactive_users.update(is_active=True)
                        messages.success(request, f"Activated: {', '.join(inactive_details)}")
                    else:
                        messages.info(request, "No inactive users selected to activate.")
                
                elif action == 'deactivate':
                    active_users = users.filter(is_active=True)
                    if active_users.exists():
                        active_details = [f"{u.first_name} {u.last_name} ({u.role.title()})" for u in active_users]
                        active_users.update(is_active=False)
                        messages.success(request, f"Deactivated: {', '.join(active_details)}")
                    else:
                        messages.info(request, "No active users selected to deactivate.")

                elif action == 'approve':
                    unapproved_users = users.filter(is_approved=False)
                    if unapproved_users.exists():
                        unapproved_details = [f"{u.first_name} {u.last_name} ({u.role.title()})" for u in unapproved_users]
                        unapproved_users.update(is_approved=True)
                        messages.success(request, f"Approved: {', '.join(unapproved_details)}")
                    else:
                        messages.info(request, "No unapproved users selected to approve.")

                elif action == 'delete':
                    messages.success(request, f"Deleted: {', '.join(user_details)}")
                    users.delete()

                else:
                    messages.error(request, "Invalid bulk action.")

        return redirect('manage_users')

    # Pagination
    all_users = User.objects.exclude(is_superuser=True).order_by('-date_joined')
    paginator = Paginator(all_users, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(request, 'scheduler/admin/manage_users.html', {
        'users': users
    })


@login_required
def approve_user(request, user_id):
    """
    Approve a user (for students pending approval)
    """
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    
    user = get_object_or_404(User, id=user_id)
    user.is_approved = True
    user.save()
    messages.success(request, f"User '{user.first_name} {user.last_name}' approved successfully.")
    return redirect('manage_users')


@login_required
def activate_user(request, user_id):
    """
    Activate a user account
    """
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, f"User '{user.first_name} {user.last_name}' activated successfully.")
    return redirect('manage_users')


@login_required
def deactivate_user(request, user_id):
    """
    Deactivate a user account
    """
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, f"User '{user.first_name} {user.last_name}' deactivated successfully.")
    return redirect('manage_users')


@login_required
def view_user_profile(request, user_id):
    """
    View user profile details (optional - if you want a dedicated page)
    This is now handled by the modal, but you can keep this for backward compatibility
    """
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    
    user = get_object_or_404(User, id=user_id)
    return render(request, 'scheduler/admin/view_user.html', {
        'view_user': user
    })

def add_user(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'ADMIN':
            form = AdminRegistrationForm(request.POST)
        elif role == 'INSTRUCTOR':
            form = InstructorRegistrationForm(request.POST)
        else:
            messages.error(request, "Invalid role selected.")
            return redirect('add_user')

        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = True if role in ['ADMIN', 'INSTRUCTOR'] else False
            user.is_active = True if role in ['ADMIN', 'INSTRUCTOR'] else False
            user.save()
            messages.success(request, f"{role.capitalize()} added successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, "Error creating user. Please check your inputs.")
    else:
        form = None  # Form will be selected based on role in the template

    return render(request, 'scheduler/admin/add_user.html', {'form': form})

def edit_user(request, user_id):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'ADMIN':
            form = AdminRegistrationForm(request.POST, instance=user)
        elif role == 'INSTRUCTOR':
            form = InstructorRegistrationForm(request.POST, instance=user)
        else:
            messages.error(request, "Invalid role selected.")
            return redirect('edit_user', user_id=user_id)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = True if role in ['ADMIN', 'INSTRUCTOR'] else user.is_approved
            user.is_active = True if role in ['ADMIN', 'INSTRUCTOR'] else user.is_active
            user.save()
            messages.success(request, f"{role.capitalize()} updated successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, "Error updating user. Please check your inputs.")
    else:
        if user.role == User.Role.ADMIN:
            form = AdminRegistrationForm(instance=user)
        elif user.role == User.Role.INSTRUCTOR:
            form = InstructorRegistrationForm(instance=user)
        else:
            messages.error(request, "Invalid user role.")
            return redirect('manage_users')

    return render(request, 'scheduler/admin/edit_user.html', {'form': form, 'user': user})



@login_required
def delete_user(request, user_id):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.delete()
    messages.warning(request, f"User {username} has been deleted.")
    return redirect('manage_users')


# ---------------- MANAGEMENT LIST PAGES (ADMIN) ----------------
@login_required
def manage_sections(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    departments = Department.objects.all()
    selected_department_id = request.GET.get('department')
    selected_department = Department.objects.filter(id=selected_department_id).first() if selected_department_id else None
    page_number = request.GET.get('page', 1)
    
    # Initialize variables
    sections_by_course = {}
    paginator_obj = None
    
    if selected_department:
        # Get sections for selected department grouped by course
        sections_list = Section.objects.select_related('course', 'course__department').filter(
            course__department=selected_department
        ).order_by('course__course_name', 'section_name')
        
        # Group sections by course
        from itertools import groupby
        sections_grouped = {}
        for course, course_sections in groupby(sections_list, key=lambda x: x.course):
            sections_grouped[course] = list(course_sections)
        
        # Apply pagination to each course (6 sections per page per course)
        for course, course_sections in sections_grouped.items():
            paginator = Paginator(course_sections, 6)
            
            try:
                paginated_sections = paginator.page(page_number)
            except PageNotAnInteger:
                paginated_sections = paginator.page(1)
            except EmptyPage:
                paginated_sections = paginator.page(paginator.num_pages)
            
            sections_by_course[course] = paginated_sections
            if not paginator_obj:  # Use first course's paginator for navigation
                paginator_obj = paginated_sections

    if request.method == 'POST':
        print(f"DEBUG: POST request received with data: {dict(request.POST)}")
        action = request.POST.get('action')
        print(f"DEBUG: Action is: {action}")
        
        # CREATE NEW SECTION
        if action == 'create_section':
            department_id = request.POST.get('department')
            course_id = request.POST.get('course')
            section_name = request.POST.get('section_name')
            year_level = request.POST.get('year_level')

            print(f"DEBUG: Creating section - dept: {department_id}, course: {course_id}, name: {section_name}, year: {year_level}")

            if not department_id:
                messages.error(request, 'Please select a department.')
                return redirect('manage_sections')
            if not course_id:
                messages.error(request, 'Please select a course.')
                return redirect('manage_sections')
            if not section_name:
                messages.error(request, 'Please enter a section name.')
                return redirect('manage_sections')

            try:
                course = get_object_or_404(Course, id=course_id)
                Section.objects.create(
                    course=course, 
                    section_name=section_name, 
                    year_level=int(year_level) if year_level else 1
                )
                messages.success(request, f'Section "{section_name}" created successfully!')
            except Exception as e:
                messages.error(request, f'Error creating section: {str(e)}')
            return redirect('manage_sections')
        
        # EDIT SECTION
        elif request.POST.get('action') == 'edit_section':
            section_id = request.POST.get('section_id')
            course_id = request.POST.get('course')
            section_name = request.POST.get('section_name')
            year_level = request.POST.get('year_level')

            if section_id and course_id and section_name:
                section = get_object_or_404(Section, id=section_id)
                course = get_object_or_404(Course, id=course_id)
                
                section.course = course
                section.section_name = section_name
                section.year_level = year_level or 1
                section.save()
                
                messages.success(request, f'Section "{section_name}" updated successfully!')
                return redirect('manage_sections')
        
        # DELETE SECTION
        elif request.POST.get('action') == 'delete_section':
            section_id = request.POST.get('section_id')
            
            if section_id:
                section = get_object_or_404(Section, id=section_id)
                section_name = section.section_name
                section.delete()
                messages.success(request, f'Section "{section_name}" deleted successfully!')
                return redirect('manage_sections')
        
        # FALLBACK - catch any unhandled POST
        else:
            print(f"DEBUG: Unhandled POST action: {action}")
            messages.warning(request, f'Unknown action received: {action}. Please try again.')
            return redirect('manage_sections')
    
    return render(request, 'scheduler/admin/manage_sections.html', {
        'departments': departments,
        'selected_department': selected_department,
        'sections_by_course': sections_by_course,
        'paginator': paginator_obj,
    })


def get_sections(request, course_id):
    sections = Section.objects.filter(course_id=course_id).values('id', 'section_name')
    return JsonResponse(list(sections), safe=False)


def get_sections_by_course(request, course_id):
    department_id = request.GET.get('department_id')
    sections = Section.objects.filter(course_id=course_id)
    if department_id:
        sections = sections.filter(course__department_id=department_id)
    return JsonResponse(list(sections.values('id', 'section_name')), safe=False)


@login_required
def manage_schedules(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')
    schedules = Schedule.objects.all()
    return render(request, 'scheduler/admin/manage_schedules.html', {'schedules': schedules})


@login_required
def manage_subjects(request):
    # --- Get all query parameters ---
    department_id = request.GET.get('department')
    department_search = request.GET.get('department_search', '').strip()
    school_year_query = request.GET.get('school_year', '').strip()
    section_query = request.GET.get('section', '').strip()
    instructor_query = request.GET.get('instructor', '').strip()
    subject_query = request.GET.get('subject', '').strip()
    room_query = request.GET.get('room', '').strip()
    subject_code_query = request.GET.get('subject_code', '').strip()

    # --- Base queryset ---
    subjects = Subject.objects.select_related(
        'section',
        'section__course',
        'room',
        'instructor',
        'instructor__user'
    ).prefetch_related(
        'curriculumsubject_set__semester__year_level'
    ).all()

    # --- Department filter (handle both ID and search) ---
    selected_department = None
    if department_id:
        selected_department = Department.objects.filter(id=department_id).first()
        subjects = subjects.filter(section__course__department_id=department_id)
    elif department_search:
        # Search by department name
        selected_department = Department.objects.filter(
            name__icontains=department_search
        ).first()
        if selected_department:
            subjects = subjects.filter(section__course__department=selected_department)

    # --- School year filter ---
    if school_year_query:
        subjects = subjects.filter(section__year_level__icontains=school_year_query)

    # --- Section filter ---
    if section_query:
        subjects = subjects.filter(section__section_name__icontains=section_query)

    # --- Instructor filter ---
    if instructor_query:
        # Split name into words (e.g., "Arian Maala" → ["Arian", "Maala"])
        name_parts = instructor_query.split()

        # Build dynamic query for all name parts
        instructor_filter = Q(instructor__user__first_name__icontains=instructor_query) | Q(instructor__user__last_name__icontains=instructor_query)
        if len(name_parts) > 1:
            for part in name_parts:
                instructor_filter |= Q(instructor__user__first_name__icontains=part) | Q(instructor__user__last_name__icontains=part)

        subjects = subjects.filter(instructor_filter)

        # Filter to instructors only under the selected department
        if selected_department:
            subjects = subjects.filter(instructor__department=selected_department)

    # --- Subject name filter ---
    if subject_query:
        subjects = subjects.filter(subject_name__icontains=subject_query)

    # --- Room filter ---
    if room_query:
        subjects = subjects.filter(room__room_name__icontains=room_query)

    # --- Subject code filter ---
    if subject_code_query:
        subjects = subjects.filter(subject_code__icontains=subject_code_query)

    # --- Prepare subjects with year and semester metadata ---
    subjects_with_metadata = []
    for subject in subjects.distinct():
        # Get the CurriculumSubject relationship to find year and semester
        curriculum_subject = subject.curriculumsubject_set.select_related(
            'semester__year_level'
        ).first()
        
        if curriculum_subject and curriculum_subject.semester:
            year_level_display = curriculum_subject.semester.year_level.year
            semester_name = curriculum_subject.semester.name
            semester_number = curriculum_subject.semester.semester_number
        else:
            year_level_display = None
            semester_name = "No Semester"
            semester_number = 999  # For sorting purposes
        
        # Add metadata as dynamic attributes
        subject.year_level_display = year_level_display
        subject.semester_display = semester_name
        subject.semester_number = semester_number
        subjects_with_metadata.append(subject)

    # Sort by section, year_level, and semester
    subjects_with_metadata.sort(key=lambda x: (
        x.section.section_name if x.section else '',
        x.year_level_display if x.year_level_display else 999,
        x.semester_number
    ))

    # --- Dropdowns data for datalists ---
    departments = Department.objects.all()
    
    # Get school years from sections
    school_years = Section.objects.values_list('year_level', flat=True).distinct().order_by('year_level')
    
    # Get section names
    if selected_department:
        sections = Section.objects.filter(
            course__department=selected_department
        ).values_list('section_name', flat=True).distinct().order_by('section_name')
    else:
        sections = Section.objects.values_list('section_name', flat=True).distinct().order_by('section_name')

    # --- Instructor list (filtered by department if selected) ---
    if selected_department:
        instructors = Instructor.objects.filter(department=selected_department).select_related('user')
    else:
        instructors = Instructor.objects.all().select_related('user')

    # --- Context ---
    context = {
        'subjects': subjects_with_metadata,
        'departments': departments,
        'selected_department': selected_department,
        'school_years': school_years,
        'sections': sections,
        'instructors': instructors,
    }

    return render(request, 'scheduler/admin/manage_subjects.html', context)

@login_required
def delete_subject(request):
    """
    Delete a subject from the database
    """
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        
        if subject_id:
            try:
                # Get the subject or return 404 if not found
                subject = get_object_or_404(Subject, id=subject_id)
                
                # Store subject info before deletion for the success message
                subject_name = subject.subject_name
                subject_code = subject.subject_code
                
                # Delete the subject
                subject.delete()
                
                # Success message
                messages.success(
                    request, 
                    f'Subject "{subject_code} - {subject_name}" has been successfully deleted.'
                )
                
            except Subject.DoesNotExist:
                messages.error(request, 'Subject not found.')
            except Exception as e:
                messages.error(request, f'Error deleting subject: {str(e)}')
        else:
            messages.error(request, 'No subject ID provided.')
    
    # Redirect back to manage_subjects with the current filters
    # Preserve the department filter if it exists
    department_id = request.GET.get('department', '')
    if department_id:
        return redirect(f'/manage-subjects/?department={department_id}')
    
    return redirect('manage_subjects')


# Alternative version if you want to preserve ALL filters:
@login_required
def delete_subject_preserve_filters(request):
    """
    Delete a subject and preserve all filter parameters
    """
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        
        if subject_id:
            try:
                subject = get_object_or_404(Subject, id=subject_id)
                subject_name = subject.subject_name
                subject_code = subject.subject_code
                subject.delete()
                
                messages.success(
                    request, 
                    f'Subject "{subject_code} - {subject_name}" has been successfully deleted.'
                )
                
            except Subject.DoesNotExist:
                messages.error(request, 'Subject not found.')
            except Exception as e:
                messages.error(request, f'Error deleting subject: {str(e)}')
        else:
            messages.error(request, 'No subject ID provided.')
    
    # Get all query parameters from the request
    query_params = request.GET.urlencode()
    
    # Redirect back with all filter parameters preserved
    if query_params:
        return redirect(f'/manage-subjects/?{query_params}')
    
    return redirect('manage_subjects')

@login_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        subject.subject_code = request.POST.get('subject_code')
        subject.subject_name = request.POST.get('subject_name')
        subject.prerequisite = request.POST.get('prerequisite')
        subject.lecture_units = request.POST.get('lecture_units')
        subject.lab_units = request.POST.get('lab_units')
        subject.units = request.POST.get('units')
        subject.time = request.POST.get('time')
        subject.day = request.POST.get('day')
        subject.room = request.POST.get('room')
        subject.section = request.POST.get('section')

        # ✅ handle instructor properly (convert from id → instance)
        instructor_id = request.POST.get('instructor')
        if instructor_id:
            subject.instructor = Instructor.objects.filter(id=instructor_id).first()
        else:
            subject.instructor = None

        subject.save()
        messages.success(request, f"Subject '{subject.subject_name}' updated successfully!")

    return redirect('manage_curriculum')


@login_required
def edit_manage_subjects(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        subject.subject_code = request.POST.get('subject_code')
        subject.subject_name = request.POST.get('subject_name')
        subject.prerequisite = request.POST.get('prerequisite')
        subject.lecture_units = request.POST.get('lecture_units')
        subject.lab_units = request.POST.get('lab_units')
        subject.units = request.POST.get('units')
        subject.save()
        messages.success(request, f"Subject '{subject.subject_name}' updated successfully!")

    return redirect('manage_subjects')



from django.http import JsonResponse

@login_required
def get_subject_api(request, subject_id):
    from django.http import JsonResponse
    subject = get_object_or_404(Subject, id=subject_id)
    data = {
        "id": subject.id,
        "subject_code": subject.subject_code,
        "subject_name": subject.subject_name,
        "prerequisite": subject.prerequisite or "",
        "lecture_units": subject.lecture_units,
        "lab_units": subject.lab_units,
        "units": subject.units,
        "time": subject.time or "",
        "day": subject.day or "",
        "room": subject.room or "",
        "section": subject.section or "",
        "instructor_id": subject.instructor.id if subject.instructor else None,  # ✅ correct
    }
    return JsonResponse(data)


@login_required
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject_name = subject.subject_name
    subject.delete()
    messages.success(request, f"Subject {subject_name} deleted successfully!")
    return redirect('manage_curriculum')



@login_required
def manage_instructors(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # =========================
    # ACCESS CONTROL
    # =========================
    if not request.user.is_admin() and not request.user.is_superuser:
        messages.error(request, "Access denied. Only admins can manage instructors.")
        return redirect('home_redirect')

    # =========================
    # SELECTION HANDLING
    # =========================
    selected_department_id = request.GET.get('department')
    selected_department = None
    page_number = request.GET.get('page', 1)

    if selected_department_id:
        selected_department = Department.objects.filter(id=selected_department_id).first()

    # =========================
    # DATA FETCHING
    # =========================
    departments = Department.objects.all().order_by('name')

    # For dropdown — only users not yet assigned as instructor
    available_users = User.objects.filter(
        role=User.Role.INSTRUCTOR,
        is_active=True
    ).exclude(
        id__in=Instructor.objects.values_list('user_id', flat=True)
    ).order_by('first_name', 'last_name')

    # =========================
    # POST HANDLERS
    # =========================
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "add_instructor":
            user_id = request.POST.get("user")
            department_id = request.POST.get("department")

            if not user_id or not department_id:
                messages.error(request, "Please select both a user and a department.")
                return redirect('manage_instructors')

            try:
                user = User.objects.get(id=user_id)
                department = Department.objects.get(id=department_id)
            except (User.DoesNotExist, Department.DoesNotExist):
                messages.error(request, "Invalid selection.")
                return redirect('manage_instructors')

            # Create instructor if not exists
            instructor, created = Instructor.objects.get_or_create(user=user)
            instructor.department = department
            instructor.save()

            if created:
                messages.success(request, f"✅ {user.get_full_name()} added as instructor in {department.name}.")
            else:
                messages.info(request, f"ℹ️ {user.get_full_name()} already exists. Department updated to {department.name}.")

            return redirect('manage_instructors')
        
        elif action == "delete_instructor":
            instructor_id = request.POST.get("instructor_id")
            try:
                instructor = Instructor.objects.get(id=instructor_id)
                name = instructor.user.get_full_name()
                instructor.delete()
                messages.success(request, f"🗑️ Instructor '{name}' removed successfully.")
            except Exception as e:
                messages.error(request, f"❌ Failed to remove instructor: {e}")
            return redirect('manage_instructors')

    # =========================
    # ORGANIZE INSTRUCTORS BY DEPARTMENT
    # =========================
    instructors_by_department = {}
    paginator_obj = None
    
    if selected_department:
        # Query instructors for selected department
        instructors = (
            Instructor.objects.select_related('user', 'department')
            .filter(department=selected_department)
            .order_by('user__last_name', 'user__first_name')
        )
        
        dept_name = selected_department.name
        instructor_list = list(instructors)
        
        # Apply pagination - 6 instructors per page
        paginator = Paginator(instructor_list, 6)
        
        try:
            paginated_instructors = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_instructors = paginator.page(1)
        except EmptyPage:
            paginated_instructors = paginator.page(paginator.num_pages)
        
        instructors_by_department[dept_name] = paginated_instructors
        paginator_obj = paginated_instructors

    # =========================
    # CONTEXT PREPARATION
    # =========================
    context = {
        'departments': departments,
        'selected_department': selected_department,
        'instructors_by_department': instructors_by_department,
        'available_users': available_users,
        'paginator': paginator_obj,
    }

    return render(request, 'scheduler/admin/manage_instructors.html', context)



@login_required
def delete_instructor(request, instructor_id):
    # Only admins
    if not request.user.is_admin() and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    if request.method == 'POST':
        instructor = get_object_or_404(Instructor, id=instructor_id)
        user = instructor.user
        # remove instructor record
        instructor.delete()
        messages.success(request, f"{user.get_full_name() or user.username} removed from instructors.")
    return redirect('manage_instructors')


# Manage rooms page
@login_required
def manage_rooms(request):
    from scheduler.models import Subject
    from django.db.models import Count
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    departments = Department.objects.all().order_by("name")

    # Always include floors 1–5
    existing_floors = list(Room.objects.values_list("floor", flat=True).distinct())
    floors = sorted(set([1, 2, 3, 4, 5] + existing_floors))

    # Filters
    selected_department = request.GET.get("department")
    selected_floor = request.GET.get("floor")
    page_number = request.GET.get("page", 1)

    # POST actions
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_room":
            room_name = request.POST.get("room_name")
            capacity = request.POST.get("capacity")
            room_type = request.POST.get("room_type")
            floor = request.POST.get("floor")
            department_id = request.POST.get("department")

            try:
                department = Department.objects.filter(id=department_id).first() if department_id else None
                Room.objects.create(
                    room_name=room_name,
                    capacity=capacity,
                    room_type=room_type,
                    floor=floor,
                    department=department,
                )
                messages.success(request, f"✅ Room '{room_name}' added successfully.")
            except Exception as e:
                messages.error(request, f"❌ Failed to add room: {e}")

            return redirect("manage_rooms")

        elif action == "delete_room":
            room_id = request.POST.get("room_id")
            try:
                room = Room.objects.get(id=room_id)
                name = room.room_name
                room.delete()
                messages.success(request, f"🗑️ Room '{name}' deleted successfully.")
            except Exception as e:
                messages.error(request, f"❌ Failed to delete room: {e}")
            return redirect("manage_rooms")

    # Organize rooms by department with pagination
    rooms_by_department = {}
    paginator_obj = None
    
    if selected_department:
        # Query rooms
        rooms = Room.objects.select_related("department").annotate(
            schedule_count=Count('subjects')
        ).filter(department_id=selected_department).order_by("floor", "room_name")
        
        if selected_floor:
            rooms = rooms.filter(floor=selected_floor)

        # Get department name
        dept = Department.objects.filter(id=selected_department).first()
        dept_name = dept.name if dept else "Unknown Department"

        room_list = []
        for room in rooms:
            # Corrected: order_by day + start_time
            subjects = room.subjects.select_related(
                "instructor__user", "section"
            ).all().order_by("day", "start_time")

            room.schedule_count = subjects.count()

            room.subjects_using = [
                {
                    "subject_code": s.subject_code,
                    "subject_name": s.subject_name,
                    "section": s.section.section_name if s.section else "N/A",
                    "day": s.get_day_display() if hasattr(s, 'get_day_display') else (s.day or "—"),
                    "time": (
                        f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"
                        if s.start_time and s.end_time else "—"
                    ),
                    "instructor": (
                        s.instructor.user.get_full_name()
                        if s.instructor and s.instructor.user
                        else "No Instructor"
                    ),
                }
                for s in subjects
            ]

            room_list.append(room)
        
        # Apply pagination - 6 rooms per page
        paginator = Paginator(room_list, 6)
        
        try:
            paginated_rooms = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_rooms = paginator.page(1)
        except EmptyPage:
            paginated_rooms = paginator.page(paginator.num_pages)
        
        rooms_by_department[dept_name] = paginated_rooms
        paginator_obj = paginated_rooms

    context = {
        "departments": departments,
        "floors": floors,
        "selected_department": selected_department,
        "selected_floor": selected_floor,
        "rooms_by_department": rooms_by_department,
        "paginator": paginator_obj,
    }

    return render(request, "scheduler/admin/manage_rooms.html", context)


# API endpoint for room schedule modal
@login_required
def room_schedule_api(request, room_id):
    try:
        room = Room.objects.get(id=room_id)
        subjects = room.subjects.select_related(
            'instructor__user', 'section'
        ).all().order_by('day', 'start_time')

        schedule_data = []
        for s in subjects:
            schedule_data.append({
                'day': s.get_day_display() if hasattr(s, 'get_day_display') else (s.day or 'N/A'),
                'time': (
                    f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"
                    if s.start_time and s.end_time else "N/A"
                ),
                'subject_code': s.subject_code,
                'subject_name': s.subject_name,
                'section': s.section.section_name if s.section else 'N/A',
                'instructor': s.instructor.user.get_full_name() if s.instructor else 'N/A'
            })

        return JsonResponse(schedule_data, safe=False)

    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API endpoint for checking room availability
@login_required
def check_room_availability(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        days = data.get('days', [])
        
        if not all([room_id, start_time, end_time, days]):
            return JsonResponse({'available': False, 'error': 'Missing parameters'})
        
        room = Room.objects.get(id=room_id)
        
        # Convert time strings to time objects
        from datetime import datetime
        start_time_obj = datetime.strptime(start_time, '%I:%M %p').time()
        end_time_obj = datetime.strptime(end_time, '%I:%M %p').time()
        
        # Check for conflicts
        for day in days:
            conflicts = Subject.objects.filter(
                room=room,
                day__icontains=day,
                start_time__lt=end_time_obj,
                end_time__gt=start_time_obj
            )
            
            if conflicts.exists():
                return JsonResponse({'available': False})
        
        return JsonResponse({'available': True})
        
    except Room.DoesNotExist:
        return JsonResponse({'available': False, 'error': 'Room not found'})
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)})

# Edit room
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == "POST":
        room.room_name = request.POST.get("room_name")
        room.capacity = request.POST.get("capacity")
        room.room_type = request.POST.get("room_type")
        room.save()
        messages.success(request, "Room updated successfully!")
        return redirect("manage_rooms")

    return render(request, "scheduler/admin/edit_room.html", {"room": room})

# Delete room
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    room.delete()
    messages.success(request, "Room deleted successfully!")
    return redirect("manage_rooms")


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (
    Department, Course, Curriculum, SchoolYearLevel,
    YearLevel, Semester, Subject, CurriculumSubject, Instructor
)
from .forms import (
    DepartmentForm, CourseForm, CurriculumForm,
    SubjectForm, SchoolYearLevelForm
)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (
    Department, Course, Curriculum, Section, Subject,
    YearLevel, Semester, CurriculumSubject, Room, Instructor, SchoolYearLevel
)
from .forms import DepartmentForm, CourseForm, CurriculumForm, SchoolYearLevelForm, SubjectForm
from django.core.exceptions import ValidationError


@login_required
def manage_curriculum(request):

    if request.method == 'POST':
        print("\n" + "="*60)
        print("POST REQUEST RECEIVED")
        print("Action:", request.POST.get('action'))
        print("All POST data:")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        print("="*60 + "\n")
    # =========================
    # SELECTION HANDLING
    # =========================
    selected_curriculum_id = request.GET.get('curriculum')
    selected_section_id = request.GET.get('section')

    selected_curriculum = (
        Curriculum.objects.filter(id=selected_curriculum_id)
        .select_related('course__department')
        .first()
        if selected_curriculum_id else None
    )
    selected_section = (
        Section.objects.filter(id=selected_section_id).first()
        if selected_section_id else None
    )

    selected_year = int(request.GET.get('year', 1))
    selected_semester = int(request.GET.get('semester', 1))

    # =========================
    # INITIALIZE FORMS
    # =========================
    department_form = DepartmentForm()
    course_form = CourseForm()
    curriculum_form = CurriculumForm()
    schoolyear_form = SchoolYearLevelForm()
    subject_form = SubjectForm(curriculum=selected_curriculum, semester=selected_semester)

    # =========================
    # AVAILABLE INSTRUCTORS AND ROOMS
    # =========================
    if selected_curriculum:
        current_department = selected_curriculum.course.department

        instructors_same_dept = Instructor.objects.filter(
            department=current_department
        ).select_related("user").order_by("user__first_name", "user__last_name")

        instructors_other = Instructor.objects.exclude(
            department=current_department
        ).select_related("user", "department").order_by("department__name", "user__first_name")

        assign_instructors = {
            'current_department': {'name': current_department.name, 'instructors': instructors_same_dept},
            'other_departments': instructors_other
        }

        from django.db.models import Count
        rooms_same_dept = Room.objects.filter(department=current_department).annotate(
            schedule_count=Count('subjects')
        ).prefetch_related('subjects').order_by('room_name')
        rooms_other = Room.objects.exclude(department=current_department).select_related('department').annotate(
            schedule_count=Count('subjects')
        ).prefetch_related('subjects').order_by('department__name', 'room_name')
        
        # Add available times for each room
        for room in rooms_same_dept:
            room.available_times = get_available_times(room)
        for room in rooms_other:
            room.available_times = get_available_times(room)

        available_rooms = {
            'current_department': {'name': current_department.name, 'rooms': rooms_same_dept},
            'other_departments': rooms_other
        }
    else:
        assign_instructors = {
            'current_department': None,
            'other_departments': Instructor.objects.select_related("user", "department").order_by("department__name")
        }
        from django.db.models import Count
        rooms_other = Room.objects.select_related('department').annotate(
            schedule_count=Count('subjects')
        ).prefetch_related('subjects').order_by('department__name', 'room_name')
        
        for room in rooms_other:
            room.available_times = get_available_times(room)
            
        available_rooms = {
            'current_department': None,
            'other_departments': rooms_other
        }

    # =========================
    # HANDLE POST REQUESTS
    # =========================
    if request.method == 'POST':
        action = request.POST.get('action')

        # -------------------------------
        # ADD DEPARTMENT
        # -------------------------------
        if action == 'add_department':
            department_form = DepartmentForm(request.POST)
            if department_form.is_valid():
                code = department_form.cleaned_data['code']
                name = department_form.cleaned_data['name']

                if Department.objects.filter(code__iexact=code).exists():
                    messages.error(request, f"Department code '{code}' already exists.")
                elif Department.objects.filter(name__iexact=name).exists():
                    messages.error(request, f"Department name '{name}' already exists.")
                else:
                    department_form.save()
                    messages.success(request, f"Department '{name}' added successfully!")
                    return redirect('manage_curriculum')
            else:
                for field, errors in department_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")

        # -------------------------------
        # ADD COURSE
        # -------------------------------
        elif action == 'add_course':
            course_form = CourseForm(request.POST)
            if course_form.is_valid():
                department = course_form.cleaned_data.get('department')
                course_code = course_form.cleaned_data.get('course_code')
                course_name = course_form.cleaned_data.get('course_name')

                if Course.objects.filter(department=department, course_code__iexact=course_code).exists():
                    messages.error(request, f"Course code '{course_code}' already exists in {department.name}.")
                elif Course.objects.filter(department=department, course_name__iexact=course_name).exists():
                    messages.error(request, f"Course name '{course_name}' already exists in {department.name}.")
                else:
                    course_form.save()
                    messages.success(request, f"Course '{course_name}' added successfully!")
                    return redirect('manage_curriculum')

        # -------------------------------
        # ADD CURRICULUM
        # -------------------------------
        elif action == 'add_curriculum':
            curriculum_form = CurriculumForm(request.POST)
            if curriculum_form.is_valid():
                course = curriculum_form.cleaned_data.get('course')
                name = curriculum_form.cleaned_data.get('name')

                if Curriculum.objects.filter(course=course, name__iexact=name).exists():
                    messages.error(request, f"A curriculum named '{name}' already exists for '{course.course_name}'.")
                else:
                    new_curriculum = curriculum_form.save()
                    messages.success(request, f"Curriculum '{new_curriculum.name}' for '{course.course_name}' created successfully!")
                    return redirect('manage_curriculum')

        # -------------------------------
        # ADD SCHOOL YEAR LEVEL
        # -------------------------------
        elif action == 'add_school_year_level':
            schoolyear_form = SchoolYearLevelForm(request.POST)
            if schoolyear_form.is_valid():
                curriculum = schoolyear_form.cleaned_data.get('curriculum')
                school_year = schoolyear_form.cleaned_data.get('school_year')

                if SchoolYearLevel.objects.filter(curriculum=curriculum, school_year__iexact=school_year).exists():
                    messages.error(request, f"School year level '{school_year}' already exists for this curriculum.")
                else:
                    new_sy = schoolyear_form.save()
                    messages.success(request, f"School year level '{new_sy.school_year}' added to '{curriculum.name}'.")
                    return redirect(f'{request.path}?curriculum={curriculum.id}')

        # -------------------------------
        # EDIT SUBJECT
        # -------------------------------
        elif action == 'edit_subject':
            subject_id = request.POST.get('subject_id')
            curriculum_id = request.POST.get('curriculum_id')
            section_id = request.POST.get('section_id')

            if not subject_id:
                messages.error(request, "Invalid subject ID.")
                return redirect('manage_curriculum')

            subject = get_object_or_404(Subject, id=subject_id)
            curriculum = get_object_or_404(Curriculum, id=curriculum_id)
            section = get_object_or_404(Section, id=section_id)

            selected_year = int(request.POST.get('year', 1))
            selected_semester = int(request.POST.get('semester_choice', 1))

            subject_form = SubjectForm(request.POST, instance=subject, curriculum=curriculum)
            if subject_form.is_valid():
                subject = subject_form.save(commit=False)
                subject.curriculum = curriculum
                subject.section = section
                subject.save()

                # Delete old schedules
                Schedule.objects.filter(subject=subject).delete()

                # Create new schedules
                DAY_MAPPING = {
                    "Monday": Schedule.Day.MON,
                    "Tuesday": Schedule.Day.TUE,
                    "Wednesday": Schedule.Day.WED,
                    "Thursday": Schedule.Day.THU,
                    "Friday": Schedule.Day.FRI,
                    "Saturday": Schedule.Day.SAT,
                    "Sunday": Schedule.Day.SUN,
                }

                if subject.day and subject.start_time and subject.end_time and subject.instructor and subject.room:
                    days_list = [d.strip() for d in subject.day.split(",")]
                    for day_name in days_list:
                        day_code = DAY_MAPPING.get(day_name)
                        if day_code:
                            try:
                                Schedule.objects.create(
                                    section=section,
                                    subject=subject,
                                    instructor=subject.instructor,
                                    room=subject.room,
                                    day=day_code,
                                    time_start=subject.start_time,
                                    time_end=subject.end_time,
                                )
                            except ValidationError as e:
                                print(f"Could not create schedule for {day_name}: {e}")

                messages.success(request, f"Subject '{subject.subject_name}' updated successfully!")
                return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')

        # -------------------------------
        # ADD SUBJECT
        # -------------------------------
        elif action == 'add_subject':
            curriculum_id = request.POST.get('curriculum_id')
            section_id = request.POST.get('section_id')

            if not curriculum_id or not section_id:
                messages.error(request, "Please select both curriculum and section before adding a subject.")
                return redirect('manage_curriculum')

            curriculum = get_object_or_404(Curriculum, id=curriculum_id)
            section = get_object_or_404(Section, id=section_id)

            selected_year = int(request.POST.get('year', 1))
            selected_semester = int(request.POST.get('semester_choice', 1))

            subject_form = SubjectForm(request.POST, curriculum=curriculum)
            if subject_form.is_valid():
                subject = subject_form.save(commit=False)
                subject.curriculum = curriculum
                subject.section = section

                subject_name = subject_form.cleaned_data.get('subject_name') or subject.subject_name
                start_time = subject_form.cleaned_data.get('start_time') or subject.start_time
                end_time = subject_form.cleaned_data.get('end_time') or subject.end_time
                day = subject_form.cleaned_data.get('day') or subject.day
                room = subject_form.cleaned_data.get('room') or subject.room
                instructor = subject_form.cleaned_data.get('instructor') or subject.instructor

                if not start_time or not end_time:
                    messages.error(request, "Start time and end time are required for schedule conflict checking.")
                    return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}')

                if not day:
                    messages.error(request, "Day selection is required for schedule conflict checking.")
                    return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}')

                selected_days = [d.strip() for d in day.split(',') if d.strip()]

                # Year & Semester objects
                year_obj, _ = YearLevel.objects.get_or_create(curriculum=curriculum, year=selected_year)
                sem_name = {1: '1st Semester', 2: '2nd Semester', 3: 'Summer'}.get(selected_semester, f'Semester {selected_semester}')
                sem_obj, _ = Semester.objects.get_or_create(year_level=year_obj, semester_number=selected_semester, defaults={'name': sem_name})

                # 1️⃣ Prevent duplicate subject in same section & semester
                if Subject.objects.filter(
                    section=section,
                    subject_name__iexact=subject_name,
                    curriculumsubject__semester=sem_obj
                ).exists():
                    messages.error(request, f"Subject '{subject_name}' already exists under section '{section.section_name}' in this semester.")
                    return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')

                # 2️⃣ Prevent room conflict (across all sections)
                if room:
                    room_conflicts = Subject.objects.filter(room=room).exclude(id=subject.id)
                    for existing_subject in room_conflicts:
                        existing_days = [d.strip() for d in existing_subject.day.split(',') if d.strip()]
                        overlapping_days = [d for d in selected_days if d in existing_days]
                        if overlapping_days:
                            time_overlap = start_time < existing_subject.end_time and end_time > existing_subject.start_time
                            if time_overlap:
                                conflict_section = existing_subject.section.section_name if existing_subject.section else "Unknown Section"
                                conflict_curriculum = existing_subject.curriculum.name if existing_subject.curriculum else "Unknown Curriculum"
                                messages.error(
                                    request,
                                    f"Room '{room.room_name}' is already occupied by '{existing_subject.subject_name}' "
                                    f"(Section: {conflict_section}, Curriculum: {conflict_curriculum}) "
                                    f"on {', '.join(overlapping_days)} "
                                    f"from {existing_subject.start_time.strftime('%I:%M %p')} to {existing_subject.end_time.strftime('%I:%M %p')}."
                                )
                                return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')
                    
                # 3️⃣ Prevent instructor conflict (across all sections)
                if instructor:
                    instructor_conflicts = Subject.objects.filter(instructor=instructor).exclude(id=subject.id)
                    for existing_subject in instructor_conflicts:
                        existing_days = [d.strip() for d in existing_subject.day.split(',') if d.strip()]
                        overlapping_days = [d for d in selected_days if d in existing_days]
                        if overlapping_days:
                            time_overlap = start_time < existing_subject.end_time and end_time > existing_subject.start_time
                            if time_overlap:
                                conflict_section = existing_subject.section.section_name if existing_subject.section else "Unknown Section"
                                conflict_curriculum = existing_subject.curriculum.name if existing_subject.curriculum else "Unknown Curriculum"
                                messages.error(
                                    request,
                                    f"Instructor '{instructor.user.get_full_name()}' is already teaching '{existing_subject.subject_name}' "
                                    f"(Section: {conflict_section}, Curriculum: {conflict_curriculum}) "
                                    f"on {', '.join(overlapping_days)} "
                                    f"from {existing_subject.start_time.strftime('%I:%M %p')} to {existing_subject.end_time.strftime('%I:%M %p')}."
                                )
                                return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')

                # ✅ Save subject
                subject.section = section 
                subject.save()
                CurriculumSubject.objects.get_or_create(
                    curriculum=curriculum,
                    year_level=year_obj,
                    semester=sem_obj,
                    subject=subject,
                    defaults={'is_required': True, 'order': 0}
                )

                messages.success(request, f"Subject '{subject.subject_name}' added under section '{section.section_name}' successfully! Remember to click 'Assign Schedule' to finalize schedules.")
                return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')
            
        # -------------------------------
        # DELETE SUBJECT
        # -------------------------------
        elif action == 'delete_subject':
            subject_id = request.POST.get('subject_id')
            curriculum_id = request.POST.get('curriculum_id')
            section_id = request.POST.get('section_id')
            
            if not subject_id:
                messages.error(request, "Invalid subject ID.")
                return redirect('manage_curriculum')
            subject = get_object_or_404(Subject, id=subject_id)
            subject_name = subject.subject_name
            
            # Delete associated schedules first
            Schedule.objects.filter(subject=subject).delete()
            
            # Then delete the subject
            subject.delete()

            messages.success(request, f"Subject '{subject_name}' and its schedules deleted successfully!")
            return redirect(f'{request.path}?curriculum={curriculum_id}&section={section_id}')
        

        # -------------------------------
        # AUTO-ASSIGN ALL SCHEDULES
        # -------------------------------
        elif action == "auto_assign_semester":
            curriculum_id = request.POST.get("curriculum_id")
            section_id = request.POST.get("section_id")

            curriculum = get_object_or_404(Curriculum, id=curriculum_id)
            section = get_object_or_404(Section, id=section_id)

            # Get year and semester from GET params
            selected_year = int(request.GET.get('year', 1))
            selected_semester = int(request.GET.get('semester', 1))
            
            year_obj, _ = YearLevel.objects.get_or_create(curriculum=curriculum, year=selected_year)
            sem_name = {1: '1st Semester', 2: '2nd Semester', 3: 'Summer'}.get(selected_semester)
            sem_obj, _ = Semester.objects.get_or_create(
                year_level=year_obj, 
                semester_number=selected_semester, 
                defaults={'name': sem_name}
            )

            # Get subjects through CurriculumSubject relationship
            curriculum_subjects = CurriculumSubject.objects.filter(
                curriculum=curriculum,
                semester=sem_obj,
                subject__section=section
            ).select_related('subject')

            subjects = [cs.subject for cs in curriculum_subjects]

            # Map full day names to Schedule.Day codes
            DAY_MAPPING = {
                "Monday": Schedule.Day.MON,
                "Tuesday": Schedule.Day.TUE,
                "Wednesday": Schedule.Day.WED,
                "Thursday": Schedule.Day.THU,
                "Friday": Schedule.Day.FRI,
                "Saturday": Schedule.Day.SAT,
                "Sunday": Schedule.Day.SUN,
            }

            skipped_subjects = []

            for subject in subjects:
                if not all([subject.instructor, subject.start_time, subject.end_time, subject.room, subject.day]):
                    skipped_subjects.append(subject.subject_name)
                    continue

                days_list = [d.strip() for d in subject.day.split(",")]
                subject_skipped = False

                for day_name in days_list:
                    day_code = DAY_MAPPING.get(day_name)
                    if not day_code:
                        subject_skipped = True
                        continue

                    exists = Schedule.objects.filter(
                        section=section,
                        subject=subject,
                        instructor=subject.instructor,
                        day=day_code,
                        time_start=subject.start_time,  
                        time_end=subject.end_time,
                    ).exists()

                    if exists:
                        continue

                    try:
                        Schedule.objects.create(
                            section=section,
                            subject=subject,
                            instructor=subject.instructor,
                            room=subject.room,
                            day=day_code,
                            time_start=subject.start_time,
                            time_end=subject.end_time,
                        )

                    except ValidationError as e:
                        subject_skipped = True
                        print(f"Skipped {subject.subject_code}: {e}")

                if subject_skipped:
                    skipped_subjects.append(subject.subject_code)

            messages.success(request, "Auto-assignment of schedules completed.")

            if skipped_subjects:
                skipped_subjects_unique = list(set(skipped_subjects))
                messages.warning(request, f"Skipped subjects due to incomplete info or conflicts: {', '.join(skipped_subjects_unique)}")
            
            return redirect(f'{request.path}?curriculum={curriculum.id}&section={section.id}&year={selected_year}&semester={selected_semester}')
        
                    

    departments = Department.objects.all()
    courses = Course.objects.all()
    curricula = Curriculum.objects.all()
    sections = Section.objects.filter(course=selected_curriculum.course).order_by('year_level', 'section_name') if selected_curriculum else []

    year_levels_dropdown = [1, 2, 3, 4]

    curriculum_subjects = []
    if selected_curriculum and selected_section:
        # Loop through all possible years (e.g., 1 to 4)
        for year in range(1, 5):
            year_obj, _ = YearLevel.objects.get_or_create(curriculum=selected_curriculum, year=year)
            semesters = []
            
            # Loop through semesters (1st, 2nd, Summer)
            for sem_num in [1, 2, 3]:
                sem_name = {1: '1st Semester', 2: '2nd Semester', 3: 'Summer'}.get(sem_num)
                sem_obj, _ = Semester.objects.get_or_create(
                    year_level=year_obj, 
                    semester_number=sem_num, 
                    defaults={'name': sem_name}
                )
                
                # Fetch subjects for this semester & selected section
                subjects_in_sem = CurriculumSubject.objects.filter(
                    semester=sem_obj,
                    subject__section=selected_section
                ).select_related('subject', 'subject__room', 'subject__instructor')
                
                # Only add semester if it has subjects
                if subjects_in_sem.exists():
                    semesters.append({'semester': sem_obj, 'subjects': subjects_in_sem})
            
            # Only add year if it has semesters with subjects
            if semesters:
                curriculum_subjects.append({'year': year_obj, 'semesters': semesters})


    context = {
        'department_form': department_form,
        'course_form': course_form,
        'curriculum_form': curriculum_form,
        'subject_form': subject_form,
        'schoolyear_form': schoolyear_form,
        'departments': departments,
        'courses': courses,
        'curricula': curricula,
        'sections': sections,
        'selected_curriculum': selected_curriculum,
        'selected_section': selected_section,
        'selected_year': selected_year,
        'selected_semester': selected_semester,
        'year_levels': year_levels_dropdown,
        'curriculum_subjects': curriculum_subjects,
        'assign_instructors': assign_instructors,
        'available_rooms': available_rooms,
    }

    return render(request, 'scheduler/admin/manage_curriculum.html', context)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Announcement

@login_required
def manage_announcements(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    # 🏫 Load all departments
    departments = Department.objects.all().order_by('name')

    # 🎯 Get selected department from GET or POST
    selected_department_id = request.GET.get('department') or request.POST.get('department')
    selected_department = Department.objects.filter(id=selected_department_id).first() if selected_department_id else None
    page_number = request.GET.get('page', 1)

    # 📢 Filter announcements by selected department with pagination
    announcements_by_department = {}
    paginator_obj = None
    
    if selected_department:
        announcements_list = list(Announcement.objects.filter(department=selected_department).order_by('-created_at'))
        
        # Apply pagination - 6 announcements per page
        paginator = Paginator(announcements_list, 6)
        
        try:
            paginated_announcements = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_announcements = paginator.page(1)
        except EmptyPage:
            paginated_announcements = paginator.page(paginator.num_pages)
        
        announcements_by_department[selected_department.name] = paginated_announcements
        paginator_obj = paginated_announcements
        announcements = paginated_announcements  # For backward compatibility
    else:
        announcements = []

    if request.method == 'POST':
        action = request.POST.get('action')

        # ✅ ADD ANNOUNCEMENT
        if action == 'add_announcement':
            title = request.POST.get('title')
            content = request.POST.get('content')
            target_roles = request.POST.getlist('target_roles')
            department_id = request.POST.get('department')

            try:
                department = Department.objects.get(id=department_id)
                Announcement.objects.create(
                    title=title or '',
                    content=content or '',
                    target_roles=','.join(target_roles) if target_roles else '',
                    department=department
                )
                messages.success(request, f"✅ Announcement created for {department.name}.")
            except Exception as e:
                messages.error(request, f"❌ Failed to create announcement: {e}")
            return redirect(f"{reverse('manage_announcements')}?department={department_id}")

        # 🗑️ DELETE ANNOUNCEMENT
        elif action == 'delete_announcement':
            ann_id = request.POST.get('announcement_id')
            Announcement.objects.filter(id=ann_id).delete()
            messages.success(request, "🗑️ Announcement deleted.")
            return redirect(f"{reverse('manage_announcements')}?department={selected_department_id}")

    context = {
        "departments": departments,
        "selected_department": selected_department,
        "announcements": announcements,
        "announcements_by_department": announcements_by_department,
        "paginator": paginator_obj,
    }

    return render(request, "scheduler/admin/manage_announcements.html", context)



# scheduler/views.py (relevant parts; ensure imports are present at top of file)
from django.http import JsonResponse
from django.views.decorators.http import require_GET

# add this simple AJAX endpoint to return courses for a department (used by the template)
@require_GET
def get_courses_section(request, dept_id):
    courses = Course.objects.filter(department_id=dept_id).values('id', 'course_code', 'course_name')
    return JsonResponse(list(courses), safe=False)


def get_courses(request, dept_id):
    courses = Course.objects.filter(department_id=dept_id).values('id', 'course_code', 'course_name')
    return JsonResponse(list(courses), safe=False)



@login_required
def assign_schedule(request, cs_id):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    cs = get_object_or_404(CurriculumSubject, id=cs_id)

    if request.method == 'POST':
        section_id = request.POST.get('section')
        instructor_id = request.POST.get('instructor')
        room_id = request.POST.get('room')
        day = request.POST.get('day')
        time_start = request.POST.get('time_start')
        time_end = request.POST.get('time_end')

        if not all([section_id, instructor_id, room_id, day, time_start, time_end]):
            messages.error(request, "All fields are required.")
            return redirect('manage_curriculum')

        section = get_object_or_404(Section, id=section_id)
        instructor = get_object_or_404(Instructor, id=instructor_id)
        room = get_object_or_404(Room, id=room_id)

        try:
            t_start = datetime.datetime.strptime(time_start, '%H:%M').time()
            t_end = datetime.datetime.strptime(time_end, '%H:%M').time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return redirect('manage_curriculum')

        # Create and save schedule
        schedule = Schedule(
            section=section,
            subject=cs.subject,
            instructor=instructor,
            room=room,
            day=day,
            time_start=t_start,
            time_end=t_end
        )

        try:
            schedule.save()  # validates conflicts
            messages.success(request, f"Schedule assigned to {cs.subject.subject_code} successfully.")

        except Exception as e:
            messages.error(request, f"Error assigning schedule: {str(e)}")

    return redirect('manage_curriculum')


@login_required
def add_curriculum(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    if request.method == 'POST':
        form = CurriculumForm(request.POST)
        if form.is_valid():
            curriculum = form.save()
            messages.success(request, f"Curriculum '{curriculum.name}' created successfully.")
            return redirect('manage_curriculum')
        else:
            messages.error(request, "Error creating curriculum. Check your inputs.")
    else:
        form = CurriculumForm()

    return render(request, 'scheduler/admin/add_curriculum.html', {'form': form})

# views.py

@login_required
def add_year_level(request, curriculum_id):
    curriculum = get_object_or_404(Curriculum, id=curriculum_id)
    if request.method == 'POST':
        form = YearLevelForm(request.POST)
        if form.is_valid():
            year_level = form.save(commit=False)
            year_level.curriculum = curriculum
            year_level.save()
            messages.success(request, f"Year {year_level.year} added successfully.")
        else:
            messages.error(request, "Error adding year level.")
    return redirect(f"{reverse('manage_curriculum')}?curriculum={curriculum.id}")


@login_required
def add_semester(request, year_level_id):
    year_level = get_object_or_404(YearLevel, id=year_level_id)
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save(commit=False)
            semester.year_level = year_level
            semester.save()
            messages.success(request, f"Semester {semester.semester_number} added successfully.")
        else:
            messages.error(request, "Error adding semester.")
    return redirect(f"{reverse('manage_curriculum')}?curriculum={year_level.curriculum.id}")


@login_required
def add_curriculum_subject(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    if request.method == 'POST':
        form = CurriculumSubjectForm(request.POST)
        if form.is_valid():
            cs = form.save(commit=False)
            cs.semester = semester
            cs.save()
            messages.success(request, f"Subject {cs.subject.subject_code} added successfully.")
        else:
            messages.error(request, "Error adding subject.")
    return redirect(f"{reverse('manage_curriculum')}?curriculum={semester.year_level.curriculum.id}")

@login_required
def bulk_user_action(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    if request.method == "POST":
        user_ids = request.POST.getlist('user_ids')
        action = request.POST.get('action')
        if user_ids and action:
            users = User.objects.filter(id__in=user_ids)
            if action == "activate":
                users.update(is_active=True)
            elif action == "deactivate":
                users.update(is_active=False)
            elif action == "delete":
                users.delete()
    return redirect('manage_users')


# ---------------- AUTO-SCHEDULER & VALIDATION ----------------
from django.views.decorators.http import require_POST
from .auto_scheduler import generate_timetable as run_scheduler


@login_required
@require_POST
def generate_timetable(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    curriculum_id = request.POST.get('curriculum_id') or None
    try:
        result = run_scheduler(curriculum_id=int(curriculum_id) if curriculum_id else None)
        created = result.get('created', 0)
        failed = len(result.get('failed', []))
        messages.success(request, f"Generated {created} schedule block(s). {failed} item(s) could not be scheduled.")
    except Exception as e:
        messages.error(request, f"Failed to generate timetable: {str(e)}")
    return redirect('manage_curriculum')


@login_required
@require_GET
def validate_slot(request):
    if not request.user.is_admin():
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    section_id = request.GET.get('section')
    instructor_id = request.GET.get('instructor')
    room_id = request.GET.get('room')
    day = request.GET.get('day')
    time_start = request.GET.get('time_start')
    time_end = request.GET.get('time_end')

    try:
        section = get_object_or_404(Section, id=section_id)
        instructor = get_object_or_404(Instructor, id=instructor_id)
        room = get_object_or_404(Room, id=room_id)
        t_start = datetime.datetime.strptime(time_start, '%H:%M').time()
        t_end = datetime.datetime.strptime(time_end, '%H:%M').time()
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid parameters"}, status=400)

    conflicts = []
    if Schedule.objects.filter(section=section, day=day).filter(time_start__lt=t_end, time_end__gt=t_start).exists():
        conflicts.append("Section has a conflicting class")
    if Schedule.objects.filter(instructor=instructor, day=day).filter(time_start__lt=t_end, time_end__gt=t_start).exists():
        conflicts.append("Instructor is not available (conflict)")
    if Schedule.objects.filter(room=room, day=day).filter(time_start__lt=t_end, time_end__gt=t_start).exists():
        conflicts.append("Room is occupied")

    # availability checks
    from .models import InstructorAvailability, RoomAvailability
    instr_av = list(instructor.availabilities.all())
    if instr_av and not any(a.day == day and a.start_time <= t_start and a.end_time >= t_end for a in instr_av):
        conflicts.append("Instructor not available in this time window")
    room_av = list(room.availabilities.all())
    if room_av and not any(a.day == day and a.start_time <= t_start and a.end_time >= t_end for a in room_av):
        conflicts.append("Room not available in this time window")

    return JsonResponse({"ok": len(conflicts) == 0, "conflicts": conflicts})

@login_required
def edit_schedule(request, schedule_id):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    schedule = get_object_or_404(Schedule, id=schedule_id)

    if request.method == 'POST':
        day = request.POST.get('day')
        time_start = request.POST.get('time_start')
        time_end = request.POST.get('time_end')
        room_id = request.POST.get('room')
        instructor_id = request.POST.get('instructor')

        try:
            t_start = datetime.datetime.strptime(time_start, '%H:%M').time()
            t_end = datetime.datetime.strptime(time_end, '%H:%M').time()
            room = get_object_or_404(Room, id=room_id)
            instructor = get_object_or_404(Instructor, id=instructor_id)

            schedule.day = day
            schedule.time_start = t_start
            schedule.time_end = t_end
            schedule.room = room
            schedule.instructor = instructor
            schedule.save()

            messages.success(request, "Schedule updated successfully.")
            return redirect('manage_schedules')

        except Exception as e:
            messages.error(request, f"Error updating schedule: {str(e)}")

    context = {
        'schedule': schedule,
        'rooms': Room.objects.all(),
        'instructors': Instructor.objects.select_related('user').all(),
    }
    return render(request, 'scheduler/admin/edit_schedule.html', context)

@login_required
def delete_schedule(request, schedule_id):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('home_redirect')

    schedule = get_object_or_404(Schedule, id=schedule_id)
    schedule.delete()
    messages.success(request, "Schedule deleted successfully.")
    return redirect('manage_schedules')


# ---------------- LOGOUT VIEW ----------------
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('auth_page')

def public_schedule_view(request):
    # GET parameters
    department_id = request.GET.get('department')
    school_year_level_text = request.GET.get('school_year_level')  # user types text
    section_name = request.GET.get('section')
    instructor_name = request.GET.get('instructor')
    subject_name = request.GET.get('subject')
    room = request.GET.get('room')
    subject_code = request.GET.get('subject_code')

    # Querysets
    departments = Department.objects.all().order_by('name')
    instructors = Instructor.objects.select_related('user').all().order_by('user__first_name')
    subjects = Subject.objects.select_related('instructor__user', 'school_year_level', 'room').all()

    # Filter by department
    selected_department = None
    if department_id:
        selected_department = get_object_or_404(Department, id=department_id)
        subjects = subjects.filter(curriculum__course__department=selected_department)

    # Filter by school year (typed search)
    if school_year_level_text:
        subjects = subjects.filter(
            school_year_level__school_year__icontains=school_year_level_text
        )

    # Filter by section
    if section_name:
        subjects = subjects.filter(section__icontains=section_name)

    # Filter by instructor
    if instructor_name:
        subjects = subjects.filter(
            Q(instructor__user__first_name__icontains=instructor_name) |
            Q(instructor__user__last_name__icontains=instructor_name)
        )

    # Filter by subject name
    if subject_name:
        subjects = subjects.filter(subject_name__icontains=subject_name)

    # Filter by room - FIXED
    if room:
        subjects = subjects.filter(room__room_name__icontains=room)  # Changed from 'name' to 'room_name'

    # Filter by subject code
    if subject_code:
        subjects = subjects.filter(subject_code__icontains=subject_code)

    context = {
        'departments': departments,
        'selected_department': selected_department,
        'subjects': subjects,
        'instructors': instructors,
        'request': request,
    }

    return render(request, 'public/public_schedule_view.html', context)