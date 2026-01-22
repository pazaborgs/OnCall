from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import UserProfileForm

User = get_user_model()


@login_required
def profile_view(request):
    user = request.user

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Seu perfil foi atualizado com sucesso!")
            return redirect("profile_view")
        else:
            messages.error(request, "Corrija os erros abaixo.")
    else:
        form = UserProfileForm(instance=user)

    return render(
        request,
        "account/profile.html",
        {
            "user": user,
            "form": form,
        },
    )
