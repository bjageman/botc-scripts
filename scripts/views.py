import json as js
import os
from tempfile import TemporaryFile

# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.views import generic
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from scripts import filters, forms, models, script_json, tables, characters
from collections import Counter

from typing import Dict, Any


class ScriptsListView(SingleTableMixin, FilterView):
    model = models.ScriptVersion
    table_class = tables.ScriptTable
    template_name = "scriptlist.html"
    filterset_class = filters.ScriptVersionFilter

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super(ScriptsListView, self).get_filterset_kwargs(filterset_class)
        if kwargs["data"] is None:
            kwargs["data"] = {"latest": True}
        return kwargs

    table_pagination = {"per_page": 20}
    ordering = ["-pk"]


class UserScriptsListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.ScriptVersion
    table_class = tables.ScriptTable
    template_name = "scriptlist.html"
    filterset_class = filters.ScriptVersionFilter

    def get_table_data(self):
        return models.ScriptVersion.objects.filter(script__owner=self.request.user)

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super(UserScriptsListView, self).get_filterset_kwargs(filterset_class)
        if kwargs["data"] is None:
            kwargs["data"] = {"latest": True}
        return kwargs

    table_pagination = {"per_page": 20}
    ordering = ["-pk"]


def get_json_additions(old_json, new_json):
    for old_id in old_json:
        if old_id["id"] == "_meta":
            continue
        for new_id in new_json:
            if new_id["id"] == "_meta":
                continue

            if old_id == new_id:
                new_json.remove(new_id)

    for new_id in new_json:
        if new_id["id"] == "_meta":
            new_json.remove(new_id)
            break

    return new_json


class ScriptView(generic.DetailView):
    template_name = "script.html"
    model = models.Script

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "sel_name" in self.request.GET:
            context["script_version"] = self.object.versions.get(
                version=self.request.GET["sel_name"]
            )
        else:
            context["script_version"] = self.object.versions.last()
        curr_version = context["script_version"].version

        changes = {}
        diff_script_version = None
        for script_version in self.object.versions.all().order_by("-version"):

            # If we're looking at an older script, don't show changes future to that.
            if script_version.version.internal_integer > curr_version.internal_integer:
                continue

            if diff_script_version:
                changes[diff_script_version.version] = {}
                changes[diff_script_version.version]["additions"] = get_json_additions(
                    script_version.content.copy(), diff_script_version.content.copy()
                )
                changes[diff_script_version.version]["deletions"] = get_json_additions(
                    diff_script_version.content.copy(), script_version.content.copy()
                )
                changes[diff_script_version.version][
                    "previous_version"
                ] = script_version.version
            diff_script_version = script_version

        context["changes"] = changes

        return context


