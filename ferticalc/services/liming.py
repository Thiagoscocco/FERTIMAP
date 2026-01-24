"""
Liming recommendation helpers derived from the RS/SC manual (chapter 5).

This module mirrors the behaviour of ``calagem.py`` located at the project root
and is tailored for consumption by the Tk pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class LimingMethod(str, Enum):
    """Method selected by the agronomic rules."""

    SMP_TABLE = "SMP (Tabela 5.2)"
    V_PERCENT = "Saturacao por bases (V%)"
    POLYNOMIAL = "Equacoes polinomiais (SMP > 6,3)"


class ManagementScenario(str, Enum):
    """Supported management scenarios (subset of tables 5.3 and 5.4)."""

    CONVENCIONAL_GRAOS = "Convencional (graos)"
    IMPLANTACAO_PD_GRAOS = "Implantacao de plantio direto (graos)"
    PD_CONSOLIDADO_GRAOS = "Plantio direto consolidado"
    CAMPO_NATURAL = "Pastagem natural"


@dataclass(frozen=True)
class LimingRecommendation:
    nc_prnt100_t_ha: float
    dose_produto_t_ha: float
    metodo_usado: LimingMethod
    ph_alvo: float
    modo_aplicacao: str
    avisos: List[str]


class LimingError(Exception):
    """Raised when there is not enough information to compute the dose."""


_SMP_TABLE: Dict[float, Dict[float, float]] = {
    4.4: {5.5: 15.0, 6.0: 21.0, 6.5: 29.0},
    4.5: {5.5: 12.5, 6.0: 17.3, 6.5: 24.0},
    4.6: {5.5: 10.9, 6.0: 15.1, 6.5: 20.0},
    4.7: {5.5: 9.6, 6.0: 13.3, 6.5: 17.5},
    4.8: {5.5: 8.5, 6.0: 11.9, 6.5: 15.7},
    4.9: {5.5: 7.7, 6.0: 10.7, 6.5: 14.2},
    5.0: {5.5: 6.6, 6.0: 9.9, 6.5: 13.3},
    5.1: {5.5: 6.0, 6.0: 9.1, 6.5: 12.3},
    5.2: {5.5: 5.3, 6.0: 8.3, 6.5: 11.3},
    5.3: {5.5: 4.8, 6.0: 7.5, 6.5: 10.4},
    5.4: {5.5: 4.2, 6.0: 6.8, 6.5: 9.5},
    5.5: {5.5: 3.7, 6.0: 6.1, 6.5: 8.6},
    5.6: {5.5: 3.2, 6.0: 5.4, 6.5: 7.8},
    5.7: {5.5: 2.8, 6.0: 4.8, 6.5: 7.0},
    5.8: {5.5: 2.3, 6.0: 4.2, 6.5: 6.3},
    5.9: {5.5: 2.0, 6.0: 3.7, 6.5: 5.6},
    6.0: {5.5: 1.6, 6.0: 3.2, 6.5: 4.9},
    6.1: {5.5: 1.3, 6.0: 2.7, 6.5: 4.3},
    6.2: {5.5: 1.0, 6.0: 2.2, 6.5: 3.7},
    6.3: {5.5: 0.8, 6.0: 1.8, 6.5: 3.1},
    6.4: {5.5: 0.6, 6.0: 1.4, 6.5: 2.6},
    6.5: {5.5: 0.4, 6.0: 1.1, 6.5: 2.1},
    6.6: {5.5: 0.2, 6.0: 0.8, 6.5: 1.6},
    6.7: {5.5: 0.0, 6.0: 0.5, 6.5: 1.2},
    6.8: {5.5: 0.0, 6.0: 0.3, 6.5: 0.8},
    6.9: {5.5: 0.0, 6.0: 0.2, 6.5: 0.5},
    7.0: {5.5: 0.0, 6.0: 0.0, 6.5: 0.2},
    7.1: {5.5: 0.0, 6.0: 0.0, 6.5: 0.0},
}


def _round_to_0_1(value: float) -> float:
    return round(value * 10) / 10.0


def _smp_lookup_with_interp(smp: float, ph_alvo: float) -> float:
    if ph_alvo not in (5.5, 6.0, 6.5):
        raise ValueError("ph_alvo deve ser 5.5, 6.0 ou 6.5.")
    smp_min, smp_max = min(_SMP_TABLE), max(_SMP_TABLE)
    if smp < smp_min or smp > smp_max:
        raise ValueError(f"SMP fora do intervalo da Tabela 5.2 ({smp_min} a {smp_max}).")
    s = _round_to_0_1(smp)
    if s in _SMP_TABLE:
        return _SMP_TABLE[s][ph_alvo]
    s_low = max(key for key in _SMP_TABLE if key < s)
    s_high = min(key for key in _SMP_TABLE if key > s)
    y_low = _SMP_TABLE[s_low][ph_alvo]
    y_high = _SMP_TABLE[s_high][ph_alvo]
    t = (smp - s_low) / (s_high - s_low)
    return y_low + t * (y_high - y_low)


def v_target_for_ph(ph_alvo: float) -> float:
    if ph_alvo == 5.5:
        return 65.0
    if ph_alvo == 6.0:
        return 75.0
    if ph_alvo == 6.5:
        return 85.0
    raise ValueError("ph_alvo deve ser 5.5, 6.0 ou 6.5.")


def nc_from_v_percent(v_atual: float, ctc_ph7: float, ph_alvo: float) -> float:
    delta = (v_target_for_ph(ph_alvo) - v_atual) / 100.0
    return max(0.0, delta * ctc_ph7)


def nc_from_polynomial(mo_percent: float, al_cmolc: float, ph_alvo: float) -> float:
    if ph_alvo == 5.5:
        nc = -0.653 + 0.480 * mo_percent + 1.937 * al_cmolc
    elif ph_alvo == 6.0:
        nc = -0.516 + 0.805 * mo_percent + 2.435 * al_cmolc
    elif ph_alvo == 6.5:
        nc = -0.122 + 1.193 * mo_percent + 2.713 * al_cmolc
    else:
        raise ValueError("ph_alvo deve ser 5.5, 6.0 ou 6.5.")
    return max(0.0, nc)


def adjust_by_prnt(nc_prnt100: float, prnt_percent: float) -> float:
    if prnt_percent <= 0:
        raise ValueError("PRNT deve ser maior que zero.")
    return nc_prnt100 * (100.0 / prnt_percent)


def limit_surface(nc_prnt100: float, limit_t_ha: float = 5.0) -> float:
    return min(nc_prnt100, limit_t_ha)


def skip_by_v_and_m(v_percent: float, m_percent: float) -> bool:
    return (v_percent >= 65.0) and (m_percent < 10.0)


def _preferred_method(smp: float, mo: Optional[float], al: Optional[float]) -> LimingMethod:
    if smp > 6.3 and mo is not None and al is not None:
        return LimingMethod.POLYNOMIAL
    return LimingMethod.SMP_TABLE


def _preferred_nc(smp: float, ph_alvo: float, mo: Optional[float], al: Optional[float]) -> float:
    if smp > 6.3:
        if mo is None or al is None:
            return _smp_lookup_with_interp(smp, ph_alvo)
        return nc_from_polynomial(mo, al, ph_alvo)
    return _smp_lookup_with_interp(smp, ph_alvo)


def recommend_liming(
    *,
    scenario: ManagementScenario,
    ph_agua: float,
    smp: float,
    v_percent: float,
    m_percent: float,
    ctc_ph7: float,
    mo_percent: Optional[float],
    al_cmolc: Optional[float],
    prnt_percent: float,
    ph_referencia: float,
    ca_cmolc: Optional[float] = None,
    mg_cmolc: Optional[float] = None,
) -> LimingRecommendation:
    avisos: List[str] = []

    if skip_by_v_and_m(v_percent, m_percent):
        return LimingRecommendation(
            nc_prnt100_t_ha=0.0,
            dose_produto_t_ha=0.0,
            metodo_usado=LimingMethod.SMP_TABLE,
            ph_alvo=ph_referencia,
            modo_aplicacao="Nao aplicar",
            avisos=["Regra do manual: nao aplicar quando V >= 65% e saturacao por Al < 10%."],
        )

    modo = "Incorporado"
    ph_alvo = ph_referencia

    if scenario in (
        ManagementScenario.CONVENCIONAL_GRAOS,
        ManagementScenario.IMPLANTACAO_PD_GRAOS,
    ):
        ph_alvo = 6.0
        modo = "Incorporado"
        if ph_agua >= 5.5:
            avisos.append("pH >= 5,5: criterio indica nao aplicar.")
            nc_prnt100 = 0.0
        else:
            nc_prnt100 = _preferred_nc(smp, ph_alvo, mo_percent, al_cmolc)

    elif scenario == ManagementScenario.PD_CONSOLIDADO_GRAOS:
        avisos.append(
            "PD consolidado: o manual requer amostras 0-10 e 10-20 cm. Criterio simplificado aplicado."
        )
        ph_alvo = 6.0
        modo = "Superficial"
        if ph_agua >= 5.5:
            avisos.append("pH >= 5,5: criterio simplificado indica nao aplicar.")
            nc_prnt100 = 0.0
        else:
            nc_integral = _preferred_nc(smp, ph_alvo, mo_percent, al_cmolc)
            nc_prnt100 = limit_surface(0.25 * nc_integral, 5.0)

    elif scenario == ManagementScenario.CAMPO_NATURAL:
        modo = "Superficial"
        ph_alvo = ph_referencia
        if ca_cmolc is not None and mg_cmolc is not None:
            if abs(ca_cmolc - 4.0) < 1e-9 and abs(mg_cmolc - 1.0) < 1e-9:
                avisos.append("Campo natural: regra Ca=4 e Mg=1 indica nao aplicar.")
                nc_prnt100 = 0.0
            else:
                nc_prnt100 = max(0.0, ((40.0 - v_percent) / 100.0) * ctc_ph7)
        else:
            avisos.append("Informe Ca e Mg para aplicar integralmente as notas do campo natural.")
            nc_prnt100 = max(0.0, ((40.0 - v_percent) / 100.0) * ctc_ph7)
        nc_prnt100 = limit_surface(nc_prnt100, 5.0)
        avisos.append("Campo natural: nao aplicar junto com fosfatos naturais (nota do manual).")

    else:
        raise LimingError(f"Cenario nao suportado: {scenario}")

    if modo.lower().startswith("super"):
        nc_prnt100 = limit_surface(nc_prnt100, 5.0)

    dose_produto = adjust_by_prnt(nc_prnt100, prnt_percent)
    metodo = _preferred_method(smp, mo_percent, al_cmolc)

    return LimingRecommendation(
        nc_prnt100_t_ha=round(nc_prnt100, 3),
        dose_produto_t_ha=round(dose_produto, 3),
        metodo_usado=metodo,
        ph_alvo=ph_alvo,
        modo_aplicacao=modo,
        avisos=avisos,
    )
