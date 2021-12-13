import json as js
import os
from tempfile import TemporaryFile

# Create your views here.
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.views import generic
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from scripts import filters, forms, models, script_json, tables, characters
from collections import Counter


class ScriptsListView(SingleTableMixin, FilterView):
    model = models.ScriptVersion
    table_class = tables.ScriptTable
    template_name = "index.html"
    filterset_class = filters.ScriptVersionFilter

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super(ScriptsListView, self).get_filterset_kwargs(filterset_class)
        if kwargs["data"] is None:
            kwargs["data"] = {"latest": True}
        return kwargs

    table_pagination = {"per_page": 20}
    ordering = ["-pk"]


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
        return initial

    def get_success_url(self):
        return "/script/" + str(self.script_version.script.pk)

    def form_valid(self, form):
        json = forms.get_json_content(form.cleaned_data)
        script_name = script_json.get_name_from_json(json)
        if not script_name:
            script_name = form.cleaned_data["name"]
        script, created = models.Script.objects.get_or_create(name=script_name)
        if script.versions.count() > 0:
            latest = script.latest_version()
            latest.latest = False
            latest.save()
        author = script_json.get_author_from_json(json)
        if not author:
            author = form.cleaned_data["author"]
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total"] = models.Script.objects.count()

        character_count = {}
        for type in characters.CharacterType:
            character_count[type.value] = Counter()
        for character in characters.Character:
            character_count[character.character_type.value][
                character.character_name
            ] = models.ScriptVersion.objects.filter(
                latest=True, content__contains=[{"id": character.json_id}]
            ).count()

        for type in characters.CharacterType:
            context[type.value] = character_count[type.value].most_common(5)
            context[type.value + "least"] = character_count[type.value].most_common()[
                :-6:-1
            ]

        return context


def vote_for_script(request, pk: int):
    if request.method != "POST":
        raise Http404()
    script_version = models.ScriptVersion.objects.get(pk=pk)
    if not request.session.get(str(pk), False):
        models.Vote.objects.create(script=script_version)
    request.session[str(pk)] = True
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
