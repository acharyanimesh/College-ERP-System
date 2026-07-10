from django import forms
from django.forms.widgets import DateInput, TextInput
from django.core.validators import RegexValidator

from .models import *
from . import models


def format_subject_code(value):
    """Normalize a subject code to UPPERCASE with a single space after the
    first 3 characters, e.g. 'abc123' -> 'ABC 123'."""
    code = (value or '').strip().upper().replace(' ', '')
    if len(code) > 3:
        code = code[:3] + ' ' + code[3:]
    return code


# Live (client-side) version of the same formatting, applied as the user types.
SUBJECT_CODE_ONINPUT = (
    "this.value = this.value.toUpperCase().replace(/\\s+/g, '')"
    ".replace(/^(.{3})(.+)$/, '$1 $2')"
)


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'


class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'gender',  'password','profile_pic', 'address' ]


class StudentForm(CustomUserForm):
    registration_number = forms.CharField(
        required=True, max_length=14, label='Registration Number',
        validators=[RegexValidator(r'^\d{4}-\d{4}-\d{4}$', 'Registration number must be 12 digits (formatted as XXXX-XXXX-XXXX)')])
    roll_number = forms.CharField(
        required=True, max_length=6, label='Roll Number',
        validators=[RegexValidator(r'^\d{6}$', 'Roll number must be exactly 6 digits')])
    address_line1 = forms.CharField(required=True, label='Address Line 1')
    address_line2 = forms.CharField(required=False, label='Address Line 2')
    city = forms.CharField(required=False, label='City')
    province = forms.CharField(required=False, label='Province')
    phone_number = forms.CharField(required=False)
    date_of_birth = forms.DateField(
        required=False, widget=DateInput(attrs={'type': 'date'}))
    shift = forms.ChoiceField(choices=Student._meta.get_field('shift').choices, label='Shift')
    current_semester = forms.IntegerField(
        min_value=1, initial=1, label='Current Semester',
        widget=forms.NumberInput(attrs={'min': 1, 'step': 1}),
        help_text="The semester this student is currently in (new students start at 1).")
    middle_name = forms.CharField(required=False, label='Middle Name')
    parent_full_name = forms.CharField(
        required=True, max_length=150, label="Parent's Full Name")
    parent_phone_number = forms.CharField(
        required=True, max_length=20, label="Parent's Phone Number")
    parent_relationship = forms.ChoiceField(
        required=True, label='Relationship with Student',
        choices=[('Father', 'Father'), ('Mother', 'Mother'),
                 ('Guardian', 'Guardian'), ('Other', 'Other')])

    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)
        self.fields.pop('address', None)
        if kwargs.get('instance'):
            admin = kwargs.get('instance').admin
            self.fields['middle_name'].initial = admin.middle_name
            self.fields['phone_number'].initial = admin.phone_number
            self.fields['date_of_birth'].initial = admin.date_of_birth
            self.fields['address_line1'].initial = admin.address_line1
            self.fields['address_line2'].initial = admin.address_line2
            self.fields['city'].initial = admin.city
            self.fields['province'].initial = admin.province

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields + \
            ['registration_number', 'roll_number', 'course', 'session', 'shift', 'current_semester',
             'parent_full_name', 'parent_phone_number', 'parent_relationship']


class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields


class StaffForm(CustomUserForm):
    staff_id = forms.CharField(
        required=True, max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'Staff ID must be exactly 6 digits')])
    address_line1 = forms.CharField(required=True, label='Address Line 1')
    address_line2 = forms.CharField(required=False, label='Address Line 2')
    city = forms.CharField(required=False, label='City')
    province = forms.CharField(required=False, label='Province')
    phone_number = forms.CharField(required=False)
    date_of_birth = forms.DateField(
        required=False, widget=DateInput(attrs={'type': 'date'}))
    teaches_morning = forms.BooleanField(required=False, label='Morning Shift')
    teaches_day = forms.BooleanField(required=False, label='Day Shift')

    def __init__(self, *args, **kwargs):
        super(StaffForm, self).__init__(*args, **kwargs)
        self.fields.pop('address', None)
        # Checkboxes shouldn't carry the .form-control class added by FormSettings.
        for f in ('teaches_morning', 'teaches_day'):
            self.fields[f].widget.attrs['class'] = 'form-check-input'
        if kwargs.get('instance'):
            admin = kwargs.get('instance').admin
            self.fields['phone_number'].initial = admin.phone_number
            self.fields['date_of_birth'].initial = admin.date_of_birth
            self.fields['address_line1'].initial = admin.address_line1
            self.fields['address_line2'].initial = admin.address_line2
            self.fields['city'].initial = admin.city
            self.fields['province'].initial = admin.province

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('teaches_morning') and not cleaned.get('teaches_day'):
            raise forms.ValidationError(
                "Please assign the staff to at least one shift (Morning or Day).")
        return cleaned

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields + \
            ['staff_id', 'phone_number', 'date_of_birth',
             'teaches_morning', 'teaches_day']


class CourseForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name', 'abbreviation', 'semesters']
        model = Course


class SubjectForm(FormSettings):
    # Course assignment + per-course semester are handled manually in the
    # view/template (see edit_subject), not as ModelForm fields.

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        # Subject codes are uppercase with a space after the first 3 chars
        # (e.g. 'ABC 123') — format live as the user types.
        self.fields['code'].widget.attrs.update({
            'class': 'form-control text-uppercase',
            'oninput': SUBJECT_CODE_ONINPUT,
        })

    def clean_code(self):
        return format_subject_code(self.cleaned_data.get('code'))

    class Meta:
        model = Subject
        fields = ['name', 'code', 'credit_hours']
        labels = {'code': 'Subject Code'}


class AddSubjectForm(FormSettings):
    # Courses + per-course semesters are handled manually in add_subject.

    def __init__(self, *args, **kwargs):
        super(AddSubjectForm, self).__init__(*args, **kwargs)
        # Subject codes are uppercase with a space after the first 3 chars
        # (e.g. 'ABC 123') — format live as the user types.
        self.fields['code'].widget.attrs.update({
            'class': 'form-control text-uppercase',
            'oninput': SUBJECT_CODE_ONINPUT,
        })

    def clean_code(self):
        return format_subject_code(self.cleaned_data.get('code'))

    class Meta:
        model = Subject
        fields = ['name', 'code', 'credit_hours']
        labels = {'code': 'Subject Code'}


class SessionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Session
        fields = '__all__'
        widgets = {
            'start_year': DateInput(attrs={'type': 'date'}),
            'end_year': DateInput(attrs={'type': 'date'}),
        }


class LeaveReportStaffForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStaff
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStaffForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStaff
        fields = ['feedback']


class LeaveReportStudentForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStudent
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStudentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStudent
        fields = ['feedback']


class StudentEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields 


class StaffEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields


#todos
# class TodoForm(forms.ModelForm):
#     class Meta:
#         model=Todo
#         fields=["title","is_finished"]

#issue book

class IssueBookForm(forms.Form):
    isbn2 = forms.ModelChoiceField(queryset=models.Book.objects.all(), empty_label="Book Name [ISBN]", to_field_name="isbn", label="Book (Name and ISBN)")
    name2 = forms.ModelChoiceField(queryset=models.Student.objects.all(), empty_label="Name ", to_field_name="", label="Student Details")
    
    isbn2.widget.attrs.update({'class': 'form-control'})
    name2.widget.attrs.update({'class':'form-control'})
