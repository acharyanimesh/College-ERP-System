"""Leave applications and feedback, for both the /leave/ and /feedback/
endpoint families. `role` in the URL is 'staff' or 'student'; "mine"
endpoints require the matching logged-in role, review endpoints are
admin-only."""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..forms import (FeedbackStaffForm, FeedbackStudentForm,
                     LeaveReportStaffForm, LeaveReportStudentForm)
from ..models import (FeedbackStaff, FeedbackStudent, LeaveReportStaff,
                      LeaveReportStudent, Staff, Student)
from .permissions import ADMIN, STAFF, STUDENT
from .serializers import form_errors

ROLE_USER_TYPE = {'staff': STAFF, 'student': STUDENT}


def _role_owner(request, role):
    """The Staff/Student profile when the logged-in user matches `role`,
    else None (→ 403)."""
    if str(request.user.user_type) != ROLE_USER_TYPE.get(role):
        return None
    model = Staff if role == 'staff' else Student
    return get_object_or_404(model, admin=request.user)


def _person_name(obj, role):
    user = (obj.staff if role == 'staff' else obj.student).admin
    return "%s %s" % (user.first_name, user.last_name)


def _course_names(obj, role):
    if role == 'staff':
        return ", ".join(c.short_name for c in obj.staff.courses.all())
    student = obj.student
    return student.course.short_name if student.course else ''


# ------------------------------------------------------------------ Leave

def _leave_dict(leave):
    return {
        'id': leave.id,
        'date': leave.date,
        'message': leave.message,
        'status': leave.status,
        'created_at': leave.created_at.strftime('%b. %d, %Y'),
    }


@api_view(['GET', 'POST'])
def leave_mine(request, role):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    owner = _role_owner(request, role)
    if owner is None:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = LeaveReportStaff if role == 'staff' else LeaveReportStudent
    owner_field = 'staff' if role == 'staff' else 'student'
    if request.method == 'GET':
        history = model.objects.filter(**{owner_field: owner})
        return Response([_leave_dict(l) for l in history])
    form_cls = LeaveReportStaffForm if role == 'staff' else LeaveReportStudentForm
    form = form_cls(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    obj = form.save(commit=False)
    setattr(obj, owner_field, owner)
    obj.save()
    return Response(_leave_dict(obj), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def leave_all(request, role):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if str(request.user.user_type) != ADMIN:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = LeaveReportStaff if role == 'staff' else LeaveReportStudent
    result = []
    for leave in model.objects.all():
        data = _leave_dict(leave)
        data['person_name'] = _person_name(leave, role)
        data['course_names'] = _course_names(leave, role)
        result.append(data)
    return Response(result)


@api_view(['POST'])
def leave_status(request, role, leave_id):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if str(request.user.user_type) != ADMIN:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = LeaveReportStaff if role == 'staff' else LeaveReportStudent
    leave = get_object_or_404(model, id=leave_id)
    # Same coercion the old views used: '1' approves, anything else rejects.
    leave.status = 1 if str(request.data.get('status')) == '1' else -1
    leave.save()
    return Response(_leave_dict(leave))


# --------------------------------------------------------------- Feedback

def _feedback_dict(feedback):
    return {
        'id': feedback.id,
        'feedback': feedback.feedback,
        'reply': feedback.reply,
        'created_at': feedback.created_at.strftime('%b. %d, %Y'),
        'updated_at': feedback.updated_at.strftime('%b. %d, %Y'),
    }


@api_view(['GET', 'POST'])
def feedback_mine(request, role):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    owner = _role_owner(request, role)
    if owner is None:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = FeedbackStaff if role == 'staff' else FeedbackStudent
    owner_field = 'staff' if role == 'staff' else 'student'
    if request.method == 'GET':
        feedbacks = model.objects.filter(**{owner_field: owner})
        return Response([_feedback_dict(f) for f in feedbacks])
    form_cls = FeedbackStaffForm if role == 'staff' else FeedbackStudentForm
    form = form_cls(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    obj = form.save(commit=False)
    setattr(obj, owner_field, owner)
    obj.reply = ""
    obj.save()
    return Response(_feedback_dict(obj), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def feedback_all(request, role):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if str(request.user.user_type) != ADMIN:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = FeedbackStaff if role == 'staff' else FeedbackStudent
    result = []
    for feedback in model.objects.all():
        data = _feedback_dict(feedback)
        data['person_name'] = _person_name(feedback, role)
        data['course_names'] = _course_names(feedback, role)
        result.append(data)
    return Response(result)


@api_view(['POST'])
def feedback_reply(request, role, feedback_id):
    if role not in ROLE_USER_TYPE:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if str(request.user.user_type) != ADMIN:
        return Response(status=status.HTTP_403_FORBIDDEN)
    model = FeedbackStaff if role == 'staff' else FeedbackStudent
    feedback = get_object_or_404(model, id=feedback_id)
    feedback.reply = request.data.get('reply') or ''
    feedback.save()
    return Response(_feedback_dict(feedback))
