from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QAction, QActionGroup, QCloseEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from calcular_horas_laborables import (
    YAML_WEEKDAY_KEYS,
    calcular_horas_laborables,
    config_from_raw,
)


WEEKDAY_UI_LABELS: List[str] = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]


def qdate_to_date(qd: QDate) -> date:
    if not qd.isValid():
        raise ValueError("Fecha no válida en el control.")
    return date(qd.year(), qd.month(), qd.day())


def date_to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def format_iso(d: date) -> str:
    return d.isoformat()


class GuiValidationError(Exception):
    """Error de validación de formulario (mensaje apto para mostrar al usuario)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DatePickerDialog(QDialog):
    """Diálogo con un QDateEdit (calendario) para elegir una fecha."""

    def __init__(self, parent: QWidget, title: str, initial: date) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._date_edit.setMinimumDate(QDate(2000, 1, 1))
        self._date_edit.setMaximumDate(QDate(2100, 12, 31))
        self._date_edit.setDate(date_to_qdate(initial))

        form = QFormLayout()
        form.addRow("Fecha:", self._date_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def selected_date(self) -> date:
        return qdate_to_date(self._date_edit.date())


class RangeDialog(QDialog):
    """Rango inicio–fin con validación al aceptar."""

    def __init__(self, parent: QWidget, title: str, start: date, end: date) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._start = QDateEdit()
        self._end = QDateEdit()
        for d in (self._start, self._end):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
            d.setMinimumDate(QDate(2000, 1, 1))
            d.setMaximumDate(QDate(2100, 12, 31))
        self._start.setDate(date_to_qdate(start))
        self._end.setDate(date_to_qdate(end))

        form = QFormLayout()
        form.addRow("Inicio:", self._start)
        form.addRow("Fin:", self._end)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def _on_accept(self) -> None:
        try:
            a = qdate_to_date(self._start.date())
            b = qdate_to_date(self._end.date())
        except ValueError:
            QMessageBox.warning(self, "Fechas inválidas", "Revisa las fechas del rango.")
            return
        if b < a:
            QMessageBox.warning(
                self,
                "Rango inválido",
                "La fecha de fin debe ser igual o posterior a la de inicio.",
            )
            return
        self.accept()

    def range(self) -> Tuple[date, date]:
        return qdate_to_date(self._start.date()), qdate_to_date(self._end.date())


class MainWindow(QMainWindow):
    """Ventana principal: edición de configuración y resultados."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Horas laborables")
        self.resize(980, 720)
        self._last_config_dir: Path = Path.cwd()
        self._current_file: Optional[Path] = None

        self._year_spin = QSpinBox()
        self._year_spin.setRange(2000, 2100)
        self._year_spin.setSuffix(" ")
        self._year_spin.setAccessibleName("Año a calcular")

        self._ji_inicio = self._make_date_edit()
        self._ji_fin = self._make_date_edit()

        self._festivos_list = QListWidget()
        self._festivos_list.setAlternatingRowColors(True)
        self._festivos_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._rangos_table = QTableWidget(0, 2)
        self._rangos_table.setHorizontalHeaderLabels(["Inicio", "Fin"])
        self._rangos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._rangos_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._rangos_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._vac_sueltos_list = QListWidget()
        self._vac_sueltos_list.setAlternatingRowColors(True)
        self._vac_sueltos_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._horas_normal: Dict[str, QDoubleSpinBox] = {}
        self._horas_int: Dict[str, QDoubleSpinBox] = {}
        for key in YAML_WEEKDAY_KEYS:
            self._horas_normal[key] = self._make_hours_spin()
            self._horas_int[key] = self._make_hours_spin()

        self._resumen_label = QLabel()
        self._resumen_label.setObjectName("hintLabel")
        self._resumen_label.setWordWrap(True)
        self._resumen_label.setMinimumHeight(80)

        self._detalle_table = QTableWidget(0, 4)
        self._detalle_table.setHorizontalHeaderLabels(
            ["Fecha", "Día", "Horas", "Jornada"]
        )
        self._detalle_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._detalle_table.setAlternatingRowColors(True)
        self._detalle_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._setup_menu_toolbar()
        self._build_tabs()
        self._connect_signals()

        y = date.today().year
        self._year_spin.setValue(y)
        self._apply_default_config_for_year(y)
        self.statusBar().showMessage("Listo.")

    def _make_date_edit(self) -> QDateEdit:
        d = QDateEdit()
        d.setCalendarPopup(True)
        d.setDisplayFormat("yyyy-MM-dd")
        d.setMinimumDate(QDate(2000, 1, 1))
        d.setMaximumDate(QDate(2100, 12, 31))
        return d

    def _make_hours_spin(self) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0.0, 24.0)
        s.setSingleStep(0.25)
        s.setDecimals(2)
        s.setSuffix(" h")
        s.setLocale(self.locale())
        return s

    def _setup_menu_toolbar(self) -> None:
        bar = self.menuBar()
        menu_archivo = QMenu("Archivo", self)

        act_abrir = QAction("Abrir configuración…", self)
        act_abrir.setShortcut("Ctrl+O")
        act_abrir.triggered.connect(self._action_open_yaml)
        menu_archivo.addAction(act_abrir)

        act_guardar = QAction("Guardar configuración…", self)
        act_guardar.setShortcut("Ctrl+S")
        act_guardar.triggered.connect(self._action_save_yaml_as)
        menu_archivo.addAction(act_guardar)

        menu_archivo.addSeparator()

        act_salir = QAction("Salir", self)
        act_salir.setShortcut("Ctrl+Q")
        act_salir.triggered.connect(self.close)
        menu_archivo.addAction(act_salir)

        bar.addMenu(menu_archivo)

        menu_calc = QMenu("Cálculo", self)
        act_calc = QAction("Calcular horas", self)
        act_calc.setShortcut("F5")
        act_calc.triggered.connect(self._action_calculate)
        menu_calc.addAction(act_calc)
        bar.addMenu(menu_calc)

        ayuda = QMenu("Ayuda", self)
        act_acerca = QAction("Acerca de", self)
        act_acerca.triggered.connect(self._action_about)
        ayuda.addAction(act_acerca)
        bar.addMenu(ayuda)

        tb = QToolBar("Principal")
        tb.setMovable(False)
        tb.setIconSize(self.style().pixelMetric(self.style().PixelMetric.PM_SmallIconSize))
        tb.addAction(act_calc)
        tb.addSeparator()
        tb.addAction(act_abrir)
        tb.addAction(act_guardar)
        self.addToolBar(tb)

    def _build_tabs(self) -> None:
        tabs = QTabWidget()

        tabs.addTab(self._build_tab_general(), "General")
        tabs.addTab(self._build_tab_festivos(), "Festivos")
        tabs.addTab(self._build_tab_vacaciones(), "Vacaciones")
        tabs.addTab(self._build_tab_horas(), "Horas por día")
        tabs.addTab(self._build_tab_resultados(), "Resultados")

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(tabs)
        self.setCentralWidget(central)

    def _build_tab_general(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        gb_year = QGroupBox("Año a calcular")
        fy = QFormLayout(gb_year)
        fy.addRow("Año natural:", self._year_spin)
        hint = QLabel(
            "Se contabilizan todos los días hábiles del 1 de enero al 31 de diciembre de ese año."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        fy.addRow(hint)

        gb_ji = QGroupBox("Jornada intensiva")
        fj = QFormLayout(gb_ji)
        fj.addRow("Inicio del periodo:", self._ji_inicio)
        fj.addRow("Fin del periodo:", self._ji_fin)
        hji = QLabel(
            "Dentro de estas fechas (inclusive) se aplican las horas de «Jornada intensiva». "
            "Fuera de ellas, las de «Semana normal»."
        )
        hji.setObjectName("hintLabel")
        hji.setWordWrap(True)
        fj.addRow(hji)

        btn_calc = QPushButton("Calcular horas laborables")
        btn_calc.setDefault(True)
        btn_calc.clicked.connect(self._action_calculate)

        lay.addWidget(gb_year)
        lay.addWidget(gb_ji)
        lay.addStretch()
        lay.addWidget(btn_calc)
        return w

    def _build_tab_festivos(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        hint = QLabel(
            "Festivos laborales del calendario oficial (u otros días no trabajados): "
            "se excluyen aunque sea lunes a viernes."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(self._festivos_list, stretch=1)

        row = QHBoxLayout()
        b_add = QPushButton("Añadir festivo")
        b_add.clicked.connect(self._festivos_add)
        b_rem = QPushButton("Quitar seleccionado")
        b_rem.setObjectName("dangerButton")
        b_rem.clicked.connect(self._festivos_remove)
        row.addWidget(b_add)
        row.addWidget(b_rem)
        row.addStretch()
        lay.addLayout(row)
        return w

    def _build_tab_vacaciones(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        gb_r = QGroupBox("Rangos de vacaciones (consecutivos)")
        lr = QVBoxLayout(gb_r)
        hr = QLabel(
            "Cada rango incluye el primer y el último día indicado. Puedes definir varios "
            "tramos no consecutivos."
        )
        hr.setObjectName("hintLabel")
        hr.setWordWrap(True)
        lr.addWidget(hr)
        lr.addWidget(self._rangos_table, stretch=1)
        rr = QHBoxLayout()
        b_ar = QPushButton("Añadir rango")
        b_ar.clicked.connect(self._rangos_add)
        b_rr = QPushButton("Quitar rango seleccionado")
        b_rr.setObjectName("dangerButton")
        b_rr.clicked.connect(self._rangos_remove)
        rr.addWidget(b_ar)
        rr.addWidget(b_rr)
        rr.addStretch()
        lr.addLayout(rr)

        gb_s = QGroupBox("Días sueltos de vacaciones")
        ls = QVBoxLayout(gb_s)
        hs = QLabel("Días adicionales que no pertenecen a ningún rango anterior.")
        hs.setObjectName("hintLabel")
        hs.setWordWrap(True)
        ls.addWidget(hs)
        ls.addWidget(self._vac_sueltos_list, stretch=1)
        rs = QHBoxLayout()
        b_as = QPushButton("Añadir día")
        b_as.clicked.connect(self._vac_sueltos_add)
        b_rs = QPushButton("Quitar seleccionado")
        b_rs.setObjectName("dangerButton")
        b_rs.clicked.connect(self._vac_sueltos_remove)
        rs.addWidget(b_as)
        rs.addWidget(b_rs)
        rs.addStretch()
        ls.addLayout(rs)

        lay.addWidget(gb_r, stretch=2)
        lay.addWidget(gb_s, stretch=1)
        return w

    def _build_tab_horas(self) -> QWidget:
        wrap = QScrollArea()
        wrap.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.addWidget(QLabel(""), 0, 0)
        grid.addWidget(QLabel("<b>Semana normal</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Jornada intensiva</b>"), 0, 2)

        for i, (label, key) in enumerate(zip(WEEKDAY_UI_LABELS, YAML_WEEKDAY_KEYS), start=1):
            grid.addWidget(QLabel(label), i, 0)
            grid.addWidget(self._horas_normal[key], i, 1)
            grid.addWidget(self._horas_int[key], i, 2)

        wrap.setWidget(inner)
        w = QWidget()
        lay = QVBoxLayout(w)
        lab = QLabel(
            "Horas efectivas por día entre semana (lunes–viernes). Sábado y domingo suelen ser 0. "
            "Los límites del periodo intensivo están en la pestaña «General»."
        )
        lab.setObjectName("hintLabel")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        lay.addWidget(wrap)
        return w

    def _build_tab_resultados(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        recalc = QPushButton("Calcular horas laborables")
        recalc.clicked.connect(self._action_calculate)

        lay.addWidget(recalc)
        lay.addWidget(QLabel("<b>Resumen</b>"))
        lay.addWidget(self._resumen_label)
        lay.addWidget(QLabel("<b>Detalle por día laborable</b>"))
        lay.addWidget(self._detalle_table, stretch=1)
        return w

    def _connect_signals(self) -> None:
        self._year_spin.valueChanged.connect(self._on_year_changed)

    def _on_year_changed(self, value: int) -> None:
        self.statusBar().showMessage(f"Año de cálculo: {value}", 2000)

    def _apply_default_config_for_year(self, year: int) -> None:
        """Configuración inicial razonable (similar al ejemplo 2026)."""
        self._ji_inicio.setDate(QDate(year, 7, 1))
        self._ji_fin.setDate(QDate(year, 9, 30))

        defaults_normal = {
            "lunes": 9.0,
            "martes": 9.0,
            "miercoles": 9.0,
            "jueves": 9.0,
            "viernes": 6.0,
            "sabado": 0.0,
            "domingo": 0.0,
        }
        defaults_int = {
            "lunes": 8.0,
            "martes": 8.0,
            "miercoles": 8.0,
            "jueves": 8.0,
            "viernes": 8.0,
            "sabado": 0.0,
            "domingo": 0.0,
        }
        for k in YAML_WEEKDAY_KEYS:
            self._horas_normal[k].setValue(defaults_normal[k])
            self._horas_int[k].setValue(defaults_int[k])

        self._festivos_list.clear()
        self._rangos_table.setRowCount(0)
        self._vac_sueltos_list.clear()

    def _list_iso_dates_from_listwidget(self, lw: QListWidget) -> List[str]:
        out: List[str] = []
        for i in range(lw.count()):
            it = lw.item(i)
            iso = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(iso, str):
                out.append(iso)
        return sorted(out)

    def _set_listwidget_dates(self, lw: QListWidget, isos: List[str]) -> None:
        lw.clear()
        for iso in sorted(set(isos)):
            try:
                d = parse_iso_date(iso)
            except ValueError:
                continue
            item = QListWidgetItem(f"{iso} ({WEEKDAY_UI_LABELS[d.weekday()]})")
            item.setData(Qt.ItemDataRole.UserRole, iso)
            lw.addItem(item)

    def _collect_raw_config(self) -> Dict[str, Any]:
        """Arma el dict tipo YAML y valida coherencia antes del motor de cálculo."""
        year = int(self._year_spin.value())
        if year < 2000 or year > 2100:
            raise GuiValidationError("El año debe estar entre 2000 y 2100.")

        try:
            ji_a = qdate_to_date(self._ji_inicio.date())
            ji_b = qdate_to_date(self._ji_fin.date())
        except ValueError as exc:
            raise GuiValidationError(str(exc)) from exc

        if ji_b < ji_a:
            raise GuiValidationError(
                "En la jornada intensiva, la fecha de fin no puede ser anterior a la de inicio."
            )

        rangos: List[Dict[str, str]] = []
        for row in range(self._rangos_table.rowCount()):
            it0 = self._rangos_table.item(row, 0)
            it1 = self._rangos_table.item(row, 1)
            if it0 is None or it1 is None:
                raise GuiValidationError("Hay filas de rangos de vacaciones incompletas.")
            a_s = it0.data(Qt.ItemDataRole.UserRole)
            b_s = it1.data(Qt.ItemDataRole.UserRole)
            if not isinstance(a_s, str) or not isinstance(b_s, str):
                raise GuiValidationError("Datos de rango de vacaciones corruptos; prueba a quitar y volver a añadir.")
            try:
                ra = parse_iso_date(a_s)
                rb = parse_iso_date(b_s)
            except ValueError:
                raise GuiValidationError("Hay fechas de vacaciones con formato inválido.") from None
            if rb < ra:
                raise GuiValidationError(
                    f"En el rango del {a_s} al {b_s}, la fecha de fin no puede ser anterior a la de inicio."
                )
            rangos.append({"inicio": a_s, "fin": b_s})

        festivos = self._list_iso_dates_from_listwidget(self._festivos_list)
        for iso in festivos:
            try:
                parse_iso_date(iso)
            except ValueError:
                raise GuiValidationError(f"Festivo con fecha inválida: {iso!r}.")

        sueltos = self._list_iso_dates_from_listwidget(self._vac_sueltos_list)
        for iso in sueltos:
            try:
                parse_iso_date(iso)
            except ValueError:
                raise GuiValidationError(f"Día de vacaciones inválido: {iso!r}.")

        semana_normal: Dict[str, float] = {}
        semana_int: Dict[str, float] = {}
        for key in YAML_WEEKDAY_KEYS:
            hn = float(self._horas_normal[key].value())
            hi = float(self._horas_int[key].value())
            if hn < 0 or hn > 24 or hi < 0 or hi > 24:
                raise GuiValidationError(f"Las horas para {key} deben estar entre 0 y 24.")
            semana_normal[key] = hn
            semana_int[key] = hi

        return {
            "jornada_intensiva": {
                "inicio": ji_a.isoformat(),
                "fin": ji_b.isoformat(),
            },
            "vacaciones": {
                "rangos": rangos,
                "dias_individuales": sueltos,
            },
            "festivos": festivos,
            "horas_laborables": {
                "semana_normal": semana_normal,
                "jornada_intensiva": semana_int,
            },
        }

    def _apply_raw_config(self, raw: Dict[str, Any]) -> None:
        """Rellena formularios desde dict (p. ej. tras abrir YAML)."""
        ji = raw.get("jornada_intensiva") or {}
        if ji.get("inicio") and ji.get("fin"):
            try:
                di = parse_iso_date(str(ji["inicio"]))
                df = parse_iso_date(str(ji["fin"]))
                self._ji_inicio.setDate(date_to_qdate(di))
                self._ji_fin.setDate(date_to_qdate(df))
            except ValueError:
                pass

        halb = raw.get("horas_laborables") or {}
        sn = halb.get("semana_normal") or {}
        si = halb.get("jornada_intensiva") or {}
        for key in YAML_WEEKDAY_KEYS:
            if key in sn:
                self._horas_normal[key].setValue(float(sn[key]))
            if key in si:
                self._horas_int[key].setValue(float(si[key]))

        fest = raw.get("festivos") or []
        if isinstance(fest, list):
            isos_f: List[str] = []
            for x in fest:
                try:
                    isos_f.append(parse_iso_date(str(x)).isoformat())
                except ValueError:
                    continue
            self._set_listwidget_dates(self._festivos_list, isos_f)

        vac = raw.get("vacaciones") or {}
        self._rangos_table.setRowCount(0)
        for r in vac.get("rangos") or []:
            try:
                a = parse_iso_date(str(r["inicio"]))
                b = parse_iso_date(str(r["fin"]))
            except (KeyError, TypeError, ValueError):
                continue
            if b < a:
                continue
            row = self._rangos_table.rowCount()
            self._rangos_table.insertRow(row)
            self._rangos_table_set_row(row, a, b)

        sueltos_l = vac.get("dias_individuales") or []
        if isinstance(sueltos_l, list):
            isos_s: List[str] = []
            for x in sueltos_l:
                try:
                    isos_s.append(parse_iso_date(str(x)).isoformat())
                except ValueError:
                    continue
            self._set_listwidget_dates(self._vac_sueltos_list, isos_s)

    def _rangos_table_set_row(self, row: int, inicio: date, fin: date) -> None:
        ia, ib = format_iso(inicio), format_iso(fin)
        t0 = QTableWidgetItem(f"{ia} ({WEEKDAY_UI_LABELS[inicio.weekday()]})")
        t0.setData(Qt.ItemDataRole.UserRole, ia)
        t1 = QTableWidgetItem(f"{ib} ({WEEKDAY_UI_LABELS[fin.weekday()]})")
        t1.setData(Qt.ItemDataRole.UserRole, ib)
        self._rangos_table.setItem(row, 0, t0)
        self._rangos_table.setItem(row, 1, t1)

    def _sort_rangos_table(self) -> None:
        rows: List[Tuple[date, date]] = []
        for r in range(self._rangos_table.rowCount()):
            it0 = self._rangos_table.item(r, 0)
            it1 = self._rangos_table.item(r, 1)
            if not it0 or not it1:
                continue
            try:
                a = parse_iso_date(str(it0.data(Qt.ItemDataRole.UserRole)))
                b = parse_iso_date(str(it1.data(Qt.ItemDataRole.UserRole)))
            except (TypeError, ValueError):
                continue
            rows.append((a, b))
        rows.sort(key=lambda x: x[0])
        self._rangos_table.setRowCount(0)
        for a, b in rows:
            n = self._rangos_table.rowCount()
            self._rangos_table.insertRow(n)
            self._rangos_table_set_row(n, a, b)

    # --- Acciones de listas ---

    def _festivos_add(self) -> None:
        y = self._year_spin.value()
        dlg = DatePickerDialog(self, "Añadir festivo", date(y, 1, 1))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.selected_date()
        iso = format_iso(d)
        existing = set(self._list_iso_dates_from_listwidget(self._festivos_list))
        if iso in existing:
            QMessageBox.information(self, "Duplicado", "Esa fecha ya está en la lista de festivos.")
            return
        self._set_listwidget_dates(self._festivos_list, list(existing | {iso}))

    def _festivos_remove(self) -> None:
        row = self._festivos_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Selecciona un festivo para quitarlo.")
            return
        self._festivos_list.takeItem(row)

    def _rangos_add(self) -> None:
        y = self._year_spin.value()
        dlg = RangeDialog(self, "Añadir rango de vacaciones", date(y, 8, 1), date(y, 8, 15))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        a, b = dlg.range()
        n = self._rangos_table.rowCount()
        self._rangos_table.insertRow(n)
        self._rangos_table_set_row(n, a, b)
        self._sort_rangos_table()

    def _rangos_remove(self) -> None:
        row = self._rangos_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Selecciona un rango para quitarlo.")
            return
        self._rangos_table.removeRow(row)

    def _vac_sueltos_add(self) -> None:
        y = self._year_spin.value()
        dlg = DatePickerDialog(self, "Añadir día suelto de vacaciones", date(y, 1, 2))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.selected_date()
        iso = format_iso(d)
        existing = set(self._list_iso_dates_from_listwidget(self._vac_sueltos_list))
        if iso in existing:
            QMessageBox.information(self, "Duplicado", "Ese día ya está en la lista.")
            return
        self._set_listwidget_dates(self._vac_sueltos_list, list(existing | {iso}))

    def _vac_sueltos_remove(self) -> None:
        row = self._vac_sueltos_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selección", "Selecciona un día para quitarlo.")
            return
        self._vac_sueltos_list.takeItem(row)

    # --- Archivo / cálculo ---

    def _action_open_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir configuración YAML",
            str(self._last_config_dir),
            "YAML (*.yml *.yaml);;Todos los archivos (*)",
        )
        if not path:
            return
        p = Path(path)
        self._last_config_dir = p.parent
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            QMessageBox.critical(self, "YAML inválido", str(exc))
            return
        except OSError as exc:
            QMessageBox.critical(self, "Error de lectura", str(exc))
            return
        if raw is not None and not isinstance(raw, dict):
            QMessageBox.warning(
                self,
                "Formato incorrecto",
                "El archivo debe ser un único objeto YAML en la raíz.",
            )
            return
        self._apply_raw_config(raw or {})
        self._current_file = p
        self.statusBar().showMessage(f"Cargado: {p}", 4000)

    def _action_save_yaml_as(self) -> None:
        try:
            raw = self._collect_raw_config()
        except GuiValidationError as exc:
            QMessageBox.warning(self, "Validación", exc.message)
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar configuración YAML",
            str(self._last_config_dir / "config_horas_laborables.yml"),
            "YAML (*.yml *.yaml)",
        )
        if not path:
            return
        p = Path(path)
        self._last_config_dir = p.parent
        text = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False)
        try:
            p.write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Error al guardar", str(exc))
            return
        self._current_file = p
        self.statusBar().showMessage(f"Guardado: {p}", 4000)

    def _soft_check_year_vs_jornada(self, year: int, ji_a: date, ji_b: date) -> None:
        """Aviso informativo si el periodo intensivo casi no toca el año calculado."""
        last = date(year, 12, 31)
        first = date(year, 1, 1)
        overlaps = ji_b >= first and ji_a <= last
        if overlaps:
            return
        QMessageBox.warning(
            self,
            "Jornada intensiva y año de cálculo",
            "El periodo de jornada intensiva no se solapa con el año seleccionado. "
            "La jornada «normal» se aplicará a todo el año para el propósito del cálculo.",
        )

    def _action_calculate(self) -> None:
        try:
            raw = self._collect_raw_config()
        except GuiValidationError as exc:
            QMessageBox.warning(self, "Validación", exc.message)
            self.statusBar().showMessage("Corrija los datos antes de calcular.")
            return

        year = int(self._year_spin.value())
        ji_a = parse_iso_date(str(raw["jornada_intensiva"]["inicio"]))
        ji_b = parse_iso_date(str(raw["jornada_intensiva"]["fin"]))
        self._soft_check_year_vs_jornada(year, ji_a, ji_b)

        try:
            cfg = config_from_raw(raw)
        except ValueError as exc:
            QMessageBox.critical(self, "Configuración", str(exc))
            return

        resultado = calcular_horas_laborables(year, cfg)

        self._resumen_label.setText(
            f"<b>Año:</b> {resultado['anio']}<br>"
            f"<b>Horas laborables totales:</b> {resultado['horas_totales']:.1f} h<br>"
            f"<b>Días laborables computados:</b> {resultado['dias_laborables_computados']}<br>"
            f"<b>Días excluidos por festivo:</b> {resultado['dias_descartados_por_festivo']}<br>"
            f"<b>Días excluidos por vacaciones:</b> {resultado['dias_descartados_por_vacaciones']}<br>"
            f"<b>Fines de semana (sáb. y dom.):</b> {resultado['dias_fin_de_semana']}"
        )

        det = resultado["detalle"]
        self._detalle_table.setRowCount(len(det))
        for row, rowd in enumerate(det):
            ds = rowd["fecha"]
            wd = int(rowd["dia_semana"])
            h = float(rowd["horas"])
            tipo = rowd["tipo_jornada"]
            d = parse_iso_date(ds)
            day_name = WEEKDAY_UI_LABELS[wd]
            self._detalle_table.setItem(row, 0, QTableWidgetItem(ds))
            self._detalle_table.setItem(row, 1, QTableWidgetItem(day_name))
            self._detalle_table.setItem(row, 2, QTableWidgetItem(f"{h:g} h"))
            self._detalle_table.setItem(
                row, 3, QTableWidgetItem("Intensiva" if tipo == "intensiva" else "Normal")
            )

        self.statusBar().showMessage(
            f"Cálculo completado: {resultado['horas_totales']:.1f} h en {year}.", 6000
        )

    def _action_about(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de",
            "<h3>Horas laborables</h3>"
            "<p>Herramienta local para estimar horas laborables anuales según calendario, "
            "festivos, vacaciones y jornada por días.</p>"
            "<p>No sustituye asesoramiento laboral ni legal.</p>",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - UI
        event.accept()
