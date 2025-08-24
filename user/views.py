from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User
from .forms import UserUpdateForm
from django.urls import reverse


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/profile.html'


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/profile_edit.html'

    def get_success_url(self):
        return reverse('user:profile_view', kwargs={'pk': self.object.pk})

    def get_object(self, queryset=None):
        return self.request.user
    