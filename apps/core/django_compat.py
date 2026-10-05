"""
Compatibility shim for a known Django/Python version-mismatch bug reported
on the client's environment (Python 3.14.6 + Django 5.0.14):

    AttributeError: 'super' object has no attribute 'dicts' and no
    __dict__ for setting new attributes

...raised inside django/template/context.py, surfacing when Django's own
built-in {% submit_row %} admin template tag renders on Add/Edit pages.

ROOT CAUSE (best-effort diagnosis — could not be executed/confirmed in
this sandbox, which has no PyPI access to install this exact
Django/Python combination; see README "Troubleshooting" for how to verify
this independently): Django 5.0 is only officially tested against Python
3.10-3.12. Django's `BaseContext.__copy__` (django/template/context.py)
relies on a `copy(super())` pattern to duplicate the context object. The
error text literally names the type involved as `'super' object` — i.e.
some code path is calling `copy.copy()` on an actual `super` proxy rather
than on a real instance, and CPython's `copy` module dispatch behavior
for that specific pattern appears to have changed between the Python
version Django 5.0 was built against and 3.14. This is Django's own
internal code — nothing in apps/*/admin.py, apps/core/admin_site.py, or
any template in this project touches template Context internals (this
was verified by grep across the whole repo before writing this patch).

WHAT THIS PATCH DOES: replaces BaseContext.__copy__ with a version-
independent reimplementation that is semantically identical to what
Django's own method is documented to do (duplicate the object, then
give the duplicate an independent copy of the `dicts` list) — it does
not change behavior on Python versions where the original works fine,
it only avoids the specific `copy(super())` call that breaks. This is a
temporary bridge, not a substitute for fixing the actual version
mismatch: the two real fixes remain (a) run this project on a Python
version Django 5.0.x officially supports (3.10-3.12), which needs no
code change at all, or (b) upgrade Django to a release that has fixed
this internally for newer Python. Both were already presented with a
risk comparison; this patch exists so Admin is usable *right now*
without forcing that decision, and can be deleted the moment either
real fix is in place — nothing else in the codebase depends on it.

This module makes NO database, migration, or model changes.
"""
import logging

logger = logging.getLogger("apps.core.django_compat")


def apply_context_copy_shim():
    try:
        from django.template.context import BaseContext
    except ImportError:
        return  # Django not installed / not the expected module layout — no-op, never crash startup

    def _safe_copy(self):
        # IMPORTANT: this must NOT call copy.copy(self) — doing so was my
        # first attempt at this shim, and it re-dispatches back to this
        # very __copy__ method (since copy.copy() looks up __copy__ and
        # calls it), causing infinite recursion. Confirmed by actually
        # running it: it raised RecursionError immediately. Building the
        # duplicate directly via __new__ + __dict__ avoids that entirely.
        cls = self.__class__
        duplicate = cls.__new__(cls)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    # Only patch if the original is actually present — if a future Django
    # release fixes this upstream and removes/renames __copy__, this
    # becomes a silent no-op rather than an error.
    if hasattr(BaseContext, "__copy__"):
        BaseContext.__copy__ = _safe_copy
        logger.info(
            "Applied BaseContext.__copy__ compatibility shim "
            "(see apps/core/django_compat.py for why this exists)."
        )
