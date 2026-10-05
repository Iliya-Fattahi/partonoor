"""
A real WYSIWYG widget for Article.content in the admin, built on Quill.js
(loaded from the same CDN allowlist already used by the rest of the project —
no extra Python dependency needed). This satisfies spec section 74
("convenient interface for articles... usable for non-programmers")
without adding a heavy server-side rich-text package.

Output is still run through apps.core.sanitize.sanitize_article_html on
save() (see apps/articles/models.py) — the editor is a UX convenience,
never the security boundary.
"""
from django import forms
from django.utils.safestring import mark_safe


class QuillEditorWidget(forms.Textarea):
    """Renders a Quill editor bound to a hidden textarea holding the real HTML value."""

    class Media:
        css = {
            "all": ["https://cdn.jsdelivr.net/npm/quill@1.3.7/dist/quill.snow.css"],
        }
        js = ["https://cdn.jsdelivr.net/npm/quill@1.3.7/dist/quill.min.js"]

    def render(self, name, value, attrs=None, renderer=None):
        textarea_html = super().render(name, value, attrs, renderer)
        widget_id = (attrs or {}).get("id", f"id_{name}")
        editor_id = f"{widget_id}_quill_editor"

        script = f"""
        <div id="{editor_id}" class="quill-rtl" style="min-height:340px;background:#fff;color:#111;"></div>
        <script>
        (function() {{
            function initQuill() {{
                var textarea = document.getElementById("{widget_id}");
                var container = document.getElementById("{editor_id}");
                if (!textarea || !container || typeof Quill === "undefined") {{
                    return setTimeout(initQuill, 100);
                }}
                textarea.style.display = "none";
                var quill = new Quill(container, {{
                    theme: "snow",
                    modules: {{
                        toolbar: [
                            [{{ header: [2, 3, 4, false] }}],
                            ["bold", "italic", "underline"],
                            [{{ list: "ordered" }}, {{ list: "bullet" }}],
                            [{{ align: [] }}, {{ direction: "rtl" }}],
                            ["blockquote", "link", "image"],
                            ["clean"]
                        ]
                    }}
                }});
                quill.root.setAttribute("dir", "rtl");
                quill.getModule("toolbar").addHandler("image", function() {{
                    var input = document.createElement("input");
                    input.type = "file"; input.accept = "image/jpeg,image/png,image/webp";
                    input.onchange = function() {{
                        if (!input.files.length) return;
                        var fd = new FormData(); fd.append("image", input.files[0]);
                        var token = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
                        fetch("/articles/upload-image/", {{ method: "POST", body: fd, headers: {{ "X-CSRFToken": token }}, credentials: "same-origin" }})
                            .then(function(r) {{ return r.json().then(function(j) {{ return {{ ok: r.ok, j: j }}; }}); }})
                            .then(function(res) {{
                                if (!res.ok) {{ alert(res.j.error || "آپلود تصویر انجام نشد."); return; }}
                                var range = quill.getSelection(true);
                                quill.insertEmbed(range.index, "image", res.j.url, "user");
                            }})
                            .catch(function() {{ alert("آپلود تصویر انجام نشد."); }});
                    }};
                    input.click();
                }});
                quill.root.innerHTML = textarea.value || "";
                quill.on("text-change", function() {{
                    textarea.value = quill.root.innerHTML;
                }});
                var form = textarea.closest("form");
                if (form) {{
                    form.addEventListener("submit", function() {{
                        textarea.value = quill.root.innerHTML;
                    }});
                }}
            }}
            initQuill();
        }})();
        </script>
        """
        # SAFE: textarea_html comes from Django's own Textarea.render() (its
        # `value` is auto-escaped by Django). `script`'s only interpolated
        # values are widget_id/editor_id, derived from the Django *field
        # name* ("content") — never from user-submitted data — so nothing
        # attacker-controlled ever enters this string. Known accepted
        # narrow exception: if admin form validation fails on another
        # field, Django re-renders with the submitted (not-yet-sanitized)
        # content value, and Quill's `innerHTML = textarea.value` briefly
        # renders that in the editor's own contenteditable area. This is a
        # self-XSS scoped to a staff user's own browser session on their
        # own unsaved submission — the value is always sanitized by
        # apps.core.sanitize before ever reaching Article.save() or any
        # public page, so it can never reach a non-staff visitor.
        return mark_safe(textarea_html + script)
