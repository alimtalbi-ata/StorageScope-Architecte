"""Atomic local saved governance filters. No executable configuration. Author: Abdelhalim Talbi."""
import json
import os
import tempfile
from pathlib import Path

FIELDS = ('query', 'owner', 'status', 'deadline')
STATUSES = ('all', 'OPEN', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'CLOSED')
DEADLINES = ('all', 'overdue', 'due_today', 'due_soon', 'upcoming')

def validate_filters(filters):
    if type(filters) is not dict or set(filters) != set(FIELDS):
        raise ValueError('invalid view fields')
    query, owner, status, deadline = (filters[k] for k in FIELDS)
    if type(query) is not str or len(query) > 256 or '\x00' in query:
        raise ValueError('invalid query')
    if owner is not None and (type(owner) is not str or not owner.strip() or len(owner) > 128):
        raise ValueError('invalid owner')
    if status not in STATUSES or deadline not in DEADLINES:
        raise ValueError('invalid filters')
    return dict(filters)

class SavedViews:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {}
        if self.path.stat().st_size > 65536:
            raise ValueError('oversized view file')
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError('invalid view file') from exc
        if type(data) is not dict or data.get('schema') != 'storagescope.saved-views.v5.43' or type(data.get('views')) is not dict or len(data['views']) > 32:
            raise ValueError('invalid view file')
        result = {}
        for name, filters in data['views'].items():
            self._name(name)
            result[name] = validate_filters(filters)
        return result

    @staticmethod
    def _name(name):
        if type(name) is not str or not name.strip() or len(name) > 64 or any(c in name for c in '\r\n\x00'):
            raise ValueError('invalid view name')

    def save(self, name, filters):
        self._name(name)
        validated = validate_filters(filters)
        views = self.load()
        if name not in views and len(views) >= 32:
            raise ValueError('too many views')
        views[name] = validated
        self._write(views)
        return validated

    def delete(self, name):
        self._name(name)
        views = self.load()
        if name not in views:
            raise KeyError(name)
        del views[name]
        self._write(views)

    def _write(self, views):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({'schema':'storagescope.saved-views.v5.43','author':'Abdelhalim Talbi','views':views}, ensure_ascii=False, indent=2) + '\n'
        fd, tmp = tempfile.mkstemp(prefix='.ss-views-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
