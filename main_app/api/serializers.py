"""Hand-rolled dict builders shared by the API views.

The payload field names deliberately match what the converted React pages
already consume (which in turn mirror the old Django template context), so
no page needs to change when the backend goes live.
"""


def form_errors(form):
    """Django form.errors → DRF-style error body ({field: [msgs]},
    '__all__' mapped to non_field_errors like useFormSubmit expects)."""
    errors = {}
    for field, msgs in form.errors.items():
        key = 'non_field_errors' if field == '__all__' else field
        errors[key] = list(msgs)
    return errors


def user_dict(user):
    """Auth payload for /auth/me/ and the login response (Sidebar/Navbar)."""
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
        'user_type': str(user.user_type),
        'gender': user.gender,
        'profile_pic': user.profile_pic.url if user.profile_pic else '',
        'email_verified': user.email_verified,
        'pending_email': user.pending_email,
        'pending_email_approved': user.pending_email_approved,
    }


def course_dict(course):
    return {
        'id': course.id,
        'name': course.name,
        'abbreviation': course.abbreviation,
        'code': course.code or '',
        'short_name': course.short_name,
        'name_with_abbr': course.name_with_abbr,
        'semesters': course.semesters,
    }


def session_dict(session):
    return {
        'id': session.id,
        'start_year': session.start_year.isoformat() if session.start_year else None,
        'end_year': session.end_year.isoformat() if session.end_year else None,
        'label': str(session),
    }


def student_row(student):
    """Table row for student lists (Manage Students, notify, attendance)."""
    user = student.admin
    return {
        'id': student.id,
        'user_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'registration_number': student.registration_number,
        'roll_number': student.roll_number,
        'course': student.course_id,
        'course_name': student.course.name if student.course else '',
        'course_short_name': student.course.short_name if student.course else '',
        'current_semester': student.current_semester,
        'shift': student.shift,
        'shift_display': student.get_shift_display(),
        'session_label': str(student.session) if student.session else '',
        'passed_out_date': student.passed_out_date.isoformat() if student.passed_out_date else None,
        'verified': user.email_verified,
    }


def student_detail(student):
    """Student Details page + Edit Student form initial values."""
    user = student.admin
    data = student_row(student)
    data.update({
        'middle_name': user.middle_name,
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else '',
        'gender': user.gender,
        'gender_display': user.get_gender_display(),
        'address': user.address,
        'address_line1': user.address_line1,
        'address_line2': user.address_line2,
        'city': user.city,
        'province': user.province,
        'profile_pic': user.profile_pic.url if user.profile_pic else '',
        'session': student.session_id,
        'parent_full_name': student.parent_full_name,
        'parent_phone_number': student.parent_phone_number,
        'parent_relationship': student.parent_relationship,
    })
    return data


def staff_row(staff):
    user = staff.admin
    return {
        'id': staff.id,
        'user_id': user.id,
        'staff_id': staff.staff_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'verified': user.email_verified,
    }


def staff_detail(staff, assignments=None, subject_count=None):
    """Staff Details page + Edit Staff form initial values.

    `courses` carries full objects for the details page; the edit form
    normalizes them back to ids on load.
    """
    user = staff.admin
    data = staff_row(staff)
    data.update({
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else '',
        'gender': user.gender,
        'gender_display': user.get_gender_display(),
        'address': user.address,
        'address_line1': user.address_line1,
        'address_line2': user.address_line2,
        'city': user.city,
        'province': user.province,
        'profile_pic': user.profile_pic.url if user.profile_pic else '',
        'courses': [
            {'id': c.id, 'name': c.name, 'short_name': c.short_name}
            for c in staff.taught_courses
        ],
        'teaches_morning': staff.teaches_morning,
        'teaches_day': staff.teaches_day,
        'shifts_display': staff.shifts_display,
    })
    if assignments is not None:
        data['assignments'] = assignments
    if subject_count is not None:
        data['subject_count'] = subject_count
    return data


def book_dict(book, my_request=None):
    """A catalogue row. `my_request` is the signed-in student's own live
    request for this title, if any — it decides which button the row shows."""
    data = {
        'id': book.id,
        'name': book.name,
        'author': book.author,
        'isbn': book.isbn,
        'category': book.category,
        'total_copies': book.total_copies,
        'available_copies': book.available_copies,
        'copies_out': book.copies_out,
    }
    if my_request is not None:
        data['my_request'] = {
            'id': my_request.id,
            'status': my_request.status,
            'status_display': my_request.get_status_display(),
            'due_date': my_request.due_date.isoformat() if my_request.due_date else None,
        }
    else:
        data['my_request'] = None
    return data


