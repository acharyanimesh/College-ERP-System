from datetime import date

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import Book, IssuedBook
from .permissions import IsStaff


@api_view(['GET', 'POST'])
def book_list(request):
    if request.method == 'GET':
        # Students browse, staff manage.
        return Response([{
            'id': b.id,
            'name': b.name,
            'author': b.author,
            'isbn': b.isbn,
            'category': b.category,
        } for b in Book.objects.all()])

    if not IsStaff().has_permission(request, None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    data = request.data
    errors = {}
    for field in ('name', 'author', 'isbn', 'category'):
        if not str(data.get(field) or '').strip():
            errors[field] = ['This field is required.']
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    book = Book.objects.create(
        name=data.get('name'), author=data.get('author'),
        isbn=data.get('isbn'), category=data.get('category'))
    return Response({'id': book.id}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsStaff])
def issue(request):
    """Issue a book to a student (staff_views.issue_book)."""
    obj = IssuedBook.objects.create(
        student_id=request.data.get('student'),
        isbn=request.data.get('isbn'))
    return Response({'id': obj.id}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsStaff])
def issued(request):
    """Issued books with the late fine (staff_views.view_issued_book:
    5 per day beyond 14 days)."""
    result = []
    for i in IssuedBook.objects.all():
        days = (date.today() - i.issued_date).days
        fine = (days - 14) * 5 if days > 14 else 0
        book = Book.objects.filter(isbn=i.isbn).first()
        result.append({
            'id': i.id,
            'student_id': i.student_id,
            'isbn': i.isbn,
            'book_name': book.name if book else '',
            'issued_date': i.issued_date.isoformat(),
            'expiry_date': i.expiry_date.isoformat(),
            'fine': fine,
        })
    return Response(result)
