from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

from .models import (
    User, Section, Curriculum, YearLevel, Semester,
    CurriculumSubject, Subject, Room, Department, Course, Schedule, SchoolYearLevel,
    Instructor
)


# ===============================
#   REGISTRATION FORMS
# ===============================
class AdminRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'middle_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.ADMIN
        user.is_active = True
        user.is_approved = True
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class InstructorRegistrationForm(UserCreationForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        label="Department",
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'middle_name', 'last_name',
            'email', 'instructor_number',
            'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.INSTRUCTOR
        user.is_active = False  # Wait for admin approval
        user.is_approved = False
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # Create Instructor profile and attach department
            Instructor.objects.create(
                user=user,
                department=self.cleaned_data['department']
            )
        return user


# ===============================
#   LOGIN FORMS
# ===============================
class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


# ===============================
#   CURRICULUM FORMS
# ===============================
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['code', 'name']
        widgets = {
            'code': forms.TextInput(attrs={
                'placeholder': 'Department Abbreviation (e.g., STCS)',
                'class': 'form-input'
            }),
            'name': forms.TextInput(attrs={
                'placeholder': 'Department Name (e.g., School of Technology and Computer Studies)',
                'class': 'form-input'
            }),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['department', 'course_code', 'course_name']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'course_code': forms.TextInput(attrs={
                'placeholder': 'Course Abbreviation (e.g., BSCS)',
                'class': 'form-input'
            }),
            'course_name': forms.TextInput(attrs={
                'placeholder': 'Course Name (e.g., Bachelor of Science in Computer Science)',
                'class': 'form-input'
            }),
        }

# ===============================
#   SUBJECT FORM
# ===============================
class SubjectForm(forms.ModelForm):
    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    ]

    SEMESTER_CHOICES = [
        (1, '1st Semester'),
        (2, '2nd Semester'),
        (3, 'Summer'),
    ]

    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    DURATION_CHOICES = [
        (1, "1 Hour"),
        (2, "2 Hours"),
        (3, "3 Hours"),
    ]

    # Generate dynamic time choices
    @staticmethod
    def generate_time_choices():
        start_times = [
            datetime.strptime(t, "%I:%M %p") for t in [
                "7:00 AM", "7:30 AM", "8:00 AM", "8:30 AM",
                "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM",
                "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
                "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM",
                "3:00 PM", "3:30 PM", "4:00 PM", "4:30 PM",
                "5:00 PM", "5:30 PM", "6:00 PM", "6:30 PM",
                "7:00 PM", "7:30 PM", "8:00 PM", "8:30 PM", "9:00 PM"
            ]
        ]

        choices = []
        for start in start_times:
            for duration in [1, 2, 3]:
                end = start + timedelta(hours=duration)
                if end.hour > 22 or (end.hour == 22 and end.minute > 30):
                    continue
                start_str = start.strftime("%I:%M %p").lstrip("0")
                end_str = end.strftime("%I:%M %p").lstrip("0")
                label = f"{start_str} - {end_str} ({duration} hr{'s' if duration > 1 else ''})"
                value = f"{start_str}-{end_str}-{duration}"
                choices.append((value, label))
        return choices

    TIME_CHOICES = generate_time_choices()

    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        required=False,
        label="Duration",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'duration-select'})
    )

    time = forms.ChoiceField(
        choices=TIME_CHOICES,
        required=False,
        label="Time",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'time-select'})
    )

    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="Year Level",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    semester_choice = forms.ChoiceField(
        choices=SEMESTER_CHOICES,
        label="Semester",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    prerequisite = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional', 'class': 'form-input'})
    )

    day = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        required=False,
        empty_label="-- Select Room --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.all(),
        required=False,
        empty_label="-- Select Instructor --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        empty_label="-- Select Section --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Subject
        fields = [
            'subject_code', 'subject_name', 'prerequisite',
            'lecture_units', 'lab_units', 'units',
            'year', 'semester_choice', 'duration', 'time',
            'day', 'room', 'instructor', 'section',
        ]
        widgets = {
            'subject_code': forms.TextInput(attrs={'placeholder': 'Subject No/Code', 'class': 'form-input'}),
            'subject_name': forms.TextInput(attrs={'placeholder': 'Descriptive Title/Subject Name', 'class': 'form-input'}),
            'lecture_units': forms.NumberInput(attrs={'placeholder': 'Lecture Hours', 'class': 'form-input'}),
            'lab_units': forms.NumberInput(attrs={'placeholder': 'Laboratory Hours', 'class': 'form-input'}),
            'units': forms.NumberInput(attrs={'placeholder': 'Units', 'class': 'form-input'}),
        }

    # Convert selected days into string
    def clean_day(self):
        days = self.cleaned_data.get('day')
        return ', '.join(days) if days else ''

    # Prevent duplicate subjects in the same section
    def clean(self):
        cleaned_data = super().clean()
        subject_code = cleaned_data.get('subject_code')
        section = cleaned_data.get('section')

        if subject_code and section:
            duplicate = Subject.objects.filter(subject_code__iexact=subject_code, section=section)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError(f"⚠️ Subject '{subject_code}' already exists in this section.")
        return cleaned_data

    # Dynamic filtering of sections/rooms by curriculum
    def __init__(self, *args, **kwargs):
        curriculum = kwargs.pop('curriculum', None)
        semester = kwargs.pop('semester', None)  # Pass current semester
        super().__init__(*args, **kwargs)

    # Filter sections & rooms by curriculum/course
        if curriculum and curriculum.course:
            self.fields['section'].queryset = Section.objects.filter(course=curriculum.course)
            self.fields['room'].queryset = Room.objects.all().order_by('department__name', 'floor', 'room_name')
        else:
            self.fields['section'].queryset = Section.objects.none()
            self.fields['room'].queryset = Room.objects.all().order_by('department__name', 'floor', 'room_name')

        # Reset semester-specific fields if semester changes
        if semester:
            self.fields['room'].initial = None
            self.fields['time'].initial = None
            self.fields['day'].initial = []
            self.fields['instructor'].initial = None



    # Save method to handle time parsing
    def save(self, commit=True):
        instance = super().save(commit=False)

        # Parse the time field if it exists (example: "7:00 AM-8:00 AM-1")
        time_value = self.cleaned_data.get('time')
        if time_value:
            try:
                start_str, end_str, duration = time_value.split('-')
                instance.start_time = datetime.strptime(start_str.strip(), "%I:%M %p").time()
                instance.end_time = datetime.strptime(end_str.strip(), "%I:%M %p").time()
                instance.duration = int(duration)
            except ValueError:
                pass  # optionally raise ValidationError

        # Convert days to string
        instance.day = self.cleaned_data.get('day', '')

        if commit:
            instance.save()
        return instance
    


