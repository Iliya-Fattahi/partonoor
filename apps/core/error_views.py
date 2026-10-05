from django.shortcuts import render


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler500(request):
    # Note: 500 handler must not depend on context processors touching the DB
    # if the DB itself is the failure — keep this template minimal.
    return render(request, "errors/500.html", status=500)
