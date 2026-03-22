from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Mapping, Optional, Tuple


class AvailabilityClass(str, Enum):
    """Five-level availability scale used for P and K."""

    MUITO_BAIXO = "Muito baixo"
    BAIXO = "Baixo"
    MEDIO = "Medio"
    ALTO = "Alto"
    MUITO_ALTO = "Muito alto"


class ThreeLevelClass(str, Enum):
    """Three-level scale used for Ca, Mg, S and micronutrients."""

    BAIXO = "Baixo"
    MEDIO = "Medio"
    ALTO = "Alto"


def _sanitize_float(value: object) -> Optional[float]:
    """Return ``value`` as float, ignoring percent signs and commas."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace(",", ".")
    cleaned = re.sub(r"[^0-9\.\-]", "", normalized)
    if cleaned in {"", "-", ".", "-.", ".-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def clay_class(argila_percent: float) -> int:
    """Tabela 6.1: return class 1..4 for P interpretation."""

    if argila_percent > 60:
        return 1
    if 41 <= argila_percent <= 60:
        return 2
    if 21 <= argila_percent <= 40:
        return 3
    return 4


def ctc_range(ctc_cmolc_dm3: float) -> int:
    """Tabela 6.1: return range index (1..4) for K interpretation."""

    if ctc_cmolc_dm3 <= 7.5:
        return 1
    if 7.6 <= ctc_cmolc_dm3 <= 15.0:
        return 2
    if 15.1 <= ctc_cmolc_dm3 <= 30.0:
        return 3
    return 4


def clay_class_label(argila_percent: float) -> str:
    """Return clay classification label following Tabela 6.1."""

    return f"Classe {clay_class(argila_percent)}"


def classify_organic_matter(value_percent: float) -> ThreeLevelClass:
    """Tabela 6.1: classify soil organic matter."""

    if value_percent <= 2.5:
        return ThreeLevelClass.BAIXO
    if value_percent <= 5.0:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_ctc_level(value_cmolc_dm3: float) -> str:
    """Tabela 6.1: classify CTC availability."""

    mapping = {
        1: "Baixa",
        2: "Media",
        3: "Alta",
        4: "Muito alta",
    }
    return mapping[ctc_range(value_cmolc_dm3)]


def p_mehlich3_to_mehlich1(value: float, argila_percent: float) -> float:
    """Convert Mehlich-3 P to Mehlich-1 equivalent."""

    denom = 2.0 - (0.02 * argila_percent)
    if denom <= 0:
        raise ValueError("Invalid denominator in Mehlich-3 -> Mehlich-1 conversion.")
    return value / denom


def k_mehlich3_to_mehlich1(value: float) -> float:
    """Convert Mehlich-3 K to Mehlich-1 equivalent."""

    return value * 0.83


# ------------------------------------------------------------------------------
# Interval helper used by table lookups
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    include_min: bool = True
    include_max: bool = True

    def contains(self, value: float) -> bool:
        if self.minimo is not None:
            if self.include_min:
                if value < self.minimo:
                    return False
            else:
                if value <= self.minimo:
                    return False
        if self.maximo is not None:
            if self.include_max:
                if value > self.maximo:
                    return False
            else:
                if value >= self.maximo:
                    return False
        return True


_P_GRUPO2 = {
    1: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=3.0)),
        (AvailabilityClass.BAIXO, Interval(minimo=3.1, maximo=6.0, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=6.1, maximo=9.0, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=9.1, maximo=18.0, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=18.0, include_min=False)),
    ],
    2: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=4.0)),
        (AvailabilityClass.BAIXO, Interval(minimo=4.1, maximo=8.0, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=8.1, maximo=12.0, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=12.1, maximo=24.0, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=24.0, include_min=False)),
    ],
    3: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=6.0)),
        (AvailabilityClass.BAIXO, Interval(minimo=6.1, maximo=12.0, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=12.1, maximo=18.0, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=18.1, maximo=36.0, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=36.0, include_min=False)),
    ],
    4: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=10.0)),
        (AvailabilityClass.BAIXO, Interval(minimo=10.1, maximo=20.0, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=20.1, maximo=30.0, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=30.1, maximo=60.0, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=60.0, include_min=False)),
    ],
}


_K_GRUPO2 = {
    1: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=20)),
        (AvailabilityClass.BAIXO, Interval(minimo=21, maximo=40, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=41, maximo=60, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=61, maximo=120, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=120, include_min=False)),
    ],
    2: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=30)),
        (AvailabilityClass.BAIXO, Interval(minimo=31, maximo=60, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=61, maximo=90, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=91, maximo=180, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=180, include_min=False)),
    ],
    3: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=40)),
        (AvailabilityClass.BAIXO, Interval(minimo=41, maximo=80, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=81, maximo=120, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=121, maximo=240, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=240, include_min=False)),
    ],
    4: [
        (AvailabilityClass.MUITO_BAIXO, Interval(maximo=45)),
        (AvailabilityClass.BAIXO, Interval(minimo=46, maximo=90, include_min=True)),
        (AvailabilityClass.MEDIO, Interval(minimo=91, maximo=135, include_min=True)),
        (AvailabilityClass.ALTO, Interval(minimo=136, maximo=270, include_min=True)),
        (AvailabilityClass.MUITO_ALTO, Interval(minimo=270, include_min=False)),
    ],
}


def classify_p(value_mg_dm3: float, argila_percent: float, metodo: str = "Mehlich-1") -> Tuple[AvailabilityClass, float]:
    metodo_norm = metodo.strip().lower()
    if metodo_norm in {"mehlich-3", "mehlich3", "m3"}:
        equiv = p_mehlich3_to_mehlich1(value_mg_dm3, argila_percent)
    else:
        equiv = value_mg_dm3
    classe = clay_class(argila_percent)
    for label, interval in _P_GRUPO2[classe]:
        if interval.contains(equiv):
            return label, equiv
    raise RuntimeError("Unable to classify P value.")


def classify_k(value_mg_dm3: float, ctc_cmolc_dm3: float, metodo: str = "Mehlich-1") -> Tuple[AvailabilityClass, float]:
    metodo_norm = metodo.strip().lower()
    if metodo_norm in {"mehlich-3", "mehlich3", "m3"}:
        equiv = k_mehlich3_to_mehlich1(value_mg_dm3)
    else:
        equiv = value_mg_dm3
    faixa = ctc_range(ctc_cmolc_dm3)
    for label, interval in _K_GRUPO2[faixa]:
        if interval.contains(equiv):
            return label, equiv
    raise RuntimeError("Unable to classify K value.")


def classify_ca(value: float) -> ThreeLevelClass:
    if value < 2.0:
        return ThreeLevelClass.BAIXO
    if value <= 4.0:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_mg(value: float) -> ThreeLevelClass:
    if value < 0.5:
        return ThreeLevelClass.BAIXO
    if value <= 1.0:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_s(value: float, critical_double: bool = False) -> ThreeLevelClass:
    if not critical_double:
        if value < 2.0:
            return ThreeLevelClass.BAIXO
        if value <= 5.0:
            return ThreeLevelClass.MEDIO
        return ThreeLevelClass.ALTO
    if value < 2.0:
        return ThreeLevelClass.BAIXO
    if value <= 10.0:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_cu(value: float) -> ThreeLevelClass:
    if value < 0.2:
        return ThreeLevelClass.BAIXO
    if value <= 0.4:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_zn(value: float) -> ThreeLevelClass:
    if value < 0.2:
        return ThreeLevelClass.BAIXO
    if value <= 0.5:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_b(value: float) -> ThreeLevelClass:
    if value < 0.2:
        return ThreeLevelClass.BAIXO
    if value <= 0.3:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


def classify_mn(value: float) -> ThreeLevelClass:
    if value < 2.5:
        return ThreeLevelClass.BAIXO
    if value <= 5.0:
        return ThreeLevelClass.MEDIO
    return ThreeLevelClass.ALTO


@dataclass(frozen=True)
class SoilElementCondition:
    code: str
    label: str
    clazz: str
    value: float
    unit: str


@dataclass(frozen=True)
class SoilConditionSummary:
    elements: dict[str, SoilElementCondition]
    warnings: tuple[str, ...] = ()


class SoilDataError(Exception):
    """Raised when metadata is insufficient to build the soil condition summary."""


def _require_float(meta: Mapping[str, object], key: str, label: str) -> float:
    value = _sanitize_float(meta.get(key))
    if value is None:
        raise SoilDataError(f"Valor '{label}' nao informado.")
    return value


def summarize_from_metadata(metadata: Mapping[str, object]) -> SoilConditionSummary:
    """
    Build :class:`SoilConditionSummary` from a field metadata dictionary.

    Expected keys: argila, ctc, mo, p, k, ca, mg, s, zn, b, cu, mn.
    """

    argila = _require_float(metadata, "argila", "Argila")
    ctc = _require_float(metadata, "ctc", "CTC")
    mo_percent = _require_float(metadata, "mo", "Materia organica")
    p_valor = _require_float(metadata, "p", "P")
    k_valor = _require_float(metadata, "k", "K")
    ca = _require_float(metadata, "ca", "Ca")
    mg = _require_float(metadata, "mg", "Mg")
    s_valor = _require_float(metadata, "s", "S")
    zn = _require_float(metadata, "zn", "Zn")
    b_valor = _require_float(metadata, "b", "B")
    cu_valor = _require_float(metadata, "cu", "Cu")
    mn_valor = _require_float(metadata, "mn", "Mn")

    p_class, p_equiv = classify_p(p_valor, argila, metadata.get("p_metodo", "Mehlich-1"))
    k_class, k_equiv = classify_k(k_valor, ctc, metadata.get("k_metodo", "Mehlich-1"))
    ca_class = classify_ca(ca)
    mg_class = classify_mg(mg)
    s_class = classify_s(s_valor)
    zn_class = classify_zn(zn)
    b_class = classify_b(b_valor)
    cu_class = classify_cu(cu_valor)
    mn_class = classify_mn(mn_valor)
    argila_class_label = clay_class_label(argila)
    mo_class = classify_organic_matter(mo_percent)
    ctc_class_label = classify_ctc_level(ctc)

    elements: dict[str, SoilElementCondition] = {
        "ARGILA": SoilElementCondition("ARGILA", "Argila", argila_class_label, argila, "%"),
        "MO": SoilElementCondition("MO", "Materia organica", mo_class.value, mo_percent, "%"),
        "CTC": SoilElementCondition("CTC", "CTC", ctc_class_label, ctc, "cmolc/dm3"),
        "P": SoilElementCondition("P", "Fosforo", p_class.value, p_equiv, "mg/dm3"),
        "K": SoilElementCondition("K", "Potassio", k_class.value, k_equiv, "mg/dm3"),
        "Ca": SoilElementCondition("Ca", "Calcio", ca_class.value, ca, "cmolc/dm3"),
        "Mg": SoilElementCondition("Mg", "Magnesio", mg_class.value, mg, "cmolc/dm3"),
        "S": SoilElementCondition("S", "Enxofre", s_class.value, s_valor, "mg/dm3"),
        "Zn": SoilElementCondition("Zn", "Zinco", zn_class.value, zn, "mg/dm3"),
        "Cu": SoilElementCondition("Cu", "Cobre", cu_class.value, cu_valor, "mg/dm3"),
        "B": SoilElementCondition("B", "Boro", b_class.value, b_valor, "mg/dm3"),
        "Mn": SoilElementCondition("Mn", "Manganes", mn_class.value, mn_valor, "mg/dm3"),
    }

    return SoilConditionSummary(elements=elements, warnings=())