class ScriptUploadView(generic.FormView):
    template_name = "upload.html"
    form_class = forms.ScriptForm
    script_version = None

    def get_initial(self):
        initial = super().get_initial()
        script_pk = self.request.GET.get("script", None)
        if script_pk:
            script = models.Script.objects.get(pk=script_pk)
            if script:
                script_version = script.latest_version()
                initial["name"] = script.name
                initial["author"] = script_version.author
                initial["version"] = script_version.version
                if script_version.notes:
                    initial["notes"] = script_version.notes
        return initial

    def get_form_kwargs(self):
        """
        We want to provide the user to the Form's clean method so the user
        can't overwrite scripts owned by someone else.
        """
        kwargs = super(ScriptUploadView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_form(self):
        """
        If this is an anonymous user, don't allow them to add notes.
        """
        form = super().get_form(self.form_class)

        # If this user isn't authenticated, do allow them to add notes or upload anonymously
        # (since it will be anonymous anyway).
        if not self.request.user.is_authenticated:
            form.fields.pop("notes")
            form.fields.pop("anonymous")
        else:
            script_pk = self.request.GET.get("script", None)
            if script_pk:
                script = models.Script.objects.get(pk=script_pk)

                # If this script is owned by someone, and it is not the currently logged in
                # user, don't show the notes field.
                if script and script.owner and (script.owner != self.request.user):
                    form.fields.pop("notes")

                # If this is an update to an existing script, we can't make it anonymous.
                if script:
                    form.fields.pop("anonymous")

        return form

    def get_success_url(self):
        return "/script/" + str(self.script_version.script.pk)

    def form_valid(self, form):
        user = self.request.user
        json = forms.get_json_content(form.cleaned_data)

        # Use the script name from the JSON in preference of the text field.
        script_name = script_json.get_name_from_json(json)
        if not script_name:
            script_name = form.cleaned_data["name"]

        # Either get the current script, or create a new one based on the name.
        script, created = models.Script.objects.get_or_create(name=script_name)

        # We only want to set the owner on newly created scripts, so if we've
        # just created the script and the user is authenticated, set the owner to this user
        # unless they uploaded anonymously.
        if created and user.is_authenticated and not form.cleaned_data["anonymous"]:
            script.owner = user
            script.save()

        # Use the author in the JSON in preference of the text field.
        author = script_json.get_author_from_json(json)
        if not author:
            author = form.cleaned_data["author"]

        # The user may just be updating some info about the current script, so let them
        # do that if the JSON content is the same
        if not created:
            latest = script.latest_version()
            if latest and (latest.content == json):
                # We're updating an existing entry.
                self.script_version = latest
                self.script_version.script_type = form.cleaned_data["script_type"]
                self.script_version.author = author
                if form.cleaned_data.get("notes", None):
                    self.script_version.notes = form.cleaned_data["notes"]
                if form.cleaned_data.get("pdf", None):
                    self.script_version.pdf = form.cleaned_data["pdf"]
                self.script_version.tags.set(form.cleaned_data["tags"])
                self.script_version.save()
                return super().form_valid(form)
            else:
                # If the content has changed, we're creating a new version
                # so set the previous latest version is no longer the latest.
                latest.latest = False
                latest.save()

        # Create the Script Version object from the form.
        if form.cleaned_data.get("notes", None):
            self.script_version = models.ScriptVersion.objects.create(
                version=form.cleaned_data["version"],
                script_type=form.cleaned_data["script_type"],
                content=json,
                script=script,
                pdf=form.cleaned_data["pdf"],
                author=author,
                notes=form.cleaned_data["notes"],
            )
        else:
            self.script_version = models.ScriptVersion.objects.create(
                version=form.cleaned_data["version"],
                script_type=form.cleaned_data["script_type"],
                content=json,
                script=script,
                pdf=form.cleaned_data["pdf"],
                author=author,
            )
        self.script_version.tags.set(form.cleaned_data["tags"])

        return super().form_valid(form)


class StatisticsView(generic.TemplateView):
    template_name = "statistics.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        stats_character = None

        if "character" in kwargs:
            if characters.Character.get(kwargs.get("character")):
                stats_character = characters.Character.get(kwargs.get("character"))
                queryset = models.ScriptVersion.objects.filter(
                    latest=True, content__contains=[{"id": stats_character.json_id}]
                )
                context["total"] = queryset.count()
            else:
                raise Http404()
        else:
            context["total"] = models.Script.objects.count()
            queryset = models.ScriptVersion.objects.filter(latest=True)

        character_count = {}
        for type in characters.CharacterType:
            character_count[type.value] = Counter()
        for character in characters.Character:
            # If we're on a Character Statistics page, don't include this character in the count.
            if character == stats_character:
                continue

            character_count[character.character_type.value][
                character
            ] = queryset.filter(content__contains=[{"id": character.json_id}]).count()

        for type in characters.CharacterType:
            context[type.value] = character_count[type.value].most_common(5)
            context[type.value + "least"] = character_count[type.value].most_common()[
                :-6:-1
            ]

        return context


class UserDeleteView(LoginRequiredMixin, generic.TemplateView):
    """
    Deletes the currently signed-in user.
    """

    template_name = "account/delete.html"

    def post(self, request):
        user = request.user
        logout(request)
        user.delete()
        return HttpResponseRedirect("/")


def vote_for_script(request, pk: int):
    if request.method != "POST":
        raise Http404()
    script_version = models.ScriptVersion.objects.get(pk=pk)

    # Authenticated users should create votes with their user profile.
    if request.user.is_authenticated:
        if models.Vote.objects.filter(
            user=request.user, script=script_version
        ).exists():
            # If this user has already voted for this script, delete that vote. Use filter.exists()
            # because it is more performant
            vote = models.Vote.objects.get(user=request.user, script=script_version)
            vote.delete()
        else:
            # Otherwise create a new vote.
            models.Vote.objects.create(user=request.user, script=script_version)
    return redirect(request.POST["next"])


def download_json(request, pk: int, version: str) -> FileResponse:
    script = models.Script.objects.get(pk=pk)
    script_version = script.versions.get(version=version)
    json_content = js.JSONEncoder().encode(script_version.content)
    temp_file = TemporaryFile()
    temp_file.write(json_content.encode("utf-8"))
    temp_file.flush()
    temp_file.seek(0)
    response = FileResponse(
        temp_file, as_attachment=True, filename=(script.name + ".json")
    )
    return response


def download_pdf(request, pk: int, version: str) -> FileResponse:
    script = models.Script.objects.get(pk=pk)
    script_version = script.versions.get(version=version)
    if os.environ.get("DJANGO_HOST", None):
        return FileResponse(script_version.pdf, as_attachment=True)
    else:
        return FileResponse(open(script_version.pdf.name, "rb"), as_attachment=True)
