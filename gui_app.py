#!/usr/bin/env python3
"""Punto de entrada de la aplicación gráfica local (PyQt6)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def _apply_light_palette(app: QApplication) -> None:
    """
    Paleta clara explícita: evita que el modo oscuro del SO deje vistas con
    fondo negro y texto ilegible al combinar estilos nativos con QSS.
    """
    p = QPalette()
    c = QColor
    p.setColor(QPalette.ColorRole.Window, c("#f4f5f7"))
    p.setColor(QPalette.ColorRole.WindowText, c("#1a1a1a"))
    p.setColor(QPalette.ColorRole.Base, c("#ffffff"))
    p.setColor(QPalette.ColorRole.AlternateBase, c("#f7f8fa"))
    p.setColor(QPalette.ColorRole.Text, c("#1a1a1a"))
    p.setColor(QPalette.ColorRole.PlaceholderText, c("#5c677a"))
    p.setColor(QPalette.ColorRole.Button, c("#eef1f6"))
    p.setColor(QPalette.ColorRole.ButtonText, c("#2d3440"))
    p.setColor(QPalette.ColorRole.Highlight, c("#1a5fb4"))
    p.setColor(QPalette.ColorRole.HighlightedText, c("#ffffff"))
    p.setColor(QPalette.ColorRole.ToolTipBase, c("#ffffff"))
    p.setColor(QPalette.ColorRole.ToolTipText, c("#1a1a1a"))
    p.setColor(QPalette.ColorRole.Link, c("#1a5fb4"))
    p.setColor(QPalette.ColorRole.LinkVisited, c("#154a90"))
    app.setPalette(p)


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("horaslaborables")
    app.setApplicationName("Horas laborables")
    app.setApplicationDisplayName("Horas laborables")

    QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))

    # Estilo Fusion + paleta clara antes del QSS (compatibilidad con modo oscuro de Windows).
    app.setStyle("Fusion")
    _apply_light_palette(app)

    qss_path = ROOT / "gui" / "resources" / "style.qss"
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
