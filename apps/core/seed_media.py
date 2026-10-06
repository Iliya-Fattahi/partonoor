from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404

def seed_media(request, path):
    base = (Path(settings.BASE_DIR) / "seed_assets").resolve()
    name = Path(path).name
    candidates = [base / "works" / name, base / name, base / "articles" / name, base / "articles" / "figures" / name]
    for file_path in candidates:
        if file_path.resolve().is_file() and base in file_path.resolve().parents:
            return FileResponse(open(file_path, "rb"))
    raise Http404
