#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

import yaml


WEEKDAY_MAP = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}

# Claves YAML canónicas (orden de interfaz / exportación)
YAML_WEEKDAY_KEYS: Tuple[str, ...] = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


@dataclass
class Config:
    vacaciones: Set[date]
    festivos: Set[date]
    jornada_intensiva_inicio: date
    jornada_intensiva_fin: date
    horas_semana_normal: Dict[int, float]
    horas_jornada_intensiva: Dict[int, float]


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Fecha inválida '{value}'. Usa el formato YYYY-MM-DD.") from exc


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def expand_vacaciones(vacaciones_cfg: dict) -> Set[date]:
    """
    Soporta dos formas:
    1) rango: {inicio: '2026-08-03', fin: '2026-09-01'}
    2) dias_individuales: ['2026-08-03', '2026-08-04']
    """
    vacaciones: Set[date] = set()

    for rango in vacaciones_cfg.get("rangos", []):
        inicio = parse_date(rango["inicio"])
        fin = parse_date(rango["fin"])
        if fin < inicio:
            raise ValueError(f"Rango de vacaciones inválido: {inicio} > {fin}")
        vacaciones.update(daterange(inicio, fin))

    for dia in vacaciones_cfg.get("dias_individuales", []):
        vacaciones.add(parse_date(dia))

    return vacaciones


def normalize_hours(hours_cfg: dict) -> Dict[int, float]:
    result = {i: 0.0 for i in range(7)}
    for day_name, hours in hours_cfg.items():
        day_key = day_name.strip().lower()
        if day_key not in WEEKDAY_MAP:
            raise ValueError(f"Día de la semana no reconocido en configuración: '{day_name}'")
        result[WEEKDAY_MAP[day_key]] = float(hours)
    return result


def config_from_raw(raw: Optional[Dict[str, Any]]) -> Config:
    """
    Construye Config a partir de un dict con la misma forma que el YAML.
    Lanza ValueError si faltan campos obligatorios o los datos son incoherentes.
    """
    raw = raw or {}

    vacaciones = expand_vacaciones(raw.get("vacaciones") or {})
    festivos_raw = raw.get("festivos") or []
    if not isinstance(festivos_raw, list):
        raise ValueError("El campo 'festivos' debe ser una lista de fechas.")
    festivos = {parse_date(d) for d in festivos_raw}

    ji = raw.get("jornada_intensiva") or {}
    try:
        inicio_s = ji["inicio"]
        fin_s = ji["fin"]
    except KeyError as exc:
        raise ValueError("La jornada intensiva requiere 'inicio' y 'fin'.") from exc

    ji_inicio = parse_date(inicio_s)
    ji_fin = parse_date(fin_s)
    if ji_fin < ji_inicio:
        raise ValueError("La fecha fin de la jornada intensiva no puede ser anterior a la de inicio.")

    horas_lb = raw.get("horas_laborables") or {}
    semana_normal = normalize_hours((horas_lb.get("semana_normal") or {}))
    semana_intensiva = normalize_hours((horas_lb.get("jornada_intensiva") or {}))

    return Config(
        vacaciones=vacaciones,
        festivos=festivos,
        jornada_intensiva_inicio=ji_inicio,
        jornada_intensiva_fin=ji_fin,
        horas_semana_normal=semana_normal,
        horas_jornada_intensiva=semana_intensiva,
    )


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is not None and not isinstance(raw, dict):
        raise ValueError("El fichero de configuración debe ser un mapa YAML en la raíz.")

    return config_from_raw(raw if isinstance(raw, dict) else None)


def calcular_horas_laborables(year: int, config: Config) -> dict:
    inicio = date(year, 1, 1)
    fin = date(year, 12, 31)

    total_horas = 0.0
    dias_laborables_computados = 0
    dias_descartados_por_festivo = 0
    dias_descartados_por_vacaciones = 0
    dias_fin_de_semana = 0
    detalle = []

    for dia in daterange(inicio, fin):
        weekday = dia.weekday()

        if weekday >= 5:
            dias_fin_de_semana += 1
            continue

        if dia in config.festivos:
            dias_descartados_por_festivo += 1
            continue

        if dia in config.vacaciones:
            dias_descartados_por_vacaciones += 1
            continue

        en_jornada_intensiva = config.jornada_intensiva_inicio <= dia <= config.jornada_intensiva_fin
        horas_dia = (
            config.horas_jornada_intensiva[weekday]
            if en_jornada_intensiva
            else config.horas_semana_normal[weekday]
        )

        if horas_dia > 0:
            dias_laborables_computados += 1
            total_horas += horas_dia
            detalle.append(
                {
                    "fecha": dia.isoformat(),
                    "dia_semana": weekday,
                    "horas": horas_dia,
                    "tipo_jornada": "intensiva" if en_jornada_intensiva else "normal",
                }
            )

    return {
        "anio": year,
        "horas_totales": total_horas,
        "dias_laborables_computados": dias_laborables_computados,
        "dias_descartados_por_festivo": dias_descartados_por_festivo,
        "dias_descartados_por_vacaciones": dias_descartados_por_vacaciones,
        "dias_fin_de_semana": dias_fin_de_semana,
        "detalle": detalle,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calcula las horas laborables de un año usando una configuración YAML."
    )
    parser.add_argument("year", type=int, help="Año a calcular. Ejemplo: 2026")
    parser.add_argument(
        "-c",
        "--config",
        default="config_horas_laborables.yml",
        help="Ruta del fichero YAML de configuración.",
    )

    args = parser.parse_args()

    try:
        config = load_config(Path(args.config))
        resultado = calcular_horas_laborables(args.year, config)
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Año: {resultado['anio']}")
    print(f"Horas laborables totales: {resultado['horas_totales']}")
    print(f"Días laborables computados: {resultado['dias_laborables_computados']}")
    print(f"Días descartados por festivo: {resultado['dias_descartados_por_festivo']}")
    print(f"Días descartados por vacaciones: {resultado['dias_descartados_por_vacaciones']}")
    print(f"Días de fin de semana: {resultado['dias_fin_de_semana']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
