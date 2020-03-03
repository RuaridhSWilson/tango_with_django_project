from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views import View
from django.utils.decorators import method_decorator

from rango.models import Category, Page, UserProfile
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


def get_category_list(max_results=0, starts_with=""):
    category_list = []

    if starts_with:
        category_list = Category.objects.filter(name__istartswith=starts_with)

    if max_results > 0:
        if len(category_list) > max_results:
            category_list = category_list[:max_results]

    return category_list


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
        return render(
            request, "rango/add_page.html", context={"form": form, "category": category}
        )

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

                return redirect(
                    reverse(
                        "rango:show_category",
                        kwargs={"category_name_slug": category_name_slug},
                    )
                )
        else:
            print(form.errors)
        return render(
            request, "rango/add_page.html", context={"form": form, "category": category}
        )

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
        return render(
            request, "rango/profile_registration.html", {"form": UserProfileForm()}
        )

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


class ProfileView(View):
    def get_user_details(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        form = UserProfileForm(
            {"website": user_profile.website, "picture": user_profile.picture}
        )

        return user, user_profile, form

    @method_decorator(login_required)
    def get(self, request, username):
        try:
            user, user_profile, form = self.get_user_details(username)
        except TypeError:
            return redirect(reverse("rango:index"))

        context_dict = {
            "user_profile": user_profile,
            "selected_user": user,
            "form": form,
        }

        return render(request, "rango/profile.html", context_dict)

    @method_decorator(login_required)
    def post(self, request, username):
        try:
            user, user_profile, form = self.get_user_details(username)
        except TypeError:
            return redirect(reverse("rango:index"))

        if request.user == user:
            form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

            if form.is_valid():
                form.save(commit=True)
                return redirect("rango:profile", user.username)
            else:
                print(form.errors)

        context_dict = {
            "user_profile": user_profile,
            "selected_user": user,
            "form": form,
        }

        return render(request, "rango/profile.html", context_dict)


class ListProfilesView(View):
    @method_decorator(login_required)
    def get(self, request):
        profiles = UserProfile.objects.all()

        return render(
            request, "rango/list_profiles.html", {"user_profile_list": profiles}
        )


class LikeCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        category_id = request.GET["category_id"]

        try:
            category = Category.objects.get(id=int(category_id))
        except (Category.DoesNotExist, ValueError):
            return HttpResponse(-1)

        category.likes += 1
        category.save()

        return HttpResponse(category.likes)


class CategorySuggestionView(View):
    def get(self, request):
        if "suggestion" in request.GET:
            suggestion = request.GET["suggestion"]
        else:
            suggestion = ""

        category_list = get_category_list(max_results=8, starts_with=suggestion)

        if len(category_list) == 0:
            category_list = Category.objects.order_by("-likes")

        return render(request, "rango/categories.html", {"categories": category_list})
