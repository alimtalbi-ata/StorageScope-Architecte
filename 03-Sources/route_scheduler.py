"""Single-worker latest-wins scheduler for graph geometry (no Tk calls)."""
from threading import Condition, Thread

class RouteCancelled(Exception):
    """A superseded routing request stopped cooperatively."""


class RouteScheduler:
    def __init__(self, compute, publish):
        self._compute, self._publish = compute, publish
        self._cv = Condition()
        self._pending = None
        self._closed = False
        self._revision = 0
        self._worker = Thread(target=self._run, name='graph-routing-worker', daemon=True)
        self._worker.start()

    def submit(self, generation, key, positions, center):
        with self._cv:
            if self._closed:
                return False
            self._revision += 1
            self._pending = (generation, key, tuple(positions), center, self._revision)
            self._cv.notify()
            return True

    def _run(self):
        while True:
            with self._cv:
                while self._pending is None and not self._closed:
                    self._cv.wait()
                if self._closed:
                    return
                generation, key, positions, center, revision = self._pending
                self._pending = None
            try:
                def cancelled():
                    with self._cv:
                        return self._closed or self._revision != revision
                value = self._compute(positions, center, cancel_check=cancelled)
                error = None
            except RouteCancelled:
                continue
            except Exception as exc:
                value, error = None, str(exc)
            with self._cv:
                if self._closed:
                    return
                # Suppress superseded results; the UI also checks generation.
                if self._pending is not None or self._revision != revision:
                    continue
            self._publish((generation, key, value, error))

    def close(self):
        with self._cv:
            self._closed = True
            self._revision += 1
            self._pending = None
            self._cv.notify_all()

    @property
    def worker(self):
        return self._worker
