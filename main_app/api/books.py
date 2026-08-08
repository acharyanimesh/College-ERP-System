"""The book catalogue. Everyone signed in may browse it; only the librarian
may change it. Borrowing lives next door in library.py."""
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..forms import BookForm
from ..models import Book, BookRequest, Student
from .permissions import IsLibrarian, STUDENT
from .serializers import book_dict, form_errors


def _open_requests_by_book(user):
    """{book_id: BookRequest} for the signed-in student's live requests, so
    the catalogue can show each row's own state without an N+1 lookup."""
    if str(user.user_type) != STUDENT:
        return {}
    student = Student.objects.filter(admin=user).first()
    if student is None:
        return {}
    return {
        r.book_id: r for r in BookRequest.objects.filter(
            student=student, status__in=BookRequest.OPEN_STATUSES)
    }


@api_view(['GET', 'POST'])
def book_list(request):
    if request.method == 'GET':
        # Students browse, the librarian manages.
        mine = _open_requests_by_book(request.user)
        books = Book.objects.all().order_by(Lower('name'))
        return Response([book_dict(b, mine.get(b.id)) for b in books])

    if not IsLibrarian().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    form = BookForm(request.data)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    book = form.save()
    return Response(book_dict(book), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsLibrarian])
def book_item(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'GET':
        return Response(book_dict(book))

    if request.method == 'DELETE':
        live = book.requests.filter(status__in=BookRequest.OPEN_STATUSES).count()
        if live:
            return Response(
                {'detail': "This book has %d open request%s or loan%s against "
                           "it. Settle those before removing it from the "
                           "catalogue." % (live, '' if live == 1 else 's',
                                           '' if live == 1 else 's')},
                status=status.HTTP_400_BAD_REQUEST)
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    form = BookForm(request.data, instance=book)
    if not form.is_valid():
        return Response(form_errors(form), status=status.HTTP_400_BAD_REQUEST)
    # Shrinking the shelf below what is already lent out would make
    # available_copies lie, so refuse it rather than clamp it.
    wanted = form.cleaned_data.get('total_copies') or 0
    if wanted < book.copies_out:
        return Response(
            {'total_copies': ["%d cop%s of this book %s currently out; the "
                              "total can't be lower than that."
                              % (book.copies_out,
                                 'y' if book.copies_out == 1 else 'ies',
                                 'is' if book.copies_out == 1 else 'are')]},
            status=status.HTTP_400_BAD_REQUEST)
    book = form.save()
    return Response(book_dict(book))
