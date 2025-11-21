from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import datetime


# ✅ CUSTOM USER MODEL
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
       

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.INSTRUCTOR)
    instructor_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR


    def save(self, *args, **kwargs):
        if self.role != self.Role.INSTRUCTOR:
            self.instructor_number = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"



# ✅ CLEAN, CUSTOMIZED DEPARTMENT MODEL
class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'scheduler_department'
        verbose_name_plural = "Departments"
        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_department_name'),
            models.UniqueConstraint(fields=['code'], name='unique_department_code'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"




# ✅ COURSE MODEL
class Course(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    course_code = models.CharField(max_length=10, unique=True)
    course_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'scheduler_course'

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"
    

SEMESTER_CHOICES = (
    (1, "1st Semester"),
    (2, "2nd Semester"),
)

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_name = models.CharField(max_length=20)
    year_level = models.PositiveIntegerField(default=1)
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES, default=1)

    class Meta:
        unique_together = ('course', 'section_name', 'semester')
        db_table = 'scheduler_section'

    def __str__(self):
        return f"{self.course.course_code} - {self.section_name} (Semester {self.semester})"


# ✅ CURRICULUM MODEL
class Curriculum(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='curricula')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scheduler_curriculum'

    def __str__(self):
        return f"{self.name} - {self.course.course_name}"



# ✅ YEAR LEVEL MODEL
class YearLevel(models.Model):
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE, related_name='year_levels')
    year = models.PositiveIntegerField()

    class Meta:
        db_table = 'scheduler_yearlevel'
        unique_together = ['curriculum', 'year']

    def __str__(self):
        return f"Year {self.year} - {self.curriculum.name}"
    

# ✅ SCHOOL YEAR LEVEL MODEL
class SchoolYearLevel(models.Model):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name="school_year_levels",
        null=True, blank=True   # 👈 Add these two to make it optional
    )
    school_year = models.CharField(
        max_length=20,
        help_text="Format: YY-# (e.g. 25-1, 25-2)"
    )

    class Meta:
        db_table = 'scheduler_schoolyearlevel'
        unique_together = ['curriculum', 'school_year']
        ordering = ['school_year']

    def __str__(self):
        return f"{self.school_year} ({self.curriculum.name if self.curriculum else 'No Curriculum'})"

    def clean(self):
        # Optional validation to enforce pattern like "25-1"
        import re
        if not re.match(r'^\d{2}-\d$', self.school_year):
            raise ValidationError("School year format must be like '25-1' or '25-2'.")



# ✅ SEMESTER MODEL
class Semester(models.Model):
    year_level = models.ForeignKey(YearLevel, on_delete=models.CASCADE, related_name='semesters')
    semester_number = models.PositiveIntegerField()
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'scheduler_semester'
        unique_together = ['year_level', 'semester_number']

    def __str__(self):
        return f"{self.name} - {self.year_level}"



