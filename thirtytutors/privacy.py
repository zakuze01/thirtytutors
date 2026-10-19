"""Lite does not emit provider/session diagnostics containing private content."""


def private_log(*args, **kwargs):
    # Deliberately discard upstream diagnostic messages, including raw exceptions.
    # UI shows classified errors; anonymous performance measurements are separate.
    return None
