import datetime
from typing import Dict, List, Optional, Tuple

from django.db import transaction

from .models import (
    Schedule,
    Curriculum,
    CurriculumSubject,
    Instructor,
    InstructorAvailability,
    Room,
    RoomAvailability,
)


DAYS = [Schedule.Day.MON, Schedule.Day.TUE, Schedule.Day.WED, Schedule.Day.THU, Schedule.Day.FRI]
START_HOUR = 8
END_HOUR = 17  # exclusive


def _time_slots() -> List[Tuple[datetime.time, datetime.time]]:
    slots = []
    for hour in range(START_HOUR, END_HOUR):
        start = datetime.time(hour, 0)
        end = datetime.time(hour + 1, 0)
        slots.append((start, end))
    return slots


def _is_available_in_range(avails, day: str, start: datetime.time, end: datetime.time) -> bool:
    for a in avails:
        if a.day == day and a.start_time <= start and a.end_time >= end:
            return True
    return False


def _has_conflict_for_instructor(instructor: Instructor, day: str, start: datetime.time, end: datetime.time) -> bool:
    return Schedule.objects.filter(instructor=instructor, day=day).filter(time_start__lt=end, time_end__gt=start).exists()


def _has_conflict_for_room(room: Room, day: str, start: datetime.time, end: datetime.time) -> bool:
    return Schedule.objects.filter(room=room, day=day).filter(time_start__lt=end, time_end__gt=start).exists()


def _has_conflict_for_section(section, day: str, start: datetime.time, end: datetime.time) -> bool:
    return Schedule.objects.filter(section=section, day=day).filter(time_start__lt=end, time_end__gt=start).exists()


@transaction.atomic
def generate_timetable(curriculum_id: Optional[int] = None) -> Dict:
    """
    A simple greedy scheduler:
    - Iterates CurriculumSubjects in order.
    - For each subject, schedules required_hours_per_week as 1-hour blocks for every section in the curriculum's course.
    - Picks the first feasible (day, slot, room, instructor) satisfying availability and conflicts.

    Returns a summary dict with counts and failures.
    """
    curricula = Curriculum.objects.filter(id=curriculum_id) if curriculum_id else Curriculum.objects.filter(is_active=True)
    results = {"created": 0, "failed": [], "processed_subjects": 0}

    slots = _time_slots()

    for curriculum in curricula:
        course = curriculum.course
        sections = list(course.sections.all())
        cs_list = CurriculumSubject.objects.filter(semester__year_level__curriculum=curriculum).select_related("subject").order_by("order", "id")
        for cs in cs_list:
            subject = cs.subject
            results["processed_subjects"] += 1

            # candidate instructors: qualified or any if none explicitly qualified
            qualified = list(Instructor.objects.filter(subjects=subject))
            if not qualified:
                qualified = list(Instructor.objects.all())

            for section in sections:
                hours_needed = max(1, int(subject.required_hours_per_week))
                hours_assigned = 0

                for day in DAYS:
                    if hours_assigned >= hours_needed:
                        break
                    for start, end in slots:
                        if hours_assigned >= hours_needed:
                            break
                        # section conflict
                        if _has_conflict_for_section(section, day, start, end):
                            continue

                        # try instructors
                        chosen_instructor = None
                        for instr in qualified:
                            if _has_conflict_for_instructor(instr, day, start, end):
                                continue
                            instr_avails = list(instr.availabilities.all())
                            if instr_avails and not _is_available_in_range(instr_avails, day, start, end):
                                continue
                            chosen_instructor = instr
                            break
                        if not chosen_instructor:
                            continue

                        # try rooms: match type and capacity
                        candidate_rooms = Room.objects.all()
                        if subject.meeting_type == 'LABORATORY':
                            candidate_rooms = candidate_rooms.filter(room_type='LABORATORY')
                        else:
                            candidate_rooms = candidate_rooms.filter(room_type='LECTURE')
                        candidate_rooms = candidate_rooms.order_by('capacity')

                        chosen_room = None
                        for room in candidate_rooms:
                            if _has_conflict_for_room(room, day, start, end):
                                continue
                            room_avails = list(room.availabilities.all())
                            if room_avails and not _is_available_in_range(room_avails, day, start, end):
                                continue
                            # quick capacity check
                            section_size = section.students.count()
                            if room.capacity and section_size > room.capacity:
                                continue
                            chosen_room = room
                            break
                        if not chosen_room:
                            continue

                        # create schedule
                        sched = Schedule(
                            section=section,
                            subject=subject,
                            instructor=chosen_instructor,
                            room=chosen_room,
                            day=day,
                            time_start=start,
                            time_end=end,
                            meeting_type=subject.meeting_type,
                        )
                        try:
                            sched.save()
                            hours_assigned += 1
                            results["created"] += 1
                        except Exception as e:
                            results["failed"].append({
                                "section": str(section),
                                "subject": subject.subject_code,
                                "day": day,
                                "start": str(start),
                                "end": str(end),
                                "reason": str(e),
                            })
                            continue

                if hours_assigned < hours_needed:
                    results["failed"].append({
                        "section": str(section),
                        "subject": subject.subject_code,
                        "reason": f"Only assigned {hours_assigned}/{hours_needed} hour(s)"
                    })

    return results


