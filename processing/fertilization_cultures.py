"""
Culture-specific fertilization requirements (N, P2O5, K2O, S, Mo).

Ported from adubacao_culturas_backend.py (ASCII-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .soil_conditions import SoilConditionSummary, clay_class


ClasseSolo = Literal["Muito baixo", "Baixo", "Medio", "Alto", "Muito alto"]
CulturaAntecedente = Literal["Leguminosa", "Graminea", "Pousio", "Consorcio"]
UsoForrageira = Literal["Pastejo", "Corte"]
MetodoAplicacaoMo = Literal["foliar", "semente"]


TABELAS_PK = {
    "aveia": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Medio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 110, 2: 70},
            "Baixo": {1: 70, 2: 50},
            "Medio": {1: 60, 2: 30},
            "Alto": {1: 30, 2: 30},
            "Muito alto": {1: 0, 2: 30},
        },
    },
    "milho": {
        "P": {
            "Muito baixo": {1: 200, 2: 140},
            "Baixo": {1: 140, 2: 120},
            "Medio": {1: 130, 2: 90},
            "Alto": {1: 90, 2: 90},
            "Muito alto": {1: 0, 2: 90},
        },
        "K": {
            "Muito baixo": {1: 140, 2: 100},
            "Baixo": {1: 100, 2: 80},
            "Medio": {1: 90, 2: 60},
            "Alto": {1: 60, 2: 60},
            "Muito alto": {1: 0, 2: 60},
        },
    },
    "soja": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Medio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 155, 2: 115},
            "Baixo": {1: 115, 2: 95},
            "Medio": {1: 105, 2: 75},
            "Alto": {1: 75, 2: 75},
            "Muito alto": {1: 0, 2: 75},
        },
    },
    "trigo": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Medio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 110, 2: 70},
            "Baixo": {1: 70, 2: 50},
            "Medio": {1: 60, 2: 30},
            "Alto": {1: 30, 2: 30},
            "Muito alto": {1: 0, 2: 30},
        },
    },
}


@dataclass(frozen=True)
class CultureRequirement:
    n_kg_ha: float
    p2o5_kg_ha: float
    k2o_kg_ha: float
    s_kg_ha: float = 0.0
    mo_kg_ha: float = 0.0
    notes: tuple[str, ...] = ()


def _classe_from_summary(summary: SoilConditionSummary, key: str) -> ClasseSolo:
    elem = summary.elements.get(key)
    if not elem:
        raise ValueError(f"Classe do nutriente {key} nao encontrada.")
    clazz = elem.clazz.strip().capitalize()
    if clazz == "Medio":
        return "Medio"
    return clazz  # "Muito baixo", "Baixo", "Alto", "Muito alto"


def _value_from_summary(summary: SoilConditionSummary, key: str) -> float:
    elem = summary.elements.get(key)
    if not elem:
        raise ValueError(f"Valor do nutriente {key} nao encontrado.")
    return elem.value


def adubacao_aveia(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    cultivo: int = 1,
) -> dict[str, float]:
    if teor_mo <= 2.5:
        n_base = 60 if cultura_antecedente == "Leguminosa" else 80
    elif teor_mo <= 5.0:
        n_base = 40 if cultura_antecedente == "Leguminosa" else 60
    else:
        n_base = 20

    if produtividade_t_ha > 3:
        n_base += (
            20 if cultura_antecedente == "Leguminosa" else 30
        ) * (produtividade_t_ha - 3)

    p_base = TABELAS_PK["aveia"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["aveia"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 2:
        p_base += 10 * (produtividade_t_ha - 2)
        k_base += 10 * (produtividade_t_ha - 2)

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}


def adubacao_milho(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    massa_seca_antecedente_t_ha: Optional[float],
    densidade_plantas_ha: Optional[float] = None,
    argila_classe: Optional[int] = None,
    ajustar_n_rendimento: bool = False,
    rotacao_soja: bool = False,
    cultivo: int = 1,
) -> dict[str, float]:
    if teor_mo <= 2.5:
        n_base = {"Leguminosa": 70, "Consorcio": 80, "Graminea": 90}[
            cultura_antecedente
        ]
    elif teor_mo <= 5.0:
        n_base = {"Leguminosa": 50, "Consorcio": 60, "Graminea": 70}[
            cultura_antecedente
        ]
    else:
        n_base = {"Leguminosa": 40, "Consorcio": 40, "Graminea": 50}[
            cultura_antecedente
        ]

    if massa_seca_antecedente_t_ha:
        if cultura_antecedente == "Leguminosa" and massa_seca_antecedente_t_ha > 3:
            n_base -= 20
        if cultura_antecedente == "Graminea" and massa_seca_antecedente_t_ha > 4:
            n_base += 30

    if produtividade_t_ha > 6:
        n_base += 15 * (produtividade_t_ha - 6)

    if densidade_plantas_ha and densidade_plantas_ha > 65000:
        n_base += ((densidade_plantas_ha - 65000) / 5000) * 10

    if ajustar_n_rendimento and produtividade_t_ha > 10 and argila_classe:
        ajuste = {1: 1.2, 2: 1.2, 3: 1.3, 4: 1.4}.get(argila_classe)
        if ajuste:
            n_base *= ajuste

    if rotacao_soja:
        n_base *= 0.8

    p_base = TABELAS_PK["milho"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["milho"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 6:
        p_base += 15 * (produtividade_t_ha - 6)
        k_base += 10 * (produtividade_t_ha - 6)

    return {"N": round(n_base, 1), "P2O5": p_base, "K2O": k_base}


def adubacao_soja(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    teor_s_mg_dm3: float,
    teor_mo_percent: float,
    ph_agua: Optional[float],
    argila_classe: Optional[int],
    metodo_aplicacao_mo: MetodoAplicacaoMo = "foliar",
    cultivo: int = 1,
) -> dict[str, float]:
    p_base = TABELAS_PK["soja"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["soja"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 3:
        p_base += 15 * (produtividade_t_ha - 3)
        k_base += 25 * (produtividade_t_ha - 3)

    s = 20 if teor_s_mg_dm3 < 10 else 0
    mo = 0.0
    metodo = (metodo_aplicacao_mo or "foliar").strip().lower()
    if metodo not in {"foliar", "semente"}:
        metodo = "foliar"

    # Mo para soja: 1o cultivo + MO baixa/media + pH < 5.5.
    if cultivo == 1 and ph_agua is not None and ph_agua < 5.5:
        if teor_mo_percent <= 2.5:
            mo = 0.050 if metodo == "foliar" else 0.025
        elif teor_mo_percent <= 5.0:
            mo = 0.025 if metodo == "foliar" else 0.012

    # Solo arenoso (classe 4): aumentar dose em 40%.
    if mo > 0 and argila_classe == 4:
        mo *= 1.4

    return {"N": 0, "P2O5": p_base, "K2O": k_base, "S": s, "Mo": mo}


def adubacao_trigo(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    cultivo: int = 1,
) -> dict[str, float]:
    if teor_mo <= 2.5:
        n_base = 60 if cultura_antecedente == "Leguminosa" else 80
    elif teor_mo <= 5.0:
        n_base = 40 if cultura_antecedente == "Leguminosa" else 60
    else:
        n_base = 20

    if produtividade_t_ha > 3:
        n_base += (
            20 if cultura_antecedente == "Leguminosa" else 30
        ) * (produtividade_t_ha - 3)

    p_base = TABELAS_PK["trigo"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["trigo"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 3:
        p_base += 15 * (produtividade_t_ha - 3)
        k_base += 10 * (produtividade_t_ha - 3)

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}


def adubacao_gramineas_forrageiras(
    estacao: Literal["fria", "quente"],
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    teor_mo: float,
    produtividade_ms_t_ha: float,
    uso: UsoForrageira,
    cultivo: int = 1,
) -> dict[str, float]:
    if estacao == "fria":
        if teor_mo < 1.6:
            n_base = 170
        elif teor_mo <= 2.5:
            n_base = 150
        elif teor_mo <= 3.5:
            n_base = 130
        elif teor_mo <= 4.5:
            n_base = 110
        else:
            n_base = 90
        if produtividade_ms_t_ha > 6:
            n_base += 30 * (produtividade_ms_t_ha - 6)
    else:
        if teor_mo < 1.6:
            n_base = 210
        elif teor_mo <= 2.5:
            n_base = 190
        elif teor_mo <= 3.5:
            n_base = 170
        elif teor_mo <= 4.5:
            n_base = 150
        else:
            n_base = 130
        if produtividade_ms_t_ha > 10:
            n_base += 30 * (produtividade_ms_t_ha - 10)

    p_base = (
        60
        if classe_p in ["Alto", "Muito alto"]
        else TABELAS_PK["aveia"]["P"][classe_p][cultivo]
    )
    k_base = (
        60
        if classe_k in ["Alto", "Muito alto"]
        else TABELAS_PK["aveia"]["K"][classe_k][cultivo]
    )

    if uso == "Corte":
        k_base += 20 * produtividade_ms_t_ha

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}


def requirement_from_summary(
    cultura: str,
    summary: SoilConditionSummary,
    *,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    teor_s_mg_dm3: float,
    massa_seca_antecedente_t_ha: Optional[float] = None,
    densidade_plantas_ha: Optional[float] = None,
    ajustar_n_rendimento: bool = False,
    rotacao_soja: bool = False,
    cultivo: int = 1,
    uso_forrageira: UsoForrageira = "Pastejo",
    produtividade_ms_t_ha: Optional[float] = None,
    ph_agua: Optional[float] = None,
    metodo_aplicacao_mo: MetodoAplicacaoMo = "foliar",
) -> CultureRequirement:
    cultura_key = cultura.strip().lower()
    classe_p = _classe_from_summary(summary, "P")
    classe_k = _classe_from_summary(summary, "K")

    notes: list[str] = []

    argila_classe: Optional[int] = None
    if "ARGILA" in summary.elements:
        argila_classe = clay_class(summary.elements["ARGILA"].value)

    if cultura_key in {"soja"}:
        dados = adubacao_soja(
            classe_p,
            classe_k,
            produtividade_t_ha,
            teor_s_mg_dm3,
            teor_mo,
            ph_agua,
            argila_classe,
            metodo_aplicacao_mo=metodo_aplicacao_mo,
            cultivo=cultivo,
        )
        if float(dados.get("Mo", 0.0)) > 0 and metodo_aplicacao_mo == "foliar":
            notes.append(
                "Aplicacao foliar de Mo: realizar entre 30 e 45 dias apos a emergencia."
            )
    elif cultura_key in {"milho"}:
        dados = adubacao_milho(
            classe_p,
            classe_k,
            produtividade_t_ha,
            cultura_antecedente,
            teor_mo,
            massa_seca_antecedente_t_ha,
            densidade_plantas_ha=densidade_plantas_ha,
            argila_classe=argila_classe,
            ajustar_n_rendimento=ajustar_n_rendimento,
            rotacao_soja=rotacao_soja,
            cultivo=cultivo,
        )
    elif cultura_key in {"trigo"}:
        dados = adubacao_trigo(
            classe_p,
            classe_k,
            produtividade_t_ha,
            cultura_antecedente,
            teor_mo,
            cultivo=cultivo,
        )
    elif cultura_key in {"aveia"}:
        dados = adubacao_aveia(
            classe_p,
            classe_k,
            produtividade_t_ha,
            cultura_antecedente,
            teor_mo,
            cultivo=cultivo,
        )
    elif cultura_key in {"gramineas de estacao fria", "gramineas estacao fria"}:
        dados = adubacao_gramineas_forrageiras(
            "fria",
            classe_p,
            classe_k,
            teor_mo,
            produtividade_ms_t_ha or produtividade_t_ha,
            uso_forrageira,
            cultivo=cultivo,
        )
    elif cultura_key in {"gramineas de estacao quente", "gramineas estacao quente"}:
        dados = adubacao_gramineas_forrageiras(
            "quente",
            classe_p,
            classe_k,
            teor_mo,
            produtividade_ms_t_ha or produtividade_t_ha,
            uso_forrageira,
            cultivo=cultivo,
        )
    else:
        raise ValueError(f"Cultura nao suportada: {cultura}")

    return CultureRequirement(
        n_kg_ha=float(dados.get("N", 0.0)),
        p2o5_kg_ha=float(dados.get("P2O5", 0.0)),
        k2o_kg_ha=float(dados.get("K2O", 0.0)),
        s_kg_ha=float(dados.get("S", 0.0)),
        mo_kg_ha=float(dados.get("Mo", 0.0)),
        notes=tuple(notes),
    )
