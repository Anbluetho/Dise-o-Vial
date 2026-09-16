"""Cálculos de capacidad y nivel de servicio vial derivados de Formulas_Vial_S5.

Las funciones trabajan con unidades del documento: km/h, veh/h, pc/h/carril y
pc/km/carril. Los factores se expresan como decimales (por ejemplo, 0.60).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _positivo(nombre: str, valor: float) -> float:
    """Valida que un dato numérico sea estrictamente positivo."""
    if valor <= 0:
        raise ValueError(f"{nombre} debe ser mayor que cero; se recibió {valor}.")
    return float(valor)


def buscar_en_tabla(
    tabla: Sequence[Mapping[str, Any]],
    criterios: Mapping[str, Any],
    columna_resultado: str,
) -> float:
    """Busca un valor de ajuste en una tabla de diccionarios.

    Cada fila debe contener las columnas usadas en ``criterios`` y la columna
    de salida. Ejemplo de una tabla de ajustes::

        [{"ancho_carril_m": 3.3, "f_lw": 1.9},
         {"ancho_carril_m": 3.6, "f_lw": 0.0}]

    Esta función permite que las tablas técnicas se carguen desde CSV, Excel o
    una base de datos antes de invocar el cálculo.
    """
    for fila in tabla:
        if all(fila.get(columna) == valor for columna, valor in criterios.items()):
            try:
                return float(fila[columna_resultado])
            except KeyError as exc:
                raise KeyError(
                    f"La fila encontrada no contiene '{columna_resultado}'."
                ) from exc
    raise LookupError(
        f"No existe una fila para los criterios {dict(criterios)} en la tabla."
    )


def velocidad_flujo_libre_base(limite_velocidad_kmh: float) -> float:
    """Calcula BFFS a partir del límite de velocidad definido en el documento."""
    limite = _positivo("limite_velocidad_kmh", limite_velocidad_kmh)
    if 65 <= limite <= 70:
        return limite + 11.0
    if 80 <= limite <= 90:
        return limite + 8.0
    raise ValueError(
        "El documento solo define BFFS para límites entre 65-70 o 80-90 km/h."
    )


def velocidad_flujo_libre(
    bffs_kmh: float,
    f_lw_kmh: float = 0.0,
    f_lc_kmh: float = 0.0,
    f_m_kmh: float = 0.0,
    f_a_kmh: float = 0.0,
) -> float:
    """Calcula FFS = BFFS - fLW - fLC - fM - fA."""
    ffs = _positivo("bffs_kmh", bffs_kmh) - sum(
        float(x) for x in (f_lw_kmh, f_lc_kmh, f_m_kmh, f_a_kmh)
    )
    return _positivo("FFS calculada", ffs)


def factor_hora_pico(volumen_horario_veh_h: float, flujo_15_min_max_veh: float) -> float:
    """Calcula PHF = volumen horario / (4 × máximo flujo de 15 minutos)."""
    phf = _positivo("volumen_horario_veh_h", volumen_horario_veh_h) / (
        4.0 * _positivo("flujo_15_min_max_veh", flujo_15_min_max_veh)
    )
    if not 0 < phf <= 1:
        raise ValueError(f"PHF debe estar en (0, 1]; se calculó {phf:.4f}.")
    return phf


def factor_vehiculos_pesados(
    proporcion_camiones: float,
    equivalencia_camion: float,
    proporcion_rv: float = 0.0,
    equivalencia_rv: float = 1.0,
) -> float:
    """Calcula fHV para camiones (T) y vehículos recreativos (R)."""
    for nombre, valor in (("proporcion_camiones", proporcion_camiones),
                          ("proporcion_rv", proporcion_rv)):
        if not 0 <= valor <= 1:
            raise ValueError(f"{nombre} debe estar entre 0 y 1.")
    denominador = (
        1.0
        + proporcion_camiones * (equivalencia_camion - 1.0)
        + proporcion_rv * (equivalencia_rv - 1.0)
    )
    return 1.0 / _positivo("denominador de fHV", denominador)


def tasa_flujo_equivalente(
    vhdd_veh_h: float, phf: float, numero_carriles: int,
    f_hv: float, f_p: float = 1.0,
) -> float:
    """Calcula vp = VHDD / (PHF × N × fHV × fp)."""
    return _positivo("vhdd_veh_h", vhdd_veh_h) / (
        _positivo("phf", phf)
        * _positivo("numero_carriles", numero_carriles)
        * _positivo("f_hv", f_hv)
        * _positivo("f_p", f_p)
    )


def numero_carriles_requeridos(
    vhdd_veh_h: float, phf: float, vp_objetivo_pc_h_ln: float,
    f_hv: float, f_p: float = 1.0,
) -> float:
    """Despeja N = VHDD / (PHF × vp × fHV × fp). Redondear después según diseño."""
    return _positivo("vhdd_veh_h", vhdd_veh_h) / (
        _positivo("phf", phf)
        * _positivo("vp_objetivo_pc_h_ln", vp_objetivo_pc_h_ln)
        * _positivo("f_hv", f_hv)
        * _positivo("f_p", f_p)
    )


def velocidad_promedio_automoviles(ffs_kmh: float, vp_pc_h_ln: float) -> float:
    """Calcula S cuando vp > 1400 pc/h/carril, con la ecuación de FFS aplicable."""
    ffs = _positivo("ffs_kmh", ffs_kmh)
    vp = _positivo("vp_pc_h_ln", vp_pc_h_ln)
    if vp <= 1400:
        raise ValueError("Esta ecuación del documento aplica solo cuando vp > 1400.")

    if 90 < ffs <= 100:
        a, b, c, d = 9.3, 630, 25, 15.7 * ffs - 770
    elif 80 < ffs <= 90:
        a, b, c, d = 10.4, 696, 26, 15.6 * ffs - 704
    elif 70 < ffs <= 80:
        a, b, c, d = 11.1, 728, 27, 15.9 * ffs - 672
    elif ffs == 70:
        a, b, c, d = 3.0, 150, 28, 25 * ffs - 1250
    else:
        raise ValueError("FFS debe estar entre 70 y 100 km/h según las ecuaciones dadas.")

    s = ffs - ((a * ffs - b) / c) * ((vp - 1400) / d) ** 1.31
    return _positivo("velocidad promedio S", s)


def densidad(vp_pc_h_ln: float, velocidad_promedio_kmh: float) -> float:
    """Calcula densidad D = vp / S en pc/km/carril."""
    return _positivo("vp_pc_h_ln", vp_pc_h_ln) / _positivo(
        "velocidad_promedio_kmh", velocidad_promedio_kmh
    )


def volumen_horario_diseno_direccional(
    tpda_veh_dia: float, proporcion_hora_pico: float, factor_direccional: float
) -> float:
    """Calcula VHDD = TPDA × K × factor direccional."""
    if not 0 < proporcion_hora_pico <= 1:
        raise ValueError("proporcion_hora_pico (K) debe estar en (0, 1].")
    if not 0 < factor_direccional <= 1:
        raise ValueError("factor_direccional debe estar en (0, 1].")
    return _positivo("tpda_veh_dia", tpda_veh_dia) * proporcion_hora_pico * factor_direccional
