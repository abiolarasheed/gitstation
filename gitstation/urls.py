# coding: utf-8

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_view
from django.contrib.auth.views import LogoutView
from django.urls import include, path, reverse_lazy
from django.views.generic import TemplateView

import gitapp.views as views

admin.autodiscover()

urlpatterns = [
    path('download/<repo_name>/<project_name>/', views.DownloadView.as_view(),
         name='download_project'),
    path('', TemplateView.as_view(template_name="index.html"), name="index"),
    path('register/', views.UserRegistrationView.as_view(), name='signup'),
    path('login/', views.MyLoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),
    url(r'<repo_name>/((?P<project_name>.*).git)/info/refs$', views.GitView.as_view(), name='push_n_clone_fetch'),
    path('encoding-error/', views.EncodingErrorView.as_view(), name='encoding_error'),
    path('<repo_name>/<project_name>/commits/<branch>/', views.ListCommitsView.as_view(), name='commits'),
    url(r'^(?P<repo_name>.*)/(?P<project_name>.*)/{0}/$'.format(settings.SOURCE),
        views.DisplayFileView.as_view(), name='display_file'),
    url(r'^(?P<repo_name>.*)/(?P<project_name>.*)/file-history/(.*)/$',
        views.HistoryView.as_view(), name='file_history'),
    url(r'^(?P<repo_name>.*)/(?P<project_name>.*)/edit-file/(.*)/$', views.EditCodeView.as_view(), name='edit_file'),
    url(r'^(?P<repo_name>.*)/(?P<project_name>.*)/render-as-text/(.*)/$', views.RenderFileAsTextView.as_view(),
        name='render_file_as_text'),
    path('admin/', admin.site.urls),
    path('account/', views.AccountView.as_view(), name='profile'),
    path('<username>/wall/', views.UserWallView.as_view(), name='wall'),
    path('star/<slug:slug>/', views.UpdateRepoStarsView.as_view(), name='star'),
    path('create-new-project/', views.CreateProjectView.as_view(), name='create_new_project'),
    path('change-repo-status/<slug:slug>/<status>/', views.ChangeRepoStatusView.as_view(),
         name='change_repo_status'),
    path('<username>/add-ssh-key/', views.CreateSshKeyView.as_view(), name='add_ssh_key'),
    path('<username>/view/ssh-key/', views.SshKeyDetailView.as_view(), name='view_ssh_key'),
    path('<username>/delete/ssh-key/<int:pk>/', views.DeleteSshKeyView, name='delete_ssh_key'),
    path('<username>/add-gnupg-key/', views.CreateGpgKeysView.as_view(), name='add_gnupg_key'),
    path('<username>/view/gnupg-key/', views.ViewGpgKeysView.as_view(), name='view_gnupg_key'),
    path('<username>/delete/gnupg-key/<int:pk>/', views.DeleteGpgKeysView.as_view(), name='delete_gnupg_key'),
    path('<username>/add-email/', views.AddEmailView.as_view(), name='add_email'),
    path('<username>/change-email/', views.ChangeEmail.as_view(), name='change_email'),
    path('<username>/view-emails/', views.EmailsDetailView.as_view(), name='view_emails'),
    path('<username>/view-password/', views.ViewPasswordView.as_view(), name='view_password'),
    path('<username>/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('read-wiki/<repo_name>/<project_name>/', views.WikiDetailView.as_view(), name='read_wiki'),
    path('create-wiki/<repo_name>/<project_name>/', views.CreateWikiView.as_view(), name='create_wiki'),
    path('update-wiki/<repo_name>/<project_name>/', views.UpdateWikiView.as_view(), name='update_wiki'),
    path('delete-wiki/<repo_name>/<project_name>/', views.WikiDeleteView.as_view(), name='delete_wiki'),
    path('list-files-in-repo/<repo_name>/<project_name>/',
         views.FilesInRepo.as_view(), name='list_files_in_repo'),
    path('<repo_name>/<project_name>/', views.ProjectDetailView.as_view(),
         name='specific_project'),
    path('resetpassword/', auth_view.password_reset),
    path('resetpassword/passwordreset/', auth_view.password_reset_done, name='password_reset_done'),
    path('reset/done/', auth_view.password_reset_complete),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_view.password_reset_confirm),
    path('', include('gitapp.urls')),
]
