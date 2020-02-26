from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator

from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm, UserProfileForm
from rango.bing_search import run_query

from datetime import datetime


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, "visits", "1"))
    last_visit_cookie = get_server_side_cookie(
        request, "last_visit", str(datetime.now())
    )
    last_visit_time = datetime.strptime(last_visit_cookie[:-7], "%Y-%m-%d %H:%M:%S")

    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        request.session["last_visit"] = str(datetime.now())
    else:
        request.session["last_visit"] = last_visit_cookie

    request.session["visits"] = visits


# VIEWS

class IndexView(View):
    def get(self, request):
        category_list = Category.objects.order_by("-likes")[:5]
        page_list = Page.objects.order_by("-views")[:5]

        context_dict = {}
        context_dict["boldmessage"] = "Crunchy, creamy, cookie, candy, cupcake!"
        context_dict["categories"] = category_list
        context_dict["pages"] = page_list

        visitor_cookie_handler(request)

        return render(request, "rango/index.html", context=context_dict)


class AboutView(View):
    def get(self, request):
        context_dict = {}

        visitor_cookie_handler(request)
        context_dict["visits"] = request.session["visits"]

        return render(request, "rango/about.html", context_dict)


class ShowCategoryView(View):
    def get(self, request, category_name_slug):
        context_dict = self.build_context_dict(category_name_slug, "", [])
        return render(request, "rango/category.html", context=context_dict)

    def post(self, request, category_name_slug):
        query = request.POST["query"].strip()
        result_list = []
        if query:
            result_list = run_query(query)

        context_dict = self.build_context_dict(category_name_slug, query, result_list)
        return render(request, "rango/category.html", context=context_dict)

    def build_context_dict(self, category_name_slug, query, result_list):
        context_dict = {}
        try:
            category = Category.objects.get(slug=category_name_slug)
            pages = Page.objects.filter(category=category).order_by("-views")
            context_dict["category"] = category
            context_dict["pages"] = pages
        except Category.DoesNotExist:
            context_dict["category"] = None
            context_dict["pages"] = None

        context_dict["query"] = query
        context_dict["result_list"] = result_list

        return context_dict


class AddCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        form = CategoryForm()
        return render(request, "rango/add_category.html", {"form": form})

    @method_decorator(login_required)
    def post(self, request):
        form = CategoryForm()

        if form.is_valid():
            form.save(commit=True)
            return redirect(reverse("rango:index"))
        else:
            print(form.errors)

        return render(request, "rango/add_category.html", {"form": form})


class AddPageView(View):
    @method_decorator(login_required)
    def get(self, request, category_name_slug):
        category = self.get_category(category_name_slug)
        form = PageForm()
        return render(request, "rango/add_page.html", context={"form": form, "category": category})
    
    @method_decorator(login_required)
    def post(self, request, category_name_slug):
        category = self.get_category(category_name_slug)
        form = PageForm(request.POST)

        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()

                return redirect(reverse("rango:show_category", kwargs={"category_name_slug": category_name_slug}))
        else:
            print(form.errors)
        return render(request, "rango/add_page.html", context={"form": form, "category": category})
    
    def get_category(self, category_name_slug):
        try:
            category = Category.objects.get(slug=category_name_slug)
        except Category.DoesNotExist:
            category = None
        
        if category is None:
            return redirect("/rango/")
        else:
            return category


class RestrictedView(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, "rango/restricted.html")


class GotoURLView(View):
    def get(self, request):
        try:
            id = request.GET.get("page_id")
            page = Page.objects.get(id=id)
            page.views += 1
            page.save()
            return redirect(page.url)
        except (Page.DoesNotExist, request.DoesNotExist):
            return redirect(reverse("rango:index"))
    
    def post(self, request):
        return redirect(reverse("rango:index"))


class RegisterProfileView(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, "rango/profile_registration.html", {"form": UserProfileForm()})
    
    @method_decorator(login_required)
    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()

            return redirect(reverse("rango:index"))
        else:
            print(form.errors)
            return render(request, "rango/profile_registration.html", {"form": form})