"""
adubacao_culturas_backend.py

Backend de recomendação de adubação (N, P, K, S e micronutrientes quando aplicável)
para as culturas:
- Aveia (branca/preta – grãos)
- Milho (grãos)
- Soja
- Trigo (grãos)
- Gramíneas de estação fria (forrageiras)
- Gramíneas de estação quente (forrageiras)

BASE LEGAL:
Manual de Calagem e Adubação – RS/SC
Capítulo 6 – Adubação de culturas
(Tabelas e notas de rodapé conforme PDFs fornecidos pelo usuário)

IMPORTANTE AO CODEX / BACKEND:
- A classificação do solo (Muito baixo, Baixo, Médio, Alto, Muito alto)
  já deve vir pronta do módulo de interpretação do solo.
- Este módulo NÃO calcula classe de solo.
- Todas as doses estão em kg/ha.
"""

from dataclasses import dataclass
from typing import Literal, Optional


ClasseSolo = Literal["Muito baixo", "Baixo", "Médio", "Alto", "Muito alto"]
CulturaAntecedente = Literal["Leguminosa", "Gramínea", "Pousio", "Consorcio"]
UsoForrageira = Literal["Pastejo", "Corte"]


# =========================
# TABELAS BASE (P e K)
# =========================

# Estrutura padrão:
# tabela[cultura][nutriente][classe_solo][cultivo (1 ou 2)]

TABELAS_PK = {
    "aveia": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Médio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 110, 2: 70},
            "Baixo": {1: 70, 2: 50},
            "Médio": {1: 60, 2: 30},
            "Alto": {1: 30, 2: 30},
            "Muito alto": {1: 0, 2: 30},
        },
    },
    "milho": {
        "P": {
            "Muito baixo": {1: 200, 2: 140},
            "Baixo": {1: 140, 2: 120},
            "Médio": {1: 130, 2: 90},
            "Alto": {1: 90, 2: 90},
            "Muito alto": {1: 0, 2: 90},
        },
        "K": {
            "Muito baixo": {1: 140, 2: 100},
            "Baixo": {1: 100, 2: 80},
            "Médio": {1: 90, 2: 60},
            "Alto": {1: 60, 2: 60},
            "Muito alto": {1: 0, 2: 60},
        },
    },
    "soja": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Médio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 155, 2: 115},
            "Baixo": {1: 115, 2: 95},
            "Médio": {1: 105, 2: 75},
            "Alto": {1: 75, 2: 75},
            "Muito alto": {1: 0, 2: 75},
        },
    },
    "trigo": {
        "P": {
            "Muito baixo": {1: 155, 2: 95},
            "Baixo": {1: 95, 2: 75},
            "Médio": {1: 85, 2: 45},
            "Alto": {1: 45, 2: 45},
            "Muito alto": {1: 0, 2: 45},
        },
        "K": {
            "Muito baixo": {1: 110, 2: 70},
            "Baixo": {1: 70, 2: 50},
            "Médio": {1: 60, 2: 30},
            "Alto": {1: 30, 2: 30},
            "Muito alto": {1: 0, 2: 30},
        },
    },
}


# =========================
# FUNÇÕES AUXILIARES
# =========================

def ajuste_produtividade(
    dose_base: float,
    produtividade: float,
    produtividade_base: float,
    incremento_por_t: float
) -> float:
    """
    Ajusta dose quando produtividade esperada > produtividade base da tabela.
    """
    if produtividade <= produtividade_base:
        return dose_base
    excesso = produtividade - produtividade_base
    return dose_base + excesso * incremento_por_t


# =========================
# AVEIA (BRANCA / PRETA)
# =========================

def adubacao_aveia(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    cultivo: int = 1
):
    """
    Aveia para produção de grãos.
    Considera notas de rodapé completas (N, P e K).
    """

    # Nitrogênio
    if teor_mo <= 2.5:
        n_base = 60 if cultura_antecedente == "Leguminosa" else 80
    elif teor_mo <= 5.0:
        n_base = 40 if cultura_antecedente == "Leguminosa" else 60
    else:
        n_base = 20

    # Ajuste por produtividade > 3 t/ha
    if produtividade_t_ha > 3:
        n_base += (20 if cultura_antecedente == "Leguminosa" else 30) * (produtividade_t_ha - 3)

    p_base = TABELAS_PK["aveia"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["aveia"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 2:
        p_base += 10 * (produtividade_t_ha - 2)
        k_base += 10 * (produtividade_t_ha - 2)

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}


# =========================
# MILHO
# =========================

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
    cultivo: int = 1
):
    """
    Milho para produção de grãos.
    Implementa TODAS as notas de rodapé.
    """

    # N base por MO e cultura antecedente
    if teor_mo <= 2.5:
        n_base = {"Leguminosa": 70, "Consorcio": 80, "Gramínea": 90}[cultura_antecedente]
    elif teor_mo <= 5.0:
        n_base = {"Leguminosa": 50, "Consorcio": 60, "Gramínea": 70}[cultura_antecedente]
    else:
        n_base = {"Leguminosa": 40, "Consorcio": 40, "Gramínea": 50}[cultura_antecedente]

    # Ajustes por massa seca antecedente
    if massa_seca_antecedente_t_ha:
        if cultura_antecedente == "Leguminosa" and massa_seca_antecedente_t_ha > 3:
            n_base -= 20
        if cultura_antecedente == "Gramínea" and massa_seca_antecedente_t_ha > 4:
            n_base += 30

    # Ajuste por produtividade
    if produtividade_t_ha > 6:
        n_base += 15 * (produtividade_t_ha - 6)

    # Ajuste por densidade
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


# =========================
# SOJA
# =========================

def adubacao_soja(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    teor_s_mg_dm3: float,
    teor_mo_percent: Optional[float] = None,
    ph_agua: Optional[float] = None,
    argila_classe: Optional[int] = None,
    metodo_aplicacao_mo: str = "foliar",
    cultivo: int = 1
):
    """
    Soja – sem N mineral.
    Considera enxofre e micronutrientes conforme texto.
    """

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

    if (
        cultivo == 1
        and teor_mo_percent is not None
        and ph_agua is not None
        and ph_agua < 5.5
    ):
        if teor_mo_percent <= 2.5:
            mo = 0.050 if metodo == "foliar" else 0.025
        elif teor_mo_percent <= 5.0:
            mo = 0.025 if metodo == "foliar" else 0.012

    if mo > 0 and argila_classe == 4:
        mo *= 1.4

    return {
        "N": 0,
        "P2O5": p_base,
        "K2O": k_base,
        "S": s,
        "Mo": mo,
        "Micros": "Aplicar Mo foliar entre 30 e 45 dias apos emergencia (quando aplicavel)."
    }


# =========================
# TRIGO
# =========================

def adubacao_trigo(
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    produtividade_t_ha: float,
    cultura_antecedente: CulturaAntecedente,
    teor_mo: float,
    cultivo: int = 1
):
    """
    Trigo exclusivamente para produção de grãos.
    """

    if teor_mo <= 2.5:
        n_base = 60 if cultura_antecedente == "Leguminosa" else 80
    elif teor_mo <= 5.0:
        n_base = 40 if cultura_antecedente == "Leguminosa" else 60
    else:
        n_base = 20

    if produtividade_t_ha > 3:
        n_base += (20 if cultura_antecedente == "Leguminosa" else 30) * (produtividade_t_ha - 3)

    p_base = TABELAS_PK["trigo"]["P"][classe_p][cultivo]
    k_base = TABELAS_PK["trigo"]["K"][classe_k][cultivo]

    if produtividade_t_ha > 3:
        p_base += 15 * (produtividade_t_ha - 3)
        k_base += 10 * (produtividade_t_ha - 3)

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}


# =========================
# GRAMÍNEAS FORRAGEIRAS
# =========================

def adubacao_gramineas_forrageiras(
    estacao: Literal["fria", "quente"],
    classe_p: ClasseSolo,
    classe_k: ClasseSolo,
    teor_mo: float,
    produtividade_ms_t_ha: float,
    uso: UsoForrageira,
    cultivo: int = 1
):
    """
    Backend unificado para gramíneas de estação fria e quente.
    """

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

    else:  # quente
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

    p_base = 60 if classe_p in ["Alto", "Muito alto"] else TABELAS_PK["aveia"]["P"][classe_p][cultivo]
    k_base = 60 if classe_k in ["Alto", "Muito alto"] else TABELAS_PK["aveia"]["K"][classe_k][cultivo]

    if uso == "Corte":
        k_base += 20 * produtividade_ms_t_ha

    return {"N": n_base, "P2O5": p_base, "K2O": k_base}
