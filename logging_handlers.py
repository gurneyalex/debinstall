import logging

CONSOLE = logging.StreamHandler()
CONSOLE.setLevel(logging.DEBUG)
CONSOLE.setFormatter(logging.Formatter('[%(levelname)-8s] %(name)-10s: %(message)s'))