# ===============================
#   OTHER FORMS
# ===============================
class CurriculumForm(forms.ModelForm):
    class Meta:
        model = Curriculum
        fields = ['name', 'course', 'is_active']
        labels = {'name': 'Revision Name', 'course': 'Course', 'is_active': 'Active'}
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., RS-4 Bachelor of Science in Computer Science'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class YearLevelForm(forms.ModelForm):
    class Meta:
        model = YearLevel
        fields = ['year']


class SchoolYearLevelForm(forms.ModelForm):
    class Meta:
        model = SchoolYearLevel
        fields = ['curriculum', 'school_year']
        labels = {'curriculum': 'Curriculum', 'school_year': 'School Year Level (e.g., 25-1)'}
        widgets = {
            'curriculum': forms.Select(attrs={'class': 'form-select'}),
            'school_year': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., 25-1'}),
        }


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ['semester_number', 'name']


class CurriculumSubjectForm(forms.ModelForm):
    subject_code = forms.CharField(max_length=50, required=True)
    subject_name = forms.CharField(max_length=200, required=True)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    is_required = forms.BooleanField(required=False)
    order = forms.IntegerField(required=False, min_value=1)

    class Meta:
        model = CurriculumSubject
        fields = ['subject_code', 'subject_name', 'description', 'is_required', 'order']

    def save(self, commit=True, semester=None):
        subject, created = Subject.objects.get_or_create(
            subject_code=self.cleaned_data['subject_code'],
            defaults={'subject_name': self.cleaned_data['subject_name'], 'description': self.cleaned_data.get('description', '')}
        )
        cs = super().save(commit=False)
        cs.subject = subject
        if semester:
            cs.semester = semester
        if commit:
            cs.save()
        return cs


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['section', 'instructor', 'room', 'day', 'time_start', 'time_end']
