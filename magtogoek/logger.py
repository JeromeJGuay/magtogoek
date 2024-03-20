from datetime import datetime

import click
import typing as tp

# noinspection PyUnresolvedReferences
__all__ = ["get_logger", "section", "log", "warning", "reset", "set_level", "write",
           "logbook", "w_count", "level"]


class Logger:
    """Logger object can log and print messages.

    Logger objects print log and warning messages  while building a
    logbook from them. The logbook is formatted as a string in
    `self._logbook`. Logger objects keep count of the warnings in
    `self._w_count`.

    Parameters
    ----------
    logbook : str, Default None.
        Formatted logbook.
    level : int,  Default 0.
        Level controls which messages are printed.
        [0: prints all, 1: print only warnings, 2: prints None]

    Attributes
    ----------
    logbook :
        String of the formatted logbook build from the different entries.
    w_count :
        Number of Warning.

    Methods
    -------
    section :
        Makes a new sections.

    log :
        Log and print a log message. Prints if level is greater or equal 0
    warning :
        Log and print warning message. Prints if level is greater or equal 1
    reset :
        Resets the logbook and the warning count.
    """

    def __init__(self, name: str, logbook: str = "", level: int = 0):
        self.name = name
        self._logbook = logbook
        self._w_count = 0
        self._level = level

    def __repr__(self):
        return self._logbook

    def section(self, section: str, t: bool = False):
        """Add a new section.
        Parameters:
        -----------
        section:
           Section's names.
        t:
           Log time if True.

        """
        time = "" if t is False else " " + self._timestamp()
        self._logbook += "[" + section + "]" + time + "\n"
        click.secho(section, fg="green") if self._level < 1 else None

    @property
    def level(self):
        return self._level

    @property
    def logbook(self):
        return self._logbook

    @property
    def w_count(self):
        return self._w_count

    def append_to_logbook(self, logbook: str):
        self._logbook += logbook

    def log(self, msg: tp.Union[str, tp.List[str]], t: bool = False):
        """Add a log.
        Parameters
        ----------
        msg :
           Message to log.
        t :
           Log time if True.
        """
        if isinstance(msg, list):
            [self.log(m, t=t) for m in msg]
        else:
            if self._level < 1:
                print(msg)
            msg = msg if t is False else self._timestamp() + " " + msg
            self._logbook += " " + msg + "\n"

    def warning(self, msg: str, t: bool = False):
        """Add a warning.
        Parameters
        ----------
        msg :
           Message to log.
        t :
           Log time if True.
        """
        if isinstance(msg, list):
            [self.warning(m, t=t) for m in msg]
        else:
            if self._level < 2:
                click.echo(click.style("WARNING: ", fg="yellow") + msg)
                self._w_count += 1
            msg = msg if t is False else self._timestamp() + " " + msg
            self._logbook += " WARNING: " + msg + "\n"

    def set_level(self, level: int):
        self._level = level

    def reset(self):
        """Reset w_count and logbook."""
        self._logbook = ""
        self._w_count = 0

    @staticmethod
    def _timestamp():
        """Make a time stamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def write(self, filename):
        with open(filename, "w") as log_file:
            log_file.write(self._logbook)
            print(f"log file made -> {filename}")


class Manager:
    current_logger: str


_manager = Manager()
_root_logger = 'root'
_manager.current_logger = _root_logger
_loggers = {_root_logger: Logger(_root_logger, level=0)}


def get_logger(logger_name=_root_logger):
    if logger_name not in _loggers:
        _loggers[logger_name] = Logger(logger_name, level=0)
    _manager.current_logger = logger_name


def append_to_logbook(logbook: str):
    _loggers[_manager.current_logger].append_to_logbook(logbook)

def section(name: str, t=False):
    _loggers[_manager.current_logger].section(name, t)


def log(msg: str, t=False):
    _loggers[_manager.current_logger].log(msg, t)


def warning(msg: str, t=False):
    _loggers[_manager.current_logger].warning(msg, t)


def reset():
    _loggers[_manager.current_logger].reset()


def set_level(level: int):
    _loggers[_manager.current_logger].set_level(level)


def write(filename: str):
    _loggers[_manager.current_logger].write(filename)

#
# logbook = None
# w_count = None
# level = None


def __getattr__(name):
    if name == 'logbook':
        return _loggers[_manager.current_logger].logbook
    if name == "w_count":
        return _loggers[_manager.current_logger].w_count
    if name == "level":
        return _loggers[_manager.current_logger].level

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
