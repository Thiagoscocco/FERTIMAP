from __future__ import annotations

"""
Backend da aba de adubacao (FertiCalc)
=====================================

Objetivo deste arquivo
----------------------
Concentrar *toda* a logica, pipeline, funcoes, contas, equacoes e opcoes
necessarias para reproduzir exatamente o comportamento da aba "Adubacao"
do FertiCalc, incluindo o modo Misto, Formulado e Individual. Este arquivo
deve ser usado como base para portar o backend para outro software (ex:
por talhoes), mantendo as mesmas entradas e saidas.

PROMPT P/ FUTURA INTEGRACAO (talhoes):
- Mapeie as necessidades brutas de cada talhao para FertilizerRequirement
  (N, P2O5, K2O em kg/ha).
- Chame calculate_fertilizers() com o modo correspondente:
  * MIXED: exige grade do formulado (%) + sacos (50 kg) + complementos.
  * FORMULATED: exige grade do formulado (%) + complementos.
  * INDIVIDUAL: usa fertilizantes individuais selecionados pelo usuario.
- Retorne produtos/formulados/individuais exatamente como lista de
  tuplas (nome, kg/ha). A UI do novo software deve decidir como exibir.
- Reproduza os mesmos alertas, faltantes e mensagens de status.

Importante sobre equivalencia
-----------------------------
- As equacoes sao copiadas fielmente dos modulos:
  * app/services/fertilization.py
  * app/services/fertilizer_catalog.py
  * app/ui/adubacao_tab.py (coleta de entradas)
  * app/ui/resultados_tab.py (formatacao de saida)
- A ordem de calculo, a escolha do primeiro nutriente para calcular o
  formulado (K2O -> P2O5 -> N) e as regras de complemento sao identicas.
- A unidade padrao de entrada/saida e kg/ha. (Molibdato pode ser mostrado
  em g/ha pela UI, mas internamente fica em kg/ha.)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple
import unicodedata

KG_PER_SACK = 50.0


# ---------------------------------------------------------------------------
# Estruturas de dados (entradas e saidas)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FertilizerRequirement:
    """
    Necessidades brutas por hectare.

    PROMPT:
    - O novo software deve preencher estes valores exatamente como recebido
      do usuario (N, P2O5, K2O em kg/ha).
    - Valores negativos sao truncados para 0 durante o calculo.
    """

    nitrogen_kg_ha: float = 0.0
    p2o5_kg_ha: float = 0.0
    k2o_kg_ha: float = 0.0


@dataclass(slots=True)
class FertilizerResult:
    """
    Saida final para a aba de adubacao.

    status:
    - idle | ok | empty | error
    message:
    - mensagens para UI; mantem semantica do FertiCalc original.
    produtos:
    - lista (nome, kg/ha) de todos os produtos recomendados.
    formulados:
    - apenas formulados (quando aplicavel).
    individuais:
    - apenas complementos/individuais (quando aplicavel).
    alertas:
    - lista de avisos gerados durante o calculo.
    faltantes:
    - nutrientes nao atendidos (kg/ha).
    mode_label:
    - texto descritivo do modo.
    """

    status: str = "idle"
    message: str = ""
    produtos: List[Tuple[str, float]] = field(default_factory=list)
    formulados: List[Tuple[str, float]] = field(default_factory=list)
    individuais: List[Tuple[str, float]] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)
    faltantes: Dict[str, float] = field(default_factory=dict)
    mode_label: str = ""


class FertilizationMode(str, Enum):
    MIXED = "mixed"
    INDIVIDUAL = "individual"
    FORMULATED = "formulated"


# ---------------------------------------------------------------------------
# Catalogo de fertilizantes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fertilizante:
    codigo: str
    nome: str
    p2o5: float = 0.0
    k2o: float = 0.0
    s: float = 0.0
    mo: float = 0.0
    n: float = 0.0


def _normalize_name(texto: str | None) -> str:
    if not texto:
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower().strip()


_FOSFATADOS_SEQ: Tuple[Fertilizante, ...] = (
    Fertilizante("TSP", "Superfosfato Triplo (TSP)", p2o5=0.46),
    Fertilizante("SSP", "Superfosfato Simples (SSP)", p2o5=0.18, s=0.12),
    Fertilizante("MAP", "MAP", p2o5=0.52, n=0.11),
    Fertilizante("DAP", "DAP", p2o5=0.46, n=0.18),
)
FOSFATADOS: Dict[str, Fertilizante] = {item.codigo: item for item in _FOSFATADOS_SEQ}
_FOSFATADO_POR_NOME = {item.nome: item for item in _FOSFATADOS_SEQ}
_FOSFATADO_POR_NORMALIZED = {_normalize_name(item.nome): item for item in _FOSFATADOS_SEQ}
FOSFATADOS_CHOICES: Tuple[str, ...] = tuple(item.nome for item in _FOSFATADOS_SEQ)

_POTASSICOS_SEQ: Tuple[Fertilizante, ...] = (
    Fertilizante("KCl", "Cloreto de Potassio (KCl)", k2o=0.60),
    Fertilizante("K2SO4", "Sulfato de Potassio (K2SO4)", k2o=0.50, s=0.18),
)
POTASSICOS: Dict[str, Fertilizante] = {item.codigo: item for item in _POTASSICOS_SEQ}
_POTASSICO_POR_NOME = {item.nome: item for item in _POTASSICOS_SEQ}
_POTASSICO_POR_NORMALIZED = {_normalize_name(item.nome): item for item in _POTASSICOS_SEQ}
POTASSICOS_CHOICES: Tuple[str, ...] = tuple(item.nome for item in _POTASSICOS_SEQ)

_NITROGENADOS_SEQ: Tuple[Fertilizante, ...] = (
    Fertilizante("UREIA", "Ureia", n=0.45),
)
NITROGENADOS: Dict[str, Fertilizante] = {item.codigo: item for item in _NITROGENADOS_SEQ}
_NITROGENADO_POR_NOME = {item.nome: item for item in _NITROGENADOS_SEQ}
_NITROGENADO_POR_NORMALIZED = {_normalize_name(item.nome): item for item in _NITROGENADOS_SEQ}
NITROGENADOS_CHOICES: Tuple[str, ...] = tuple(item.nome for item in _NITROGENADOS_SEQ)

GESSO_PADRAO = Fertilizante("GESSO", "Gesso agricola", s=0.17)
MOLIBDATO_PADRAO = Fertilizante("MOLIBDATO", "Molibdato de sodio (Mo)", mo=0.39)

FORMULADO_COMPLEMENTO_P = FOSFATADOS["TSP"]
FORMULADO_COMPLEMENTO_K = POTASSICOS["KCl"]
FORMULADO_COMPLEMENTO_N = NITROGENADOS["UREIA"]


@dataclass
class FertilizacaoResultado:
    produtos: List[Tuple[str, float]]
    alertas: List[str]
    faltantes: Dict[str, float]
    formulados: List[Tuple[str, float]] = field(default_factory=list)
    individuais: List[Tuple[str, float]] = field(default_factory=list)


def obter_fosfatado_por_nome(nome: str | None) -> Fertilizante | None:
    if not nome:
        return None
    chave = _normalize_name(nome)
    return _FOSFATADO_POR_NOME.get(nome) or _FOSFATADO_POR_NORMALIZED.get(chave)


def obter_potassico_por_nome(nome: str | None) -> Fertilizante | None:
    if not nome:
        return None
    chave = _normalize_name(nome)
    return _POTASSICO_POR_NOME.get(nome) or _POTASSICO_POR_NORMALIZED.get(chave)


def obter_nitrogenado_por_nome(nome: str | None) -> Fertilizante | None:
    if not nome:
        return None
    chave = _normalize_name(nome)
    return _NITROGENADO_POR_NOME.get(nome) or _NITROGENADO_POR_NORMALIZED.get(chave)


# ---------------------------------------------------------------------------
# Utilitarios de calculo
# ---------------------------------------------------------------------------


def _adicionar_produto(destino: List[Tuple[str, float]], nome: str, quantidade: float, minimo: float = 1e-6) -> None:
    if quantidade <= minimo:
        return
    destino.append((nome, quantidade))


def _alerta_nitrogenio(fert: Fertilizante | None) -> str | None:
    if fert is None or fert.n <= 0:
        return None
    return f"{fert.nome} fornece nitrogenio; usar com cautela."


def _subtrair_fornecido(
    requerido: float,
    quantidade_kg: float,
    fracao: float,
) -> float:
    if requerido <= 0 or quantidade_kg <= 0 or fracao <= 0:
        return max(requerido, 0.0)
    return max(requerido - quantidade_kg * fracao, 0.0)


def _complementar_enxofre(
    restante_s: float,
    produtos: List[Tuple[str, float]],
    individuais: List[Tuple[str, float]],
) -> float:
    if restante_s <= 0:
        return 0.0
    if GESSO_PADRAO.s <= 0:
        raise ValueError("Fertilizante padrao de enxofre invalido.")
    kg = restante_s / GESSO_PADRAO.s
    _adicionar_produto(produtos, GESSO_PADRAO.nome, kg)
    _adicionar_produto(individuais, GESSO_PADRAO.nome, kg)
    return kg


def _complementar_molibdenio(
    restante_mo: float,
    produtos: List[Tuple[str, float]],
    individuais: List[Tuple[str, float]],
) -> float:
    if restante_mo <= 0:
        return 0.0
    if MOLIBDATO_PADRAO.mo <= 0:
        raise ValueError("Fertilizante padrao de molibdenio invalido.")
    kg = restante_mo / MOLIBDATO_PADRAO.mo
    _adicionar_produto(produtos, MOLIBDATO_PADRAO.nome, kg)
    _adicionar_produto(individuais, MOLIBDATO_PADRAO.nome, kg)
    return kg


# ---------------------------------------------------------------------------
# Nucleo de calculo - formulado, individual, misto
# ---------------------------------------------------------------------------


def calcular_formulado(
    demanda: Dict[str, float],
    grade: Dict[str, float],
    nome_formulado: str,
    *,
    complemento_n: Fertilizante | None = None,
    complemento_p: Fertilizante | None = None,
    complemento_k: Fertilizante | None = None,
    kg_formulado_predefinido: float | None = None,
) -> FertilizacaoResultado:
    """
    Calcula adubacao com fertilizante formulado + complementos.

    REGRAS (copiadas do FertiCalc):
    - grade: percentuais de N/P2O5/K2O (0-100).
    - Se kg_formulado_predefinido for None, escolhe o primeiro nutriente
      com demanda > 0 e fracao > 0 na ordem: K2O -> P2O5 -> N.
    - Se definido (modo misto), usa kg_formulado_predefinido direto.
    - O formulado atende parte das necessidades e o restante e completado
      com fertilizantes individuais (fosfatado, potassico, nitrogenado).
    - Complementa S e Mo com fertilizantes padrao se necessario.
    """

    produtos: List[Tuple[str, float]] = []
    formulados: List[Tuple[str, float]] = []
    individuais: List[Tuple[str, float]] = []
    alertas: List[str] = []
    faltantes: Dict[str, float] = {}

    n_req = max(demanda.get("N", 0.0), 0.0)
    p_req = max(demanda.get("P2O5", 0.0), 0.0)
    k_req = max(demanda.get("K2O", 0.0), 0.0)
    s_req = max(demanda.get("S", 0.0), 0.0)
    mo_req = max(demanda.get("Mo", 0.0), 0.0)

    n_frac = max(grade.get("N", 0.0), 0.0) / 100.0
    p_frac = max(grade.get("P2O5", 0.0), 0.0) / 100.0
    k_frac = max(grade.get("K2O", 0.0), 0.0) / 100.0

    kg_formulado = max(kg_formulado_predefinido or 0.0, 0.0)
    if kg_formulado_predefinido is None:
        for _nutriente, req, fracao in (
            ("K2O", k_req, k_frac),
            ("P2O5", p_req, p_frac),
            ("N", n_req, n_frac),
        ):
            if req > 0 and fracao > 0:
                kg_formulado = req / fracao
                break

    if kg_formulado > 0:
        _adicionar_produto(produtos, nome_formulado, kg_formulado)
        _adicionar_produto(formulados, nome_formulado, kg_formulado)

    n_suprido = kg_formulado * n_frac
    p_suprido = kg_formulado * p_frac
    k_suprido = kg_formulado * k_frac

    n_restante = max(n_req - n_suprido, 0.0)
    p_restante = max(p_req - p_suprido, 0.0)
    k_restante = max(k_req - k_suprido, 0.0)

    if p_restante > 0:
        fert_p = complemento_p or FORMULADO_COMPLEMENTO_P
        if fert_p.p2o5 <= 0:
            faltantes["P2O5"] = p_restante
            alertas.append("Selecione um fertilizante fosfatado valido para complementar o P2O5.")
        else:
            kg_p = p_restante / fert_p.p2o5
            _adicionar_produto(produtos, fert_p.nome, kg_p)
            _adicionar_produto(individuais, fert_p.nome, kg_p)
            alerta_n = _alerta_nitrogenio(fert_p)
            if alerta_n:
                alertas.append(alerta_n)
            n_restante = _subtrair_fornecido(n_restante, kg_p, fert_p.n)
            s_req = _subtrair_fornecido(s_req, kg_p, fert_p.s)
            mo_req = _subtrair_fornecido(mo_req, kg_p, fert_p.mo)

    if k_restante > 0:
        fert_k = complemento_k or FORMULADO_COMPLEMENTO_K
        if fert_k.k2o <= 0:
            faltantes["K2O"] = k_restante
            alertas.append("Selecione um fertilizante potassico valido para complementar o K2O.")
        else:
            kg_k = k_restante / fert_k.k2o
            _adicionar_produto(produtos, fert_k.nome, kg_k)
            _adicionar_produto(individuais, fert_k.nome, kg_k)
            s_req = _subtrair_fornecido(s_req, kg_k, fert_k.s)
            mo_req = _subtrair_fornecido(mo_req, kg_k, fert_k.mo)

    if n_restante > 0:
        fert_n = complemento_n or FORMULADO_COMPLEMENTO_N
        if fert_n.n <= 0:
            faltantes["N"] = n_restante
            alertas.append("Selecione um fertilizante nitrogenado valido para complementar o N.")
        else:
            kg_n = n_restante / fert_n.n
            _adicionar_produto(produtos, fert_n.nome, kg_n)
            _adicionar_produto(individuais, fert_n.nome, kg_n)
            s_req = _subtrair_fornecido(s_req, kg_n, fert_n.s)
            mo_req = _subtrair_fornecido(mo_req, kg_n, fert_n.mo)

    _complementar_enxofre(s_req, produtos, individuais)
    _complementar_molibdenio(mo_req, produtos, individuais)

    return FertilizacaoResultado(
        produtos=produtos,
        alertas=alertas,
        faltantes=faltantes,
        formulados=formulados,
        individuais=individuais,
    )


def calcular_individual_usuario(
    demanda: Dict[str, float],
    fosfatado_codigo: str | None,
    potassico_codigo: str | None,
    nitrogenado_codigo: str | None,
) -> FertilizacaoResultado:
    """
    Calcula adubacao individual com fertilizantes escolhidos pelo usuario.

    PROMPT:
    - Mantenha os mesmos alertas/faltantes quando o fertilizante nao atende
      ao nutriente ou quando o usuario escolhe um produto sem necessidade.
    - O resultado deve incluir somente os produtos individuais.
    """

    produtos: List[Tuple[str, float]] = []
    individuais: List[Tuple[str, float]] = []
    alertas: List[str] = []
    faltantes: Dict[str, float] = {}

    n_req = max(demanda.get("N", 0.0), 0.0)
    p_req = max(demanda.get("P2O5", 0.0), 0.0)
    k_req = max(demanda.get("K2O", 0.0), 0.0)
    s_req = max(demanda.get("S", 0.0), 0.0)
    mo_req = max(demanda.get("Mo", 0.0), 0.0)

    fert_p = FOSFATADOS.get(fosfatado_codigo or "")
    if p_req > 0:
        if fert_p is None or fert_p.p2o5 <= 0:
            faltantes["P2O5"] = p_req
            if fert_p is None:
                alertas.append("Selecione um fertilizante fosfatado para atender ao P2O5.")
            else:
                alertas.append(f"O fertilizante '{fert_p.nome}' nao fornece P2O5 suficiente.")
        else:
            kg_p = p_req / fert_p.p2o5
            _adicionar_produto(produtos, fert_p.nome, kg_p)
            _adicionar_produto(individuais, fert_p.nome, kg_p)
            alerta_n = _alerta_nitrogenio(fert_p)
            if alerta_n:
                alertas.append(alerta_n)
            n_req = _subtrair_fornecido(n_req, kg_p, fert_p.n)
            s_req = _subtrair_fornecido(s_req, kg_p, fert_p.s)
            mo_req = _subtrair_fornecido(mo_req, kg_p, fert_p.mo)
    elif fosfatado_codigo:
        alertas.append("Nenhuma necessidade de P2O5 foi informada.")

    fert_k = POTASSICOS.get(potassico_codigo or "")
    if k_req > 0:
        if fert_k is None or fert_k.k2o <= 0:
            faltantes["K2O"] = k_req
            if fert_k is None:
                alertas.append("Selecione um fertilizante potassico para atender ao K2O.")
            else:
                alertas.append(f"O fertilizante '{fert_k.nome}' nao fornece K2O suficiente.")
        else:
            kg_k = k_req / fert_k.k2o
            _adicionar_produto(produtos, fert_k.nome, kg_k)
            _adicionar_produto(individuais, fert_k.nome, kg_k)
            s_req = _subtrair_fornecido(s_req, kg_k, fert_k.s)
            mo_req = _subtrair_fornecido(mo_req, kg_k, fert_k.mo)
    elif potassico_codigo:
        alertas.append("Nenhuma necessidade de K2O foi informada.")

    fert_n = NITROGENADOS.get(nitrogenado_codigo or "")
    if n_req > 0:
        if fert_n is None or fert_n.n <= 0:
            faltantes["N"] = n_req
            if fert_n is None:
                alertas.append("Selecione um fertilizante nitrogenado para atender ao N.")
            else:
                alertas.append(f"O fertilizante '{fert_n.nome}' nao fornece N suficiente.")
        else:
            kg_n = n_req / fert_n.n
            _adicionar_produto(produtos, fert_n.nome, kg_n)
            _adicionar_produto(individuais, fert_n.nome, kg_n)
            s_req = _subtrair_fornecido(s_req, kg_n, fert_n.s)
            mo_req = _subtrair_fornecido(mo_req, kg_n, fert_n.mo)
    elif nitrogenado_codigo:
        alertas.append("Nenhuma necessidade de N foi informada.")

    _complementar_enxofre(s_req, produtos, individuais)
    _complementar_molibdenio(mo_req, produtos, individuais)

    return FertilizacaoResultado(
        produtos=produtos,
        alertas=alertas,
        faltantes=faltantes,
        individuais=individuais,
    )


def calcular_individual_software(demanda: Dict[str, float]) -> FertilizacaoResultado:
    """
    Variante usada internamente pelo software (sem escolha do usuario).

    REGRAS:
    - P2O5 -> TSP; se precisa de S e K==0 usa SSP.
    - K2O -> KCl; se precisa de S usa K2SO4.
    - N -> Ureia.
    """

    produtos: List[Tuple[str, float]] = []
    individuais: List[Tuple[str, float]] = []
    alertas: List[str] = []

    n_req = max(demanda.get("N", 0.0), 0.0)
    p_req = max(demanda.get("P2O5", 0.0), 0.0)
    k_req = max(demanda.get("K2O", 0.0), 0.0)
    s_req = max(demanda.get("S", 0.0), 0.0)
    mo_req = max(demanda.get("Mo", 0.0), 0.0)

    fert_p: Fertilizante | None = None
    fert_k: Fertilizante | None = None

    if p_req > 0:
        fert_p = FOSFATADOS["TSP"]
        if s_req > 0 and k_req == 0:
            fert_p = FOSFATADOS["SSP"]

    if k_req > 0:
        fert_k = POTASSICOS["KCl"]
        if s_req > 0:
            fert_k = POTASSICOS["K2SO4"]

    if fert_p is not None:
        kg_p = p_req / fert_p.p2o5
        _adicionar_produto(produtos, fert_p.nome, kg_p)
        _adicionar_produto(individuais, fert_p.nome, kg_p)
        alerta_n = _alerta_nitrogenio(fert_p)
        if alerta_n:
            alertas.append(alerta_n)
        n_req = _subtrair_fornecido(n_req, kg_p, fert_p.n)
        s_req = _subtrair_fornecido(s_req, kg_p, fert_p.s)
        mo_req = _subtrair_fornecido(mo_req, kg_p, fert_p.mo)

    if fert_k is not None:
        kg_k = k_req / fert_k.k2o
        _adicionar_produto(produtos, fert_k.nome, kg_k)
        _adicionar_produto(individuais, fert_k.nome, kg_k)
        s_req = _subtrair_fornecido(s_req, kg_k, fert_k.s)
        mo_req = _subtrair_fornecido(mo_req, kg_k, fert_k.mo)

    if n_req > 0:
        fert_n = NITROGENADOS["UREIA"]
        kg_n = n_req / fert_n.n
        _adicionar_produto(produtos, fert_n.nome, kg_n)
        _adicionar_produto(individuais, fert_n.nome, kg_n)
        s_req = _subtrair_fornecido(s_req, kg_n, fert_n.s)
        mo_req = _subtrair_fornecido(mo_req, kg_n, fert_n.mo)

    _complementar_enxofre(s_req, produtos, individuais)
    _complementar_molibdenio(mo_req, produtos, individuais)

    return FertilizacaoResultado(
        produtos=produtos,
        alertas=alertas,
        faltantes={},
        individuais=individuais,
    )


# ---------------------------------------------------------------------------
# Pipeline principal da aba adubacao
# ---------------------------------------------------------------------------


def _make_demanda(requirement: FertilizerRequirement) -> Dict[str, float]:
    return {
        "N": max(requirement.nitrogen_kg_ha, 0.0),
        "P2O5": max(requirement.p2o5_kg_ha, 0.0),
        "K2O": max(requirement.k2o_kg_ha, 0.0),
        "S": 0.0,
        "Mo": 0.0,
    }


def calculate_fertilizers(
    requirement: FertilizerRequirement,
    mode: FertilizationMode,
    *,
    formulated_grade: Optional[Dict[str, float]] = None,
    formulated_name: Optional[str] = None,
    fosfatado_codigo: Optional[str] = None,
    potassico_codigo: Optional[str] = None,
    nitrogenado_codigo: Optional[str] = None,
    mixed_sacks: Optional[float] = None,
) -> FertilizerResult:
    """
    Pipeline principal que a UI chama quando o usuario clica em "Calcular".

    Entradas:
    - requirement: necessidades brutas N, P2O5, K2O (kg/ha).
    - mode: MIXED | FORMULATED | INDIVIDUAL.
    - formulated_grade: dict com percentuais (ex: {"N": 5, "P2O5": 20, "K2O": 20}).
    - formulated_name: string exibida nos resultados (ex: "N 5 - P 20 - K 20").
    - mixed_sacks: apenas para modo misto. Qtde de sacos (50 kg cada).
    - fertilizantes selecionados (codigos).

    Saida:
    - FertilizerResult com produtos, alertas, faltantes.

    PROMPT:
    - Mantenha mensagens e logica identicas ao FertiCalc.
    - Erros devem retornar status="error" e message adequada.
    """

    demanda = _make_demanda(requirement)

    try:
        if mode is FertilizationMode.FORMULATED:
            if not formulated_grade:
                return FertilizerResult(
                    status="error",
                    message="Informe a grade do formulado (N, P2O5 e K2O).",
                    mode_label="Fertilizantes formulados",
                )
            nome = formulated_name or "Formulado personalizado"
            resultado = calcular_formulado(
                demanda,
                formulated_grade,
                nome,
                complemento_n=NITROGENADOS.get(nitrogenado_codigo or ""),
                complemento_p=FOSFATADOS.get(fosfatado_codigo or ""),
                complemento_k=POTASSICOS.get(potassico_codigo or ""),
            )
            mode_label = "Fertilizantes formulados"
        elif mode is FertilizationMode.INDIVIDUAL:
            resultado = calcular_individual_usuario(demanda, fosfatado_codigo, potassico_codigo, nitrogenado_codigo)
            mode_label = "Fertilizantes individuais"
        elif mode is FertilizationMode.MIXED:
            if not formulated_grade:
                return FertilizerResult(
                    status="error",
                    message="Informe a grade do formulado (N, P2O5 e K2O).",
                    mode_label="Plano misto",
                )
            sacos = mixed_sacks if mixed_sacks is not None else 0.0
            if sacos < 0:
                return FertilizerResult(
                    status="error",
                    message="Informe uma quantidade de sacos maior ou igual a zero.",
                    mode_label="Plano misto",
                )
            kg_formulado = sacos * KG_PER_SACK
            nome = formulated_name or "Formulado selecionado"
            resultado = calcular_formulado(
                demanda,
                formulated_grade,
                nome,
                complemento_n=NITROGENADOS.get(nitrogenado_codigo or ""),
                complemento_p=FOSFATADOS.get(fosfatado_codigo or ""),
                complemento_k=POTASSICOS.get(potassico_codigo or ""),
                kg_formulado_predefinido=kg_formulado,
            )
            mode_label = "Plano misto"
        else:
            return FertilizerResult(
                status="error",
                message=f"Modo de adubacao desconhecido: {mode}.",
                mode_label=mode.value,
            )
    except Exception as exc:  # noqa: BLE001
        return FertilizerResult(status="error", message=str(exc), mode_label=mode.value)

    produtos = list(resultado.produtos)
    formulados = list(resultado.formulados)
    individuais = list(resultado.individuais)
    alertas = list(resultado.alertas)
    faltantes = dict(resultado.faltantes)

    status = "ok"
    mensagem = "Calculo de fertilizantes concluido."
    if not produtos and not faltantes and not alertas:
        status = "empty"
        mensagem = "Nenhum fertilizante necessario para as necessidades informadas."

    return FertilizerResult(
        status=status,
        message=mensagem,
        produtos=produtos,
        formulados=formulados,
        individuais=individuais,
        alertas=alertas,
        faltantes=faltantes,
        mode_label=mode_label,
    )


# ---------------------------------------------------------------------------
# Formatacao opcional de saida (usada na aba resultados do FertiCalc)
# ---------------------------------------------------------------------------


def format_products(
    produtos: Iterable[Tuple[str, float]],
    *,
    area_ha: float = 0.0,
    por_area: bool = True,
    unit: str = "kg",
) -> str:
    """
    Replica a formatacao da aba Resultados (para uso opcional).

    - unit: "kg", "t" ou "sacas".
    - Se "molibdato" estiver no nome, exibe em g/ha.
    """

    def _format_value(value: float) -> str:
        if value >= 1000:
            return f"{value:.0f}"
        if value >= 100:
            return f"{value:.1f}"
        if value >= 10:
            return f"{value:.2f}"
        if value >= 1:
            return f"{value:.2f}"
        return f"{value:.3f}"

    def _convert_mass(kg_value: float, unit_local: str) -> Tuple[float, str]:
        unit_local = unit_local.lower()
        if unit_local == "kg":
            return kg_value, "kg"
        if unit_local == "t":
            return kg_value / 1000.0, "t"
        if unit_local.startswith("saca"):
            return kg_value / KG_PER_SACK, "sacas"
        return kg_value, "kg"

    def _format_quantity(kg_value: float, area: float, por_area_local: bool, unit_local: str) -> str:
        unit_label = {"kg": "KG", "t": "T", "sacas": "SC"}.get(unit_local, "KG")
        base = kg_value if por_area_local else kg_value * max(area, 0.0)
        numero, _ = _convert_mass(base, unit_local)
        sufixo = "/HA" if por_area_local else ""
        return f"{_format_value(numero)} {unit_label}{sufixo}"

    linhas: List[str] = []
    for nome, quantidade in produtos:
        kg = max(quantidade, 0.0)
        if "molibdato" in nome.lower():
            base = kg if por_area else kg * max(area_ha, 0.0)
            valor = f"{_format_value(base * 1000.0)} G{'/HA' if por_area else ''}"
        else:
            valor = _format_quantity(kg, area_ha, por_area, unit)
        linhas.append(f"{nome}: {valor.upper()}")
    return "\n\n".join(linhas) if linhas else "Nenhum fertilizante configurado."