def book_request_dict(req, for_librarian=False):
    """One borrow request. The librarian's queue additionally needs to know
    who is asking and whether a copy is free to give them."""
    data = {
        'id': req.id,
        'status': req.status,
        'status_display': req.get_status_display(),
        'book_id': req.book_id,
        'book_name': req.book.name,
        'book_author': req.book.author,
        'book_isbn': req.book.isbn,
        'student_note': req.student_note,
        'librarian_note': req.librarian_note,
        'requested_at': req.requested_at.strftime('%b. %d, %Y'),
        'decided_at': req.decided_at.strftime('%b. %d, %Y') if req.decided_at else None,
        'issued_date': req.issued_date.isoformat() if req.issued_date else None,
        'due_date': req.due_date.isoformat() if req.due_date else None,
        'returned_date': req.returned_date.isoformat() if req.returned_date else None,
        'days_overdue': req.days_overdue,
        'days_late': req.days_late,
        'fine': req.fine,
        'fine_settled': req.fine_settled,
        'fine_outstanding': req.fine_outstanding,
        # Renewal: one extension per loan, so these say both where the
        # current request stands and whether another one is even possible.
        'renewal_state': req.renewal_state,
        'renewal_state_display': req.get_renewal_state_display(),
        'renewal_reason': req.renewal_reason,
        'renewal_librarian_note': req.renewal_librarian_note,
        'renewal_requested_at': (
            req.renewal_requested_at.strftime('%b. %d, %Y')
            if req.renewal_requested_at else None),
        'renewal_decided_at': (
            req.renewal_decided_at.strftime('%b. %d, %Y')
            if req.renewal_decided_at else None),
        'due_date_before_renewal': (
            req.due_date_before_renewal.isoformat()
            if req.due_date_before_renewal else None),
        'can_request_renewal': req.can_request_renewal,
    }
    if for_librarian:
        student = req.student
        user = student.admin
        data.update({
            'student_id': student.id,
            'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
            'student_roll': student.roll_number or '',
            'student_course': student.course.short_name if student.course else '—',
            'student_semester': student.current_semester,
            'available_copies': req.book.available_copies,
            'decided_by': str(req.decided_by) if req.decided_by else None,
            'renewal_decided_by': (
                str(req.renewal_decided_by) if req.renewal_decided_by else None),
        })
    return data


def library_fine_dict(fine, for_librarian=False):
    """One fine receipt. Read-only by nature — the record is written once at
    the desk and never revised, so there is no matching input shape."""
    data = {
        'id': fine.id,
        'receipt_no': fine.receipt_no,
        'kind': fine.kind,
        'kind_display': fine.get_kind_display(),
        'amount': fine.amount,
        'days_late': fine.days_late,
        'rate_per_day': fine.rate_per_day,
        'note': fine.note,
        # The snapshot, not the FK: who took the cash has to stay legible
        # even if that librarian account is gone.
        'collected_by': fine.collected_by_name,
        'collected_on': fine.created_at.strftime('%b. %d, %Y'),
        'collected_at': fine.created_at.strftime('%b. %d, %Y, %I:%M %p'),
        'book_name': fine.request.book.name,
        'request_id': fine.request_id,
    }
    if for_librarian:
        student = fine.student
        user = student.admin
        data.update({
            'student_id': student.id,
            'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
            'student_roll': student.roll_number or '',
            'student_course': student.course.short_name if student.course else '—',
        })
    return data


def librarian_row(librarian):
    user = librarian.admin
    return {
        'id': librarian.id,
        'user_id': user.id,
        'librarian_id': librarian.librarian_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'verified': user.email_verified,
    }


def librarian_detail(librarian):
    """Librarian Details page + Edit Librarian form initial values."""
    user = librarian.admin
    data = librarian_row(librarian)
    data.update({
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else '',
        'gender': user.gender,
        'gender_display': user.get_gender_display(),
        'address': user.address,
        'address_line1': user.address_line1,
        'address_line2': user.address_line2,
        'city': user.city,
        'province': user.province,
        'profile_pic': user.profile_pic.url if user.profile_pic else '',
    })
    return data


def accountant_row(accountant):
    user = accountant.admin
    return {
        'id': accountant.id,
        'user_id': user.id,
        'accountant_id': accountant.accountant_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'verified': user.email_verified,
    }


def accountant_detail(accountant):
    """Accountant Details page + Edit Accountant form initial values."""
    user = accountant.admin
    data = accountant_row(accountant)
    data.update({
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else '',
        'gender': user.gender,
        'gender_display': user.get_gender_display(),
        'address': user.address,
        'address_line1': user.address_line1,
        'address_line2': user.address_line2,
        'city': user.city,
        'province': user.province,
        'profile_pic': user.profile_pic.url if user.profile_pic else '',
    })
    return data


# ------------------------------------------------------------------- Fees

def fee_head_dict(head):
    return {
        'id': head.id,
        'name': head.name,
        'code': head.code,
        'description': head.description,
        'recurring': head.recurring,
        'refundable': head.refundable,
    }


