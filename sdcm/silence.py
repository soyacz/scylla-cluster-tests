import logging

from sdcm.sct_events import Severity
from sdcm.sct_events.system import TestFrameworkEvent


class silence:  # pylint: disable=invalid-name
    """
    A decorator and context manager that catch, log and store any exception that
        happened within wrapped function or within context clause.
    Two ways of using it:
    1) as decorator
        class someclass:
            @silence(verbose=True)
            def my_method(self):
                ...

    2) as context manager
        class someclass:
            def my_method(self):
                with silence(parent=self, name='Step #1'):
                    ...
                with silence(parent=self, name='Step #2'):
                    ...
    """
    test = None
    name: str = None

    def __init__(self, parent=None, name: str = None, verbose: bool = False):
        self.parent = parent
        self.name = name
        self.verbose = verbose
        self.log = logging.getLogger(self.__class__.__name__)

    def __enter__(self):
        pass

    def __call__(self, funct):
        def decor(*args, **kwargs):
            if self.name is None:
                name = funct.__name__
            else:
                name = self.name
            result = None
            try:
                self.log.debug("Silently running '%s'", name)
                result = funct(*args, **kwargs)
                self.log.debug("Finished '%s'. No errors were silenced.", name)
            except Exception as exc:  # pylint: disable=broad-except
                self.log.debug("Finished '%s'. %s exception was silenced.", name, str(type(exc)))
                self._store_test_result(args[0], exc, exc.__traceback__, name)
            return result

        return decor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.log.debug("Finished '%s'. No errors were silenced.", self.name)
        else:
            self.log.debug("Finished '%s'. %s exception was silenced.", self.name, str(exc_type))
            self._store_test_result(self.parent, exc_val, exc_tb, self.name)
        return True

    @staticmethod
    def _store_test_result(parent, exc_val, exc_tb, name):
        TestFrameworkEvent(
            source=parent.__class__.__name__,
            source_method=name,
            message=f'{name} (silenced) failed with:',
            exception=exc_val,
            severity=getattr(exc_val, 'severity', Severity.ERROR),
            trace=exc_tb.tb_frame,
        ).publish_or_dump(default_logger=parent.log)
