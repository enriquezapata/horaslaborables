#!/usr/bin/env python3
"""Punto de entrada de la aplicación gráfica local (PyQt6)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("horaslaborables")
    app.setApplicationName("Horas laborables")
    app.setApplicationDisplayName("Horas laborables")

    QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))

    qss_path = ROOT / "gui" / "resources" / "style.qss"
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