def fee_structure_dict(structure, with_items=True):
    data = {
        'id': structure.id,
        'course': structure.course_id,
        'course_name': structure.course.short_name if structure.course else '—',
        'session': structure.session_id,
        'session_name': str(structure.session) if structure.session else '—',
        'semester': structure.semester,
        'due_days': structure.due_days,
        'late_fine_per_day': structure.late_fine_per_day,
        'note': structure.note,
        'total': structure.total,
    }
    if with_items:
        data['items'] = [
            {
                'id': item.id,
                'head': item.head_id,
                'head_name': item.head.name,
                'amount': item.amount,
            }
            for item in structure.items.all()
        ]
    return data


def fee_invoice_dict(invoice, detail=False, for_office=False):
    """One bill.

    `detail` adds the line-by-line breakdown and the history behind the
    balance; `for_office` adds who it belongs to, which the student's own
    view has no use for.
    """
    data = {
        'id': invoice.id,
        'number': invoice.number,
        'semester': invoice.semester,
        'instalment': invoice.instalment,
        'course_name': invoice.course.short_name if invoice.course else '—',
        'session_name': str(invoice.session) if invoice.session else '—',
        'issued_date': invoice.issued_date.isoformat(),
        'due_date': invoice.due_date.isoformat(),
        'gross': invoice.gross,
        'adjustment_total': invoice.adjustment_total,
        'payable': invoice.payable,
        'paid': invoice.paid,
        'balance': invoice.balance,
        'status': invoice.status,
        'days_overdue': invoice.days_overdue,
        'is_cancelled': invoice.is_cancelled,
        'cancel_reason': invoice.cancel_reason,
    }
    if for_office:
        student = invoice.student
        user = student.admin
        data.update({
            'student_id': student.id,
            'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
            'student_roll': student.roll_number or '',
            'student_email': user.email,
        })
    if detail:
        data.update({
            'lines': [
                {'id': l.id, 'head_name': l.head_name, 'amount': l.amount}
                for l in invoice.lines.all()],
            'adjustments': [
                {
                    'id': a.id,
                    'kind': a.kind,
                    'kind_display': a.get_kind_display(),
                    'amount': a.amount,
                    'reason': a.reason,
                    'created_by_name': a.created_by_name,
                    'created_at': a.created_at.strftime('%b. %d, %Y'),
                }
                for a in invoice.adjustments.all()],
            'payments': [fee_payment_dict(p) for p in invoice.payments.all()],
        })
    return data


def fee_payment_dict(payment, for_office=False):
    """One receipt. Read-only by nature — written once and never revised, so
    as with library_fine_dict there is no matching input shape."""
    data = {
        'id': payment.id,
        'receipt_no': payment.receipt_no,
        'amount': payment.amount,
        'mode': payment.mode,
        'mode_display': payment.get_mode_display(),
        'reference': payment.reference,
        'received_on': payment.received_on.isoformat(),
        'note': payment.note,
        # The snapshot, not the FK: who took the money has to stay legible
        # after the account that took it is gone.
        'collected_by_name': payment.collected_by_name,
        'invoice_id': payment.invoice_id,
        'invoice_number': payment.invoice.number,
    }
    if for_office:
        student = payment.student
        user = student.admin
        data.update({
            'student_id': student.id,
            'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
            'student_roll': student.roll_number or '',
        })
    return data


def deposit_slip_dict(slip, for_office=False):
    """One bank-deposit claim, awaiting or past verification.

    The image URL is served to both sides: the office needs it to check the
    slip against the statement, and the student needs to see what they
    actually uploaded when the office says it can't be read.
    """
    data = {
        'id': slip.id,
        'amount': slip.amount,
        'deposited_on': slip.deposited_on.isoformat(),
        'bank_name': slip.bank_name,
        'reference': slip.reference,
        'image_url': slip.image.url if slip.image else '',
        'note': slip.note,
        'status': slip.status,
        'status_display': slip.get_status_display(),
        'reviewed_by_name': slip.reviewed_by_name,
        'reviewed_at': (slip.reviewed_at.strftime('%b. %d, %Y')
                        if slip.reviewed_at else None),
        'review_note': slip.review_note,
        'submitted_at': slip.created_at.strftime('%b. %d, %Y'),
        'invoice_id': slip.invoice_id,
        'invoice_number': slip.invoice.number,
        # Present once verified, so both sides can jump straight to the
        # receipt the slip turned into.
        'payment_id': slip.payment_id,
        'receipt_no': slip.payment.receipt_no if slip.payment_id else '',
    }
    if for_office:
        student = slip.student
        user = student.admin
        data.update({
            'student_id': student.id,
            'student_name': ("%s %s" % (user.first_name, user.last_name)).strip(),
            'student_roll': student.roll_number or '',
            # What the bill still owes, so the desk can see at a glance
            # whether the claimed amount is even possible.
            'invoice_balance': slip.invoice.balance,
        })
    return data


def subject_dict(subject):
    return {
        'id': subject.id,
        'name': subject.name,
        'code': subject.code,
        'credit_hours': subject.credit_hours,
    }
