# coding: utf-8

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm as UserForm, PasswordChangeForm
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse, reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Field, Button, Fieldset
from crispy_forms.bootstrap import FormActions, InlineRadios, TabHolder, Tab
from .models import Project, Wiki, SshKey, GnuPgKey, Email

CURRENT, NEW = range(2)
REPO_CHOICES = (('current', _('Commit to Current branch'),),
                ('new', _('Create a new branch')),
                )


class EditFile(forms.Form):
    content = forms.CharField(label="", required=False, widget=forms.Textarea(attrs={'rows': 120}))
    message_title = forms.CharField(label='', required=False)
    message = forms.CharField(label="", required=False, widget=forms.Textarea)
    new_branch_name = forms.CharField(label="", required=False,)
    choice_branch = forms.ChoiceField(label="", required=False, choices=REPO_CHOICES,
                                      widget=forms.RadioSelect, initial='current')

    def __init__(self, *args, **kwargs):
        url = kwargs.pop('url')
        self.code = kwargs.pop('code' or None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'col-md-9'
        self.helper.form_action = url
        self.helper.layout = Layout(
            Fieldset(HTML('<br>'),
                     HTML("<h4 class=\"\">Edit File</h4>"),
                     Field('content', css_class='col-md-9'),
                     TabHolder(Tab('Commit changes',
                                   HTML("<br>"),
                                   Div(Field('message_title', css_class='col-md-6',
                                             placeholder=_('Commit Message Title')), css_class='offset2'),
                                   Div(Field('message', css_class='col-md-6',
                                             placeholder=_('Commit message (Optional)')), css_class='offset2'),
                                   Div(InlineRadios('choice_branch',), css_class='offset2'),
                                   Div(Field('new_branch_name', placeholder="Proposed new branch name",
                                             css_class='col-md-4'),
                                       css_class='col-md-6 offset2 collapse out',
                                       css_id='new_branch_name'),)), css_class=''),
            FormActions(Submit('', 'Save changes'), Button('cancel', 'Cancel'),
                        style="background: white;")
        )

    def clean(self):
        cleaned_data = super(EditFile, self).clean()
        content = cleaned_data['content']
        if not content or not content.strip(''):
            raise forms.ValidationError(_('File contains no Content'))

        if content == self.code:
            raise forms.ValidationError(_('File Content did not change'))

        message_title = cleaned_data['message_title']

        if not message_title:
            raise forms.ValidationError(_('Please enter a Commit Title'))

        choice_branch = cleaned_data['choice_branch']

        if choice_branch == 'new':
            new_branch_name = cleaned_data['new_branch_name']
            if not new_branch_name or not new_branch_name.strip(''):
                raise forms.ValidationError(_(''))
        return cleaned_data


class SshKeyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'gs-profile col-md-9'
        self.helper.form_action = reverse('add_ssh_key', args=[user.username])
        self.helper.add_input(Submit('', "Add Key", css_class='btn btn-success'))
        self.helper.layout = Layout(HTML("<h2 class=\"form-signin-heading\">Add Ssh Keys</h2>"),
                                    Div(Div(Field('title', css_class='col-md-9'), css_class='col-md-9'),
                                        Div(Field('key', css_class='col-md-9'), css_class='col-md-9'),
                                        css_class='row'),)

    class Meta:
        model = SshKey
        fields = ('title', 'key')


class GnuPgKeyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'gs-profile col-md-9'
        self.helper.form_action = reverse('add_gnupg_key', args=[user.username])
        self.helper.add_input(Submit('', "Add Key", css_class='btn btn-success'))
        self.helper.layout = Layout(HTML("<h2 class=\"form-signin-heading\">Add GnuPgp Keys</h2>"),
                                    Div(Div(Field('title', css_class='col-md-9'), css_class='col-md-9'),
                                        Div(Field('key', css_class='col-md-9'), css_class='col-md-9'),
                                        css_class='row'),)

    class Meta:
        model = GnuPgKey
        fields = ('title', 'key')


class ChangePasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = args[0]
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'gs-profile col-md-9'
        self.helper.form_action = reverse('change_password', args=[self.user.username])
        self.helper.add_input(Submit('', _("Update"), css_class='btn btn-success'))
        self.helper.layout = Layout(HTML("<h2 class=\"form-signin-heading\">Change Password</h2>"),
                                    Div(Div(Field('old_password', css_class='col-md-9'), css_class='col-md-9'),
                                    Div(Field('new_password1', css_class='col-md-9'), css_class='col-md-9'),
                                    Div(Field('new_password2', css_class='col-md-9'), css_class='col-md-9'),
                                    css_class='row'),
                                    )

    @staticmethod
    def get_edit_change_url():
        return reverse('change_password')


class ChangeEmailForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'gs-profile col-md-9'
        self.helper.form_action = reverse('change_email', args=[user.username])
        self.helper.add_input(Submit('', _("Update"), css_class='btn btn-success'))
        self.helper.layout = Layout(HTML("<h4 class=\"form-signin-heading\">Change Primary Email</h4>"),
                                    Div(Div(Field('email', css_class='col-md-4'), css_class='col-md-9'),
                                    css_class='row'),
                                    )

    class Meta:
        model = User
        fields = ('email',)


class AddEmailForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'gs-profile col-md-9'
        self.helper.form_action = reverse('add_email', args=[user.username])
        self.helper.add_input(Submit('', _("Add!"), css_class='btn btn-success'))
        self.helper.layout = Layout(HTML("<h4 class=\"form-signin-heading\">Add Email</h4>"),
                                    Div(Div(Field('email', css_class='col-md-4'), css_class='col-md-9'),
                                    css_class='row'),
                                    )

    class Meta:
        model = Email
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data["email"]

        try:
            Email.objects.get(email=email)
            raise forms.ValidationError("Email already exists")
        except Email.DoesNotExist:
            try:
                User.objects.get(email=email)
                raise forms.ValidationError("Email already exists")
            except User.DoesNotExist:
                return email


class UserCreationForm(UserForm):
    """ Require email address when a user signs up """
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'tomtom1'}),
                               label=_('Username'), max_length=75, required=True)
    email = forms.EmailField(widget=forms.TextInput(attrs={'placeholder': 'me@example.com'}),
                             label=_('Email'), max_length=75, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy('signup')
        self.helper.layout = Layout(
                                    Fieldset(
                                             HTML("<br>"),
                                             HTML("<h2 class=\"form-signin-heading text-center\"> Signup </h2>"),
                                             Field('username',),
                                             Field('email',),
                                             Field('password1',),
                                             Field('password2',),
                                             FormActions(Submit('Register', "Register", css_class='btn btn-success'),),
                                            ),
               )
        super().__init__(*args, **kwargs)


class CreateProjectForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'col-md-9'
        self.helper.form_action = reverse_lazy('create_new_project')
        self.helper.layout = Layout(Field('name'),
                                    Field('description', css_class="input-block-level"),
                                    Field('is_private'),
                                    Field('poster'),
                                    HTML("<button type=\"submit\" class=\"btn btn-primary btn-lg btn-block\">"
                                         "Create Project</button>"),
                                    )
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "Project name"
        self.fields["description"].label = "Description"
        self.fields['name'].widget.attrs = {'placeholder': 'html-project'}
        self.fields['description'].widget.attrs = {'placeholder': 'Project description'}

    class Meta:
        exclude = ('date_created', 'date_updated', 'path', 'repo',
                   'contributors', 'downloads', 'clones', 'slug')
        model = Project

    def clean_name(self):
        name = self.cleaned_data.get('name', None)
        if not None:
            clean_name = '_'.join(name.split(' '))
            return clean_name
        raise forms.ValidationError("Field Name can not be empty")


class LoginForm(forms.Form):
    username = forms.CharField(label=_("username"),
                               required=True)
    password = forms.CharField(label=_("password"),
                               widget=forms.PasswordInput(render_value=False),
                               required=True)

    def __init__(self, *args, **kwargs):
        kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy('login')
        self.helper.form_class = 'form-signin'
        self.helper.layout = Layout(
                                    Fieldset(HTML("<br>"),
                                             HTML("<h2 class=\"form-signin-heading text-center\"> Sign in </h2>"),
                                             Field('username', placeholder="Username / Email",),
                                             Field('password', placeholder="password"),
                                             HTML("<label class=\"checkbox\"><input type=\"checkbox\" "
                                                  "value=\"remember-me\">\
                                             Remember me </label>"),
                                             HTML("<a href=\"/resetpassword\" class=\"text-danger float-right\">"
                                                  "Reset it!</a>"),
                                             HTML("<button type=\"submit\" "
                                                  "class=\"btn btn-lg btn-primary btn-block\">Sign in</button>"),
                                             )
        )

    def get_user(self):
        return authenticate(
            username=self.cleaned_data.get('username', '').lower().strip(),
            password=self.cleaned_data.get('password', ''),
        )


class WikiForm(forms.ModelForm):
    text = forms.Textarea()

    def __init__(self, *args, **kwargs):
        repo_name = kwargs.pop('repo_name')
        project_name = kwargs.pop('project_name')

        self.helper = FormHelper()
        self.helper.form_method = 'POST'

        self.helper.form_action = reverse_lazy('create_wiki', args=(repo_name, project_name))

        self.helper.form_class = 'form-signin'
        self.helper.layout = Layout(HTML("<h2 class=\"form-signin-heading\"> Create Wiki </h2>"),
                                    Field('text', css_class="input-block-level",
                                          placeholder=_("Write some text here"), ),
                                    FormActions(Submit('submit', "submit",
                                                       css_class="btn btn-large btn-block btn-primary"),
                                                )
                                    )
        super().__init__(*args, **kwargs)

    class Meta:
        fields = ("text",)
        model = Wiki


class WikiUpdateForm(WikiForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        repo_name = kwargs.get('repo_name')
        project_name = kwargs.get('project_name')
        self.helper.form_action = reverse_lazy('update_wiki',
                                               args=(repo_name,
                                                     project_name))
