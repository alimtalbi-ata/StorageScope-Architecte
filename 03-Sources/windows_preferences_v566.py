"""Validated, atomic local UI preferences. Author: Abdelhalim Talbi."""
import json
import os
import tempfile
from pathlib import Path

DEFAULTS = {'theme': 'system', 'geometry': '1200x760', 'last_page': 'Accueil'}
PAGES = ('Accueil', 'Gouvernance', 'Campagnes', 'Diagnostic', 'Maintenance')

def validate_preferences(data):
    if not isinstance(data, dict):
        raise ValueError('preferences must be an object')
    result = dict(DEFAULTS)
    theme = data.get('theme', result['theme'])
    if theme not in ('system', 'light'):
        raise ValueError('invalid theme')
    geometry = data.get('geometry', result['geometry'])
    if not isinstance(geometry, str):
        raise ValueError('invalid geometry')
    try:
        width, height = map(int, geometry.split('x'))
    except (ValueError, AttributeError) as exc:
        raise ValueError('invalid geometry') from exc
    if not (920 <= width <= 3840 and 580 <= height <= 2160):
        raise ValueError('geometry outside supported range')
    page = data.get('last_page', result['last_page'])
    if page not in PAGES:
        raise ValueError('invalid page')
    result.update(theme=theme, geometry=f'{width}x{height}', last_page=page)
    return result

def load_preferences(path):
    path = Path(path)
    if not path.exists():
        return dict(DEFAULTS)
    return validate_preferences(json.loads(path.read_text(encoding='utf-8')))

def save_preferences(path, data):
    clean = validate_preferences(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.preferences-', suffix='.tmp', delete=False) as f:
            name = f.name
            json.dump(clean, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return clean
