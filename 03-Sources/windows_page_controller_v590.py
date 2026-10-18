"""Deterministic, testable lazy-page navigation for StorageScope. Author: Abdelhalim Talbi."""

class PageController:
    def __init__(self, names):
        self.names = tuple(names)
        if not self.names or len(set(self.names)) != len(self.names):
            raise ValueError('Invalid page registry')
        self._loaders = {}
        self._loaded = set()
        self._loading = set()
        self.current = None
        self._navigating = False

    def register(self, name, loader, cleanup=None):
        if name not in self.names or name in self._loaders or not callable(loader):
            raise ValueError('Invalid page loader')
        self._loaders[name] = (loader, cleanup)

    def navigate(self, name, render):
        """Commit only after render; prohibit nested navigation and allow safe retries."""
        if name not in self.names:
            raise ValueError('Unknown page: ' + str(name))
        if self._navigating:
            raise RuntimeError('Recursive page navigation')
        if not callable(render):
            raise TypeError('Page renderer must be callable')
        self._navigating = True
        try:
            newly_loaded = name not in self._loaded and name in self._loaders
            if newly_loaded:
                loader, cleanup = self._loaders[name]
                try:
                    loader()
                except BaseException:
                    if cleanup is not None:
                        try:
                            cleanup()
                        except Exception:
                            pass
                    raise
            try:
                render(name)
            except BaseException:
                if newly_loaded:
                    _, cleanup = self._loaders[name]
                    if cleanup is not None:
                        try:
                            cleanup()
                        except Exception:
                            pass
                raise
            if newly_loaded:
                self._loaded.add(name)
            self.current = name
            return name
        finally:
            self._navigating = False