class Subject(models.Model):
    subject_code = models.CharField(max_length=10)
    subject_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # existing fields
    units = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    lecture_units = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    lab_units = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    tf_units = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    load_units = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)

    prerequisite = models.CharField(max_length=100, blank=True, null=True)

    # curriculum relationships
    curriculum = models.ForeignKey(
        Curriculum, on_delete=models.CASCADE,
        related_name='subjects', null=True, blank=True
    )
    year_level = models.ForeignKey(
        YearLevel, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    school_year_level = models.ForeignKey(
        SchoolYearLevel, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subjects'
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    required_hours_per_week = models.PositiveIntegerField(default=3)
    meeting_type = models.CharField(
        max_length=20,
        choices=(('LECTURE', 'Lecture'), ('LABORATORY', 'Laboratory')),
        default='LECTURE'
    )

    # NEW — FOR REAL SCHEDULING
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)

    day = models.CharField(max_length=100, blank=True, null=True)   # "Monday, Wednesday"

    room = models.ForeignKey(
        'Room',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subjects'
    )

    instructor = models.ForeignKey(
        'Instructor', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subject_instructor'
    )

    # FIXED — use real Section FK!
    section = models.ForeignKey(
    Section, on_delete=models.SET_NULL,
    null=True, blank=True, related_name="scheduled_subjects"
    )


    class Meta:
        db_table = 'scheduler_subject'

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"





# ✅ INSTRUCTOR MODEL
class Instructor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    subjects = models.ManyToManyField(Subject, related_name='qualified_instructors', blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'scheduler_instructor'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"



# ✅ ROOM MODEL 
class Room(models.Model):
    class RoomType(models.TextChoices):
        LECTURE = 'LECTURE', _('Lecture')
        LABORATORY = 'LABORATORY', _('Laboratory')

    room_name = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveIntegerField(default=30)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.LECTURE)

    # 🆕 Optional link to Department
    department = models.ForeignKey(
        'Department',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='rooms'
    )

    # 🆕 Floor number (e.g., 1 = First Floor, etc.)
    floor = models.PositiveIntegerField(default=1)



    class Meta:
        db_table = 'scheduler_room'

    def __str__(self):
        return f"{self.room_name} ({self.get_room_type_display()}) - Floor {self.floor}"




# ✅ SCHEDULE MODEL
class Schedule(models.Model):
    class Day(models.TextChoices):
        MON = 'MON', _('Monday')
        TUE = 'TUE', _('Tuesday')
        WED = 'WED', _('Wednesday')
        THU = 'THU', _('Thursday')
        FRI = 'FRI', _('Friday')
        SAT = 'SAT', _('Saturday')
        SUN = 'SUN', _('Sunday')

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='schedules')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedules')
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='schedules')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=3, choices=Day.choices, default=Day.MON)
    time_start = models.TimeField(default=datetime.time(8, 0))
    time_end = models.TimeField(default=datetime.time(9, 0))
    meeting_type = models.CharField(
        max_length=20,
        choices=(('LECTURE', 'Lecture'), ('LABORATORY', 'Laboratory')),
        default='LECTURE'
    )

    class Meta:
        ordering = ['day', 'time_start']
        db_table = 'scheduler_schedule'
        indexes = [
            models.Index(fields=['day', 'time_start', 'time_end']),
            models.Index(fields=['room', 'day', 'time_start', 'time_end']),
            models.Index(fields=['instructor', 'day', 'time_start', 'time_end']),
            models.Index(fields=['section', 'day', 'time_start', 'time_end']),
        ]

    def __str__(self):
        return f"{self.section} - {self.subject} - {self.day} {self.time_start}-{self.time_end}"

    def clean(self):
        if self.time_start >= self.time_end:
            raise ValidationError(_('End time must be after start time.'))

        duration = datetime.datetime.combine(datetime.date.today(), self.time_end) - datetime.datetime.combine(datetime.date.today(), self.time_start)
        if duration.total_seconds() < 1800:
            raise ValidationError(_('Class duration must be at least 30 minutes.'))
        if duration.total_seconds() > 14400:
            raise ValidationError(_('Class duration cannot exceed 4 hours.'))

        # Room conflict
        if Schedule.objects.filter(room=self.room, day=self.day).exclude(pk=self.pk).filter(
            models.Q(time_start__lt=self.time_end, time_end__gt=self.time_start)
        ).exists():
            raise ValidationError(_('This room is already occupied during the selected time.'))

        # Instructor conflict
        if Schedule.objects.filter(instructor=self.instructor, day=self.day).exclude(pk=self.pk).filter(
            models.Q(time_start__lt=self.time_end, time_end__gt=self.time_start)
        ).exists():
            raise ValidationError(_('This instructor is already teaching during the selected time.'))

        # Section conflict
        if Schedule.objects.filter(section=self.section, day=self.day).exclude(pk=self.pk).filter(
            models.Q(time_start__lt=self.time_end, time_end__gt=self.time_start)
        ).exists():
            raise ValidationError(_('This section already has a class during the selected time.'))


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ✅ ANNOUNCEMENT MODEL
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    target_roles = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comma-separated roles (ADMIN, INSTRUCTOR)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # 🏫 NEW: Link each announcement to a department (optional)
    department = models.ForeignKey(
        'Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='announcements'
    )

    class Meta:
        db_table = 'scheduler_announcement'

    def __str__(self):
        dept = self.department.name if self.department else "General"
        return f"{self.title} ({dept})"


class CurriculumSubject(models.Model):
    curriculum = models.ForeignKey(
        'Curriculum', on_delete=models.CASCADE,
        related_name='curriculum_subjects',
        null=True, blank=True
    )
    year_level = models.ForeignKey(
        'YearLevel', on_delete=models.CASCADE,
        related_name='curriculum_subjects',
        null=True, blank=True
    )
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='curriculum_subjects')
    school_year_level = models.ForeignKey(
        'SchoolYearLevel',
        on_delete=models.CASCADE,
        related_name='curriculum_subjects',
        null=True, blank=True
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'scheduler_curriculum_subject'
        ordering = ['order']
        unique_together = ['curriculum', 'year_level', 'semester', 'subject']

    def __str__(self):
        return f"{self.subject.subject_code} - {self.curriculum or 'No Curriculum'} ({self.semester})"


# ✅ AVAILABILITY MODELS
class InstructorAvailability(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='availabilities')
    day = models.CharField(max_length=3, choices=Schedule.Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = 'scheduler_instructor_availability'
        indexes = [
            models.Index(fields=['instructor', 'day', 'start_time', 'end_time'])
        ]

    def __str__(self):
        return f"{self.instructor} - {self.day} {self.start_time}-{self.end_time}"


class RoomAvailability(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='availabilities')
    day = models.CharField(max_length=3, choices=Schedule.Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = 'scheduler_room_availability'
        indexes = [
            models.Index(fields=['room', 'day', 'start_time', 'end_time'])
        ]

    def __str__(self):
        return f"{self.room} - {self.day} {self.start_time}-{self.end_time}"


class CurriculumRevision(models.Model):
    curriculum = models.ForeignKey(
        'Curriculum',
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    name = models.CharField(max_length=100, help_text="Revision name, e.g. Rev. 1, Rev. 2025")
    effective_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'scheduler_curriculum_revision'
        unique_together = ['curriculum', 'name']
        ordering = ['-effective_date', 'name']

    def __str__(self):
        return f"{self.curriculum.name} - {self.name}"
