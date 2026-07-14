"""Colored console messages and interactive prompts."""

import sys

_USE_COLOR = sys.stdout.isatty()


def _color(code: str) -> str:
    return f"\033[{code}m" if _USE_COLOR else ""


COLOR_RED = _color("31")
COLOR_GREEN = _color("32")
COLOR_YELLOW = _color("33")
COLOR_BLUE = _color("34")
COLOR_MAGENTA = _color("35")
COLOR_CYAN = _color("36")
COLOR_WHITE = _color("37")
COLOR_RESET = _color("0")


def message(color: str, tag: str, text: str) -> None:
    print(f"{color}[{tag}]:{COLOR_RESET} {text}")


def question(text: str) -> None:
    message(COLOR_MAGENTA, "QUESTION", text)


def info(text: str) -> None:
    message(COLOR_BLUE, "INFO", text)


def warning(text: str) -> None:
    message(COLOR_YELLOW, "WARNING", text)


def success(text: str) -> None:
    message(COLOR_GREEN, "SUCCESS", text)


def error(text: str) -> None:
    message(COLOR_RED, "ERROR", text)


def ask(prompt: str) -> str:
    question(prompt)
    return input().strip()


def confirm(prompt: str) -> bool:
    return ask(f"{prompt}(y/N)") == "y"


def header() -> None:
    print(
        f"\n{COLOR_YELLOW}The\n"
        "LINUX IMAGE MANAGER\n"
        "is an administration tool designed from and for Kevin Veen-Birkenbach.\n\n"
        "Licensed under GNU GENERAL PUBLIC LICENSE Version 3"
        f"{COLOR_RESET}\n"
    )
