from collections import namedtuple

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Min, Max, Count, Sum, Case, When, IntegerField
from django.utils import timezone

from judge.models import Problem, Organization, Submission


@login_required
def overall_summary(request, organization, problem_prefix):
    if not request.user.is_superuser:
        raise Http404()

    context = {}

    if ',' in problem_prefix:
        prefixes = problem_prefix.split(',')

        q = Q(code__startswith=prefixes[0])
        for prefix in prefixes[1:]:
            q |= Q(code__startswith=prefix)

        problems = Problem.objects.filter(q)
    else:
        problems = Problem.objects.filter(code__startswith=problem_prefix)

    organization = get_object_or_404(Organization, slug=organization)

    students = organization.members.order_by('user__last_name')

    StudentGrade = namedtuple('StudentGrade', [
        'sid',
        'last_name',
        'first_name',
        'section',
        'cn',
        'grades',
        'total_time',
        'total_points',
        'date',
    ])

    problem_headers = sorted([i.code for i in problems])

    now = timezone.now()
    zero_timedelta = now - now
    student_grades = []
    is_contest = False

    for student in students:
        grade_mapping = {header: None for header in problem_headers}
        total_points = 0
        final_time = zero_timedelta
        best_submission_date = None

        for problem in problems:
            grade = problem.grade_of(student)
            time = problem.best_time_of(student)
            is_contest = problem.containing_contest(student)
            date = problem.best_submission_date_of(student)

            total_points += grade

            if is_contest and time is not None:
                if final_time is None:
                    final_time = time
                final_time = max(final_time, time)

            elif not is_contest and date is not None:
                if best_submission_date is None:
                    best_submission_date = date
                best_submission_date = max(best_submission_date, date)

            grade_mapping[problem.code] = {
                "grade": grade,
                "time": time,
            }

        name = student.user.last_name
        section, cn, last_name, first_name = name.split('_', 3)

        #last_name = last_name.encode('utf8')
        #first_name = first_name.encode('utf8')
        name = name.encode('utf8')

        sg = StudentGrade(
            sid="",
            last_name=last_name,
            first_name=first_name,
            section=section,
            cn=cn,
            grades=[i[1] for i in sorted(grade_mapping.items(), key=lambda item: item[0])],
            total_time=final_time if final_time is not None else zero_timedelta,
            date=best_submission_date,
            total_points=total_points,
        )

        student_grades.append(sg)


    ranked = request.GET.get("ranked")
    if ranked:
        if is_contest:
            student_grades = sorted(student_grades, key=lambda sg: (
                -sg.total_points,
                zero_timedelta.max if sg.total_time == zero_timedelta and sg.total_points == 0 else sg.total_time,
                sg.last_name,
                sg.first_name,
            ))
        else:
            student_grades = sorted(student_grades, key=lambda sg: (-sg.total_points, now if sg.date is None else sg.date, sg.last_name, sg.first_name))

    context['problem_headers'] = problem_headers
    context['organization'] = organization
    context['student_grades'] = student_grades
    context['ranked'] = ranked
    context['is_contest'] = is_contest

    return render(request, 'summary/overall.html', context)


@login_required
def overall_completion(request, organization, problem_prefix):
    if not request.user.is_superuser:
        raise Http404()

    context = {}

    if ',' in problem_prefix:
        prefixes = problem_prefix.split(',')

        q = Q(code__startswith=prefixes[0])
        for prefix in prefixes[1:]:
            q |= Q(code__startswith=prefix)

        problems = Problem.objects.filter(q)
    else:
        problems = Problem.objects.filter(code__startswith=problem_prefix)

    organization = get_object_or_404(Organization, slug=organization)

    students = organization.members.order_by('user__last_name')

    StudentGrade = namedtuple('StudentGrade', [
        'sid',
        'last_name',
        'first_name',
        'section',
        'grades',
        'total_time',
        'total_points',
        'date',
    ])

    problem_headers = sorted([i.code for i in problems])

    now = timezone.now()
    zero_timedelta = now - now
    student_grades = []
    is_contest = False

    for student in students:
        grade_mapping = {header: None for header in problem_headers}
        total_points = 0
        final_time = zero_timedelta

        for problem in problems:
            submissions = Submission.objects.filter(problem=problem, user=student)

            grade = 0.0
            if submissions:
                submissions = submissions.order_by("-points", "date")
                grade = submissions.first().points
                if grade is None:
                    grade = 0.0

            total_points += grade

            grade_mapping[problem.code] = {
                "grade": grade,
            }

        sid, section, last_name, first_name = student.user.last_name.encode('utf8').split('_', 3)
        sg = StudentGrade(
            sid="",
            last_name=last_name,
            first_name=first_name,
            section=section,
            grades=[i[1] for i in sorted(grade_mapping.items(), key=lambda item: item[0])],
            total_time=None,
            date=None,
            total_points=total_points,
        )

        student_grades.append(sg)


    ranked = request.GET.get("ranked")
    zero_row = request.GET.get("zero_row")
    if ranked:
        if is_contest:
            student_grades = sorted(student_grades, key=lambda sg: (
                -sg.total_points,
                zero_timedelta.max if sg.total_time == zero_timedelta and sg.total_points == 0 else sg.total_time,
                sg.last_name,
                sg.first_name,
            ))
        else:
            student_grades = sorted(student_grades, key=lambda sg: (-sg.total_points, now if sg.date is None else sg.date, sg.last_name, sg.first_name))

    context['problem_headers'] = problem_headers
    context['organization'] = organization
    context['student_grades'] = student_grades
    context['ranked'] = ranked
    context['is_contest'] = is_contest
    context['zero_row'] = zero_row

    return render(request, 'summary/overall.html', context)
