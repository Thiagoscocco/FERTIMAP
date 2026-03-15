"""
Per-field fertilization workflow.
"""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, ttk

from ..services.fertilization import (
    FOSFATADOS,
    NITROGENADOS,
    POTASSICOS,
    FOSFATADOS_CHOICES,
    NITROGENADOS_CHOICES,
    POTASSICOS_CHOICES,
    FertilizationMode,
    FertilizerRequirement,
    IndividualSelection,
    calculate_fertilizers,
    format_formulated_name,
    obter_fosfatado_por_nome,
    obter_potassico_por_nome,
    obter_nitrogenado_por_nome,
)
from ..services.fertilization_cultures import (
    CultureRequirement,
    CulturaAntecedente,
    UsoForrageira,
    requirement_from_summary,
)
from ..services.kmz_loader import FieldGeometry
from ..services.soil_conditions import SoilDataError, summarize_from_metadata
from .add_fields import AddFieldsPage


class AdubacaoPage(AddFieldsPage):
    """Per-field fertilization configuration and recommendations."""

    title = "Adubacao"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    MODE_OPTIONS = [
        ("Individual", FertilizationMode.INDIVIDUAL),
        ("Formulado", FertilizationMode.FORMULATED),
        ("Misto", FertilizationMode.MIXED),
    ]
    INDIVIDUAL_SOURCE_OPTIONS = [
        ("Automatico", IndividualSelection.SOFTWARE),
        ("Usuario", IndividualSelection.USER),
    ]
    ANTECEDENTE_OPTIONS = ("Indiferente", "Graminea", "Leguminosa")
    USO_FORRAGEIRA_OPTIONS = ("Pastejo", "Corte")
    CULTIVO_OPTIONS = ("1", "2")
    METRIC_BASE_LABELS = ("Nitrogenio", "Fosforo", "Potassio", "Outros")
    UNIT_OPTIONS = (
        ("Quilos (kg)", "kg"),
        ("Toneladas (t)", "t"),
        ("Sacas de 50 kg", "sc"),
    )
    UNIT_PER_HA_LABELS = {
        "kg": "kg/ha",
        "t": "t/ha",
        "sc": "sacas (50 kg)/ha",
    }
    UNIT_TOTAL_LABELS = {
        "kg": "kg",
        "t": "t",
        "sc": "sacas (50 kg)",
    }
    COLOR_LOW = (64, 168, 96)
    COLOR_HIGH = (187, 45, 33)
    COLOR_NO_DATA = "#d9d9d9"

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"
        self._manual_expanded: set[int] = set()
        self._auto_expanded_index: int | None = None
        self._metric_var = tk.StringVar(value=self.METRIC_BASE_LABELS[0])
        self._metric_var.trace_add("write", self._on_metric_change)
        self._unit_var = tk.StringVar(value=self.UNIT_OPTIONS[0][0])
        self._unit_var.trace_add("write", self._on_unit_change)
        self._metric_options: list[str] = list(self.METRIC_BASE_LABELS)
        self._metric_map: dict[str, tuple[str, str | None]] = {}
        self._metric_range: tuple[float, float] | None = None
        self._total_metric: float = 0.0

    def build(self) -> None:
        super().build()
        self._init_unit_selector()

    def _build_sidebar_content(self) -> None:
        ttk.Label(
            self.sidebar_inner,
            text="Configure a adubacao de cada talhao e gere as doses por hectare.",
            wraplength=self.SIDEBAR_WIDTH - 36,
        ).pack(fill="x", padx=(6, 2), pady=(0, 12))

        self._build_attribute_viewer()

        self.field_cards_frame = ttk.Frame(self.sidebar_inner)
        self.field_cards_frame.pack(fill="both", expand=True, padx=(6, 2))
        self._refresh_field_cards()

    def refresh(self) -> None:
        self.status_var.set("")
        self._update_area_labels()
        self._refresh_field_cards()
        self._render_fields()

    def _build_attribute_viewer(self) -> None:
        container = ttk.LabelFrame(
            self.sidebar_inner,
            text="Visualizacao dos atributos",
            padding=(12, 8),
        )
        container.pack(fill="x", padx=(6, 2), pady=(0, 12))
        ttk.Label(
            container,
            text="Escolha a informacao que deseja visualizar nos talhoes.",
            wraplength=self.SIDEBAR_WIDTH - 60,
        ).pack(anchor="w")
        self._metric_combo = ttk.Combobox(
            container,
            state="readonly",
            values=self._metric_options,
            textvariable=self._metric_var,
        )
        self._metric_combo.pack(fill="x", pady=(10, 0))

    def _on_metric_change(self, *_args) -> None:
        if not hasattr(self, "field_cards_frame"):
            return
        self._refresh_field_cards()
        self._render_fields()

    def _on_unit_change(self, *_args) -> None:
        if not hasattr(self, "field_cards_frame"):
            return
        self._refresh_field_cards()
        self._render_fields()

    def _init_unit_selector(self) -> None:
        bottom = getattr(self, "bottom_info", None)
        if bottom is None:
            return
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=0)
        container = tk.Frame(bottom, background=self.CANVAS_BG)
        container.grid(row=0, column=1, sticky="e")
        tk.Label(
            container,
            text="Unidade",
            background=self.CANVAS_BG,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="e")
        ttk.Combobox(
            container,
            state="readonly",
            values=[label for label, _ in self.UNIT_OPTIONS],
            textvariable=self._unit_var,
            width=18,
        ).pack(anchor="e", pady=(2, 0))

    def _refresh_field_cards(self) -> None:
        self._update_metric_options()
        self._update_metric_stats()
        self._manual_expanded = {
            idx for idx in self._manual_expanded if 0 <= idx < len(self.fields)
        }
        if self._auto_expanded_index is not None and not (
            0 <= self._auto_expanded_index < len(self.fields)
        ):
            self._auto_expanded_index = None
        if (
            self.fields
            and not self._manual_expanded
            and self._auto_expanded_index is None
        ):
            if self.selected_index is not None and 0 <= self.selected_index < len(self.fields):
                self._auto_expanded_index = self.selected_index
            else:
                self._auto_expanded_index = 0

        for child in self.field_cards_frame.winfo_children():
            child.destroy()
        if not self.fields:
            ttk.Label(
                self.field_cards_frame,
                text="Nenhum talhao para exibir. Adicione-os na aba 'Adicionar talhoes'.",
                anchor="w",
                wraplength=self.SIDEBAR_WIDTH - 48,
            ).pack(fill="x", pady=8)
            return

        for index, field in enumerate(self.fields):
            color = self._field_color(field, index)
            expanded = self._is_card_expanded(index)
            card = tk.Frame(
                self.field_cards_frame,
                bg=color,
                highlightbackground="#b6b6b6",
                highlightcolor="#2c3e50",
                highlightthickness=3 if index == self.selected_index else 1,
                bd=0,
                padx=12,
                pady=10,
            )
            card.pack(fill="x", pady=4)
            card.field_index = index  # type: ignore[attr-defined]

            text_kwargs = {"bg": color, "fg": self._text_fg, "anchor": "w", "justify": "left"}
            header = tk.Frame(card, bg=color)
            header.pack(fill="x")
            tk.Label(
                header,
                text=field.name,
                font=self.CARD_TITLE_FONT,
                **text_kwargs,
            ).pack(side="left", anchor="w")
            toggle_label = tk.Label(
                header,
                text="-" if expanded else "+",
                bg=color,
                fg=self._text_fg,
                font=("Segoe UI", 12, "bold"),
                cursor="hand2",
                padx=6,
            )
            toggle_label.pack(side="right")
            toggle_label.bind(
                "<Button-1>",
                lambda event, idx=index: self._handle_toggle_click(idx),
            )
            crop_name = field.cultivation or "Nao informado"
            tk.Label(
                card,
                text=f"Cultivo: {crop_name}",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(2, 4))
            tk.Label(
                card,
                text=f"{self._metric_var.get()}: {self._metric_display(field)}",
                font=self.CARD_EMPH_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(0, 4))

            if expanded:
                self._render_form_section(card, field, index, text_kwargs)
            self._bind_card_selection(card, index)

        self._highlight_selected_card()
    def _render_form_section(self, card, field: FieldGeometry, index: int, text_kwargs) -> None:
        state = self._get_form_state(field)
        result = field.metadata.get("_adubacao_result")
        editing = self._is_edit_mode(field) or not result

        if editing:
            form = tk.Frame(card, bg=card["bg"])
            form.pack(fill="x", pady=(6, 0))
            inputs = ttk.Frame(form)
            inputs.pack(fill="x")

            form_fields: list[
                tuple[str, Callable[[ttk.Frame], ttk.Widget], int]
            ] = []
            mode_var = tk.StringVar(value=state["mode"])
            self._bind_var(state, "mode", mode_var, refresh=True)
            mode_labels = [label for label, _ in self.MODE_OPTIONS]
            form_fields.append(
                (
                    "Tipo de recomendacao",
                    lambda master, var=mode_var: ttk.Combobox(
                        master,
                        state="readonly",
                        values=mode_labels,
                        textvariable=var,
                        width=20,
                    ),
                    2,
                )
            )

            self._render_form_fields(inputs, form_fields)
            self._render_culture_section(form, field, state)
            self._render_mode_specific_form(form, state)

            missing_fields = self._missing_soil_fields(field, state)
            if missing_fields:
                helper = ttk.LabelFrame(
                    form,
                    text="Dados do solo necessarios",
                    padding=(10, 6),
                )
                helper.pack(fill="x", pady=(8, 0))
                ttk.Label(
                    helper,
                    text="Preencha os dados ausentes para permitir o calculo da adubacao.",
                    wraplength=self.SIDEBAR_WIDTH - 80,
                ).pack(anchor="w", pady=(0, 4))
                extra_rows = ttk.Frame(helper)
                extra_rows.pack(fill="x")
                extra_fields: list[tuple[str, Callable[[ttk.Frame], ttk.Widget], int]] = []
                for key, label in missing_fields:
                    var = tk.StringVar(value=state.get(key, ""))
                    self._bind_var(state, key, var)
                    extra_fields.append(
                        (
                            label,
                            lambda master, v=var: ttk.Entry(master, textvariable=v, width=12),
                            1,
                        )
                    )
                self._render_form_fields(extra_rows, extra_fields)

            ttk.Button(
                form,
                text="Calcular adubacao",
                command=lambda idx=index: self._handle_calculate(idx),
                bootstyle="primary",
            ).pack(fill="x", pady=(8, 0))

        self._render_result_section(card, result, text_kwargs)
        if not editing:
            self._render_edit_button(card, index)

    def _render_culture_section(self, parent, field: FieldGeometry, state: dict) -> None:
        meta = field.metadata or {}
        if meta.get("modo") == "need":
            return
        frame = ttk.LabelFrame(parent, text="Parametros da cultura", padding=(10, 6))
        frame.pack(fill="x", pady=(8, 0))
        cultura = (field.cultivation or "").strip() or "Nao informado"
        cultura_lower = cultura.lower()
        produtividade = meta.get("produtividade") or field.productivity or "Nao informado"
        if isinstance(produtividade, str):
            low = produtividade.lower()
            if "t/ha" not in low and "sc" not in low and "saca" not in low:
                produtividade = f"{produtividade} t/ha"
        cultivo_safra = meta.get("cultivo_safra", "1")
        if str(cultivo_safra).strip() in {"1", "1º", "1o"}:
            cultivo_label = "1º"
        elif str(cultivo_safra).strip() in {"2", "2º", "2o"}:
            cultivo_label = "2º"
        else:
            cultivo_label = str(cultivo_safra)
        antecedente = meta.get("cultura_antecedente", "Indiferente")
        massa_seca = meta.get("producao_cultura_antecedente", "")

        tk.Label(
            frame,
            text=f"Cultivo: {cultura}",
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=f"Cultivo: {cultivo_label}",
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=f"Produtividade esperada: {produtividade}",
            anchor="w",
        ).pack(anchor="w")
        if cultura_lower != "soja":
            tk.Label(
                frame,
                text=f"Cultura antecedente: {antecedente}",
                anchor="w",
            ).pack(anchor="w")
            if massa_seca:
                tk.Label(
                    frame,
                    text=f"Massa seca antecedente: {massa_seca} t/ha",
                    anchor="w",
                ).pack(anchor="w")

        if "gramineas" in cultura_lower:
            rows = ttk.Frame(frame)
            rows.pack(fill="x", pady=(6, 0))
            uso_var = tk.StringVar(value=state.get("uso_forrageira", "Pastejo"))
            self._bind_var(state, "uso_forrageira", uso_var)
            self._render_form_fields(
                rows,
                [
                    (
                        "Uso da forrageira",
                        lambda master, var=uso_var: ttk.Combobox(
                            master,
                            state="readonly",
                            values=self.USO_FORRAGEIRA_OPTIONS,
                            textvariable=var,
                            width=12,
                        ),
                        1,
                    ),
                    (
                        "Produtividade MS (t/ha)",
                        lambda master: ttk.Entry(
                            master,
                            textvariable=self._ensure_var(state, "produtividade_ms_t_ha"),
                            width=12,
                        ),
                        1,
                    ),
                ],
            )

    def _render_mode_specific_form(self, parent, state: dict) -> None:
        mode = self._resolve_mode(state.get("mode"))
        frame = ttk.LabelFrame(parent, text="Configuracao da adubacao", padding=(10, 6))
        frame.pack(fill="x", pady=(8, 0))
        rows = ttk.Frame(frame)
        rows.pack(fill="x")

        fields: list[tuple[str, Callable[[ttk.Frame], ttk.Widget], int]] = []
        if mode is FertilizationMode.INDIVIDUAL:
            source_var = tk.StringVar(value=state.get("individual_source", "Automatico"))
            self._bind_var(state, "individual_source", source_var, refresh=True)
            fields.append(
                (
                    "Selecao dos fertilizantes",
                    lambda master, var=source_var: ttk.Combobox(
                        master,
                        state="readonly",
                        values=[label for label, _ in self.INDIVIDUAL_SOURCE_OPTIONS],
                        textvariable=var,
                        width=16,
                    ),
                    2,
                )
            )
            self._render_form_fields(rows, fields)

            if self._resolve_individual_source(state.get("individual_source")) is IndividualSelection.USER:
                self._render_fertilizer_choices(frame, state)
            return

        if mode in {FertilizationMode.FORMULATED, FertilizationMode.MIXED}:
            fields = [
                (
                    "Nome do formulado",
                    lambda master: ttk.Entry(
                        master,
                        textvariable=self._ensure_var(state, "formulado_nome"),
                        width=18,
                    ),
                    2,
                ),
                (
                    "N (%)",
                    lambda master: ttk.Entry(
                        master,
                        textvariable=self._ensure_var(state, "formulado_n"),
                        width=8,
                    ),
                    1,
                ),
                (
                    "P2O5 (%)",
                    lambda master: ttk.Entry(
                        master,
                        textvariable=self._ensure_var(state, "formulado_p"),
                        width=8,
                    ),
                    1,
                ),
                (
                    "K2O (%)",
                    lambda master: ttk.Entry(
                        master,
                        textvariable=self._ensure_var(state, "formulado_k"),
                        width=8,
                    ),
                    1,
                ),
            ]
            if mode is FertilizationMode.MIXED:
                fields.append(
                    (
                        "Sacos (50 kg)",
                        lambda master: ttk.Entry(
                            master,
                            textvariable=self._ensure_var(state, "misto_sacos"),
                            width=10,
                        ),
                        1,
                    )
                )
            self._render_form_fields(rows, fields)
            self._render_fertilizer_choices(frame, state, allow_optional=True)
    def _render_fertilizer_choices(
        self, parent, state: dict, allow_optional: bool = False
    ) -> None:
        choices = ttk.Frame(parent)
        choices.pack(fill="x", pady=(6, 0))
        form_fields: list[tuple[str, Callable[[ttk.Frame], ttk.Widget], int]] = []

        fos_default = state.get("fosfatado", "")
        pot_default = state.get("potassico", "")
        nit_default = state.get("nitrogenado", "")

        def _combo(values, key, default):
            var = tk.StringVar(value=default)
            self._bind_var(state, key, var)
            return lambda master: ttk.Combobox(
                master,
                state="readonly",
                values=values,
                textvariable=var,
                width=24,
            )

        fos_values = FOSFATADOS_CHOICES
        pot_values = POTASSICOS_CHOICES
        nit_values = NITROGENADOS_CHOICES
        if allow_optional:
            fos_values = ("",) + fos_values
            pot_values = ("",) + pot_values
            nit_values = ("",) + nit_values

        form_fields.extend(
            [
                ("Fosfatado", _combo(fos_values, "fosfatado", fos_default), 1),
                ("Potassico", _combo(pot_values, "potassico", pot_default), 1),
                ("Nitrogenado", _combo(nit_values, "nitrogenado", nit_default), 1),
            ]
        )
        self._render_form_fields(choices, form_fields)

    def _render_result_section(self, card, result, text_kwargs) -> None:
        output_frame = tk.Frame(card, bg=card["bg"])
        output_frame.pack(fill="x", pady=(10, 0))
        if not result:
            return
        req = result.get("requirement", {})
        tk.Label(
            output_frame,
            text=f"N: {self._format_per_ha_value(req.get('N'))}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        tk.Label(
            output_frame,
            text=f"P2O5: {self._format_per_ha_value(req.get('P2O5'))}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        tk.Label(
            output_frame,
            text=f"K2O: {self._format_per_ha_value(req.get('K2O'))}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        if req.get("S", 0) or req.get("Mo", 0):
            tk.Label(
                output_frame,
                text=f"Outros: {self._format_per_ha_value(req.get('S', 0) + req.get('Mo', 0))}",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w")
        if result.get("produtos"):
            tk.Label(
                output_frame,
                text="Fertilizantes:",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(6, 0))
            fert_text_kwargs = dict(text_kwargs)
            fert_text_kwargs["fg"] = "#4f5b66"
            for nome, quantidade in result.get("produtos", []):
                tk.Label(
                    output_frame,
                    text=f"- {nome}: {self._format_per_ha_value(quantidade)}",
                    font=self.CARD_BODY_FONT,
                    **fert_text_kwargs,
                ).pack(anchor="w")
        for warning in result.get("alertas", []):
            tk.Label(
                output_frame,
                text=f"- {warning}",
                font=self.CARD_EMPH_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(2, 0))
        for nutriente, faltante in result.get("faltantes", {}).items():
            tk.Label(
                output_frame,
                text=f"Faltante {nutriente}: {self._format_per_ha_value(faltante)}",
                font=self.CARD_EMPH_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(2, 0))

    def _render_edit_button(self, card, index: int) -> None:
        actions = ttk.Frame(card)
        actions.pack(fill="x", pady=(6, 0))
        ttk.Button(
            actions,
            text="Editar dados",
            command=lambda idx=index: self._enable_edit_mode(idx),
            bootstyle="secondary",
        ).pack(fill="x")

    def _highlight_selected_card(self) -> None:
        for card in self.field_cards_frame.winfo_children():
            idx = getattr(card, "field_index", None)
            if idx is None:
                continue
            selected = idx == self.selected_index
            outline = "#2c3e50" if selected else "#b6b6b6"
            thickness = 3 if selected else 1
            card.configure(highlightbackground=outline, highlightthickness=thickness)

    def _field_color(self, field: FieldGeometry, index: int) -> str:
        return self._metric_color(field)

    def _field_fill_color(self, base_color: str, is_selected: bool) -> str:
        if base_color == self.COLOR_NO_DATA or is_selected:
            return base_color
        return self._lighten(base_color, 0.35)

    def _select_field(self, index: int | None, _sync_tree: bool = False) -> None:
        self._auto_expanded_index = index
        super()._select_field(index, _sync_tree)
        self._refresh_field_cards()

    def _is_card_expanded(self, index: int) -> bool:
        return index in self._manual_expanded or self._auto_expanded_index == index

    def _handle_toggle_click(self, index: int) -> str:
        expanded = self._is_card_expanded(index)
        if not expanded:
            self._manual_expanded.add(index)
            self._auto_expanded_index = index
            self._refresh_field_cards()
        else:
            if index in self._manual_expanded:
                self._manual_expanded.remove(index)
                if self._auto_expanded_index == index:
                    self._auto_expanded_index = None
                self._refresh_field_cards()
            else:
                self._auto_expanded_index = None
                self._select_field(None)
        return "break"

    def _get_form_state(self, field: FieldGeometry) -> dict[str, str]:
        meta = field.metadata or {}
        storage = meta.setdefault("_adubacao_form", {})
        source_label = storage.get("individual_source") or self.INDIVIDUAL_SOURCE_OPTIONS[0][0]
        if isinstance(source_label, str) and source_label.strip().lower() == "software":
            source_label = "Automatico"
        defaults = {
            "mode": storage.get("mode") or self.MODE_OPTIONS[0][0],
            "individual_source": source_label,
            "formulado_n": storage.get("formulado_n") or "0",
            "formulado_p": storage.get("formulado_p") or "0",
            "formulado_k": storage.get("formulado_k") or "0",
            "formulado_nome": storage.get("formulado_nome") or "",
            "misto_sacos": storage.get("misto_sacos") or "0",
            "fosfatado": storage.get("fosfatado") or "",
            "potassico": storage.get("potassico") or "",
            "nitrogenado": storage.get("nitrogenado") or "",
            "produtividade_ms_t_ha": storage.get("produtividade_ms_t_ha") or "",
            "massa_seca_antecedente": storage.get("massa_seca_antecedente") or "",
        }
        storage.update(defaults)
        return storage

    def _handle_calculate(self, index: int) -> None:
        if index < 0 or index >= len(self.fields):
            return
        field = self.fields[index]
        state = self._get_form_state(field)
        try:
            requirement, notes = self._build_requirement(field, state)
            result = self._compute_fertilization(field, state, requirement)
        except (ValueError, SoilDataError) as exc:
            messagebox.showerror("Adubacao", str(exc))
            return

        field.metadata["_adubacao_result"] = {
            "status": result.status,
            "message": result.message,
            "produtos": result.produtos,
            "formulados": result.formulados,
            "individuais": result.individuais,
            "alertas": result.alertas,
            "faltantes": result.faltantes,
            "mode_label": result.mode_label,
            "requirement": {
                "N": requirement.nitrogen_kg_ha,
                "P2O5": requirement.p2o5_kg_ha,
                "K2O": requirement.k2o_kg_ha,
                "S": requirement.s_kg_ha,
                "Mo": requirement.mo_kg_ha,
            },
            "notes": list(notes),
        }
        self._set_edit_mode(field, False)
        self._manual_expanded.discard(index)
        self._focus_next_pending_field(index)
        self._refresh_field_cards()
        self._render_fields()
    def _build_requirement(
        self, field: FieldGeometry, state: dict[str, str]
    ) -> tuple[FertilizerRequirement, tuple[str, ...]]:
        meta = field.metadata or {}
        if meta.get("modo") == "need":
            n = self._require_float(meta.get("n"), "N")
            p = self._require_float(meta.get("p"), "P2O5")
            k = self._require_float(meta.get("k"), "K2O")
            return FertilizerRequirement(n, p, k), ()

        merged = dict(meta)
        for key in ("argila", "ctc", "mo", "p", "k", "s", "ph"):
            if state.get(key):
                merged[key] = state[key]

        summary = summarize_from_metadata(merged)
        cultura = field.cultivation or ""
        if not cultura.strip():
            raise ValueError("Informe o cultivo do talhao para calcular a adubacao.")
        produtividade_t_ha = self._parse_productivity(meta.get("produtividade", ""))
        if produtividade_t_ha is None:
            raise ValueError("Informe a produtividade esperada (t/ha).")

        antecedente_label = meta.get("cultura_antecedente")
        antecedente = self._normalize_antecedente(antecedente_label)
        teor_mo = summary.elements["MO"].value
        teor_s = summary.elements["S"].value
        massa_seca = self._optional_float(meta.get("producao_cultura_antecedente"))
        if antecedente_label and antecedente_label.lower().startswith("ind"):
            massa_seca = None
        densidade = None
        cultivo = int(self._optional_float(meta.get("cultivo_safra")) or 1)
        uso_forrageira = state.get("uso_forrageira") or "Pastejo"
        produtividade_ms = self._optional_float(state.get("produtividade_ms_t_ha"))
        ph_agua = self._optional_float(merged.get("ph"))

        cultura_req = requirement_from_summary(
            cultura,
            summary,
            produtividade_t_ha=produtividade_t_ha,
            cultura_antecedente=antecedente,
            teor_mo=teor_mo,
            teor_s_mg_dm3=teor_s,
            massa_seca_antecedente_t_ha=massa_seca,
            densidade_plantas_ha=densidade,
            cultivo=cultivo,
            uso_forrageira=uso_forrageira,  # type: ignore[arg-type]
            produtividade_ms_t_ha=produtividade_ms,
            ph_agua=ph_agua,
        )
        requirement = FertilizerRequirement(
            cultura_req.n_kg_ha,
            cultura_req.p2o5_kg_ha,
            cultura_req.k2o_kg_ha,
            cultura_req.s_kg_ha,
            cultura_req.mo_kg_ha,
        )
        return requirement, cultura_req.notes

    def _compute_fertilization(
        self, field: FieldGeometry, state: dict[str, str], requirement: FertilizerRequirement
    ):
        mode = self._resolve_mode(state.get("mode"))
        fos = self._fertilizante_codigo(state.get("fosfatado"), obter_fosfatado_por_nome, FOSFATADOS)
        pot = self._fertilizante_codigo(state.get("potassico"), obter_potassico_por_nome, POTASSICOS)
        nit = self._fertilizante_codigo(state.get("nitrogenado"), obter_nitrogenado_por_nome, NITROGENADOS)

        if mode is FertilizationMode.INDIVIDUAL:
            selection = self._resolve_individual_source(state.get("individual_source"))
            return calculate_fertilizers(
                requirement,
                mode,
                fosfatado_codigo=fos,
                potassico_codigo=pot,
                nitrogenado_codigo=nit,
                individual_selection=selection,
            )

        if mode in {FertilizationMode.FORMULATED, FertilizationMode.MIXED}:
            grade = self._parse_formulated_grade(state)
            nome = state.get("formulado_nome") or format_formulated_name(grade)
            sacos = None
            if mode is FertilizationMode.MIXED:
                sacos = self._require_float(state.get("misto_sacos"), "Sacos (50 kg)")
            return calculate_fertilizers(
                requirement,
                mode,
                formulated_grade=grade,
                formulated_name=nome,
                fosfatado_codigo=fos,
                potassico_codigo=pot,
                nitrogenado_codigo=nit,
                mixed_sacks=sacos,
            )

        raise ValueError("Modo de adubacao invalido.")

    def _render_fields(self) -> None:
        self._update_metric_stats()
        super()._render_fields()
        if not getattr(self, "canvas", None):
            return
        for index, field in enumerate(self.fields):
            label = self._canvas_label(field)
            for item in self.canvas.find_withtag(f"field-{index}"):
                if "label" in self.canvas.gettags(item):
                    self.canvas.itemconfigure(item, text=label)

    def _canvas_label(self, field: FieldGeometry) -> str:
        return f"{field.name}\n{self._metric_var.get()}: {self._metric_display(field)}"

    def _enable_edit_mode(self, index: int) -> None:
        if index < 0 or index >= len(self.fields):
            return
        field = self.fields[index]
        self._manual_expanded.add(index)
        self._set_edit_mode(field, True)
        self._auto_expanded_index = index
        self._refresh_field_cards()

    def _is_edit_mode(self, field: FieldGeometry) -> bool:
        meta = field.metadata or {}
        if not meta.get("_adubacao_result"):
            return True
        return bool(meta.get("_adubacao_editing", True))

    def _set_edit_mode(self, field: FieldGeometry, value: bool) -> None:
        if field.metadata is None:
            field.metadata = {}
        field.metadata["_adubacao_editing"] = value

    def _show_field_editor(self, index: int) -> None:
        self._manual_expanded.add(index)
        self._enable_edit_mode(index)

    def _focus_next_pending_field(self, current_index: int) -> None:
        next_index = self._next_pending_index(current_index)
        if next_index is None:
            self._auto_expanded_index = current_index
        else:
            self._auto_expanded_index = next_index

    def _next_pending_index(self, start: int) -> int | None:
        total = len(self.fields)
        if total <= 1:
            return None
        for offset in range(1, total + 1):
            idx = (start + offset) % total
            meta = self.fields[idx].metadata or {}
            if not meta.get("_adubacao_result"):
                return idx
        return None

    def _update_metric_options(self) -> None:
        products: set[str] = set()
        for field in self.fields:
            meta = field.metadata or {}
            result = meta.get("_adubacao_result") or {}
            for nome, _ in result.get("produtos", []):
                products.add(nome)
        options = list(self.METRIC_BASE_LABELS) + sorted(products)
        self._metric_options = options
        self._metric_map = {
            "Nitrogenio": ("nutrient", "N"),
            "Fosforo": ("nutrient", "P2O5"),
            "Potassio": ("nutrient", "K2O"),
            "Outros": ("other", None),
        }
        for nome in products:
            self._metric_map[nome] = ("product", nome)

        if self._metric_var.get() not in options:
            self._metric_var.set(self.METRIC_BASE_LABELS[0])
        if getattr(self, "_metric_combo", None):
            self._metric_combo.configure(values=options)

    def _current_metric_key(self) -> tuple[str, str | None]:
        return self._metric_map.get(
            self._metric_var.get(), ("nutrient", "N")
        )

    def _metric_display(self, field: FieldGeometry) -> str:
        value = self._metric_value(field)
        if value is None:
            return "Aguardando calculo"
        return self._format_per_ha_value(value)

    def _metric_value(self, field: FieldGeometry) -> float | None:
        meta = field.metadata or {}
        result = meta.get("_adubacao_result")
        if not result:
            return None
        key_type, key = self._current_metric_key()
        if key_type == "nutrient" and key:
            return float(result.get("requirement", {}).get(key, 0.0))
        if key_type == "other":
            req = result.get("requirement", {})
            return float(req.get("S", 0.0)) + float(req.get("Mo", 0.0))
        if key_type == "product" and key:
            for nome, quantidade in result.get("produtos", []):
                if nome == key:
                    return float(quantidade)
            return 0.0
        return 0.0

    def _update_metric_stats(self) -> None:
        values: list[float] = []
        total = 0.0
        for field in self.fields:
            value = self._metric_value(field)
            if value is None:
                continue
            values.append(value)
            total += value * field.area_ha
        self._metric_range = (min(values), max(values)) if values else None
        self._total_metric = total

    def _render_canvas_overlays(self, width: int, height: int) -> None:
        super()._render_canvas_overlays(width, height)
        if not getattr(self, "canvas", None):
            return
        scale_bbox = None
        if self._metric_range:
            scale_bbox = self._draw_metric_scale(width, height)
        self._draw_total_box(width, height, scale_bbox)

    def _draw_metric_scale(
        self, canvas_width: int, canvas_height: int
    ) -> tuple[float, float, float, float] | None:
        if not self.canvas or not self._metric_range:
            return None
        padding = 18
        unit_label = self.UNIT_PER_HA_LABELS[self._current_unit_key()]
        box_width = 260
        if "sacas" in unit_label.lower():
            box_width = 320
        box_height = 94
        if canvas_width < box_width + padding * 2 or canvas_height < box_height + padding * 2:
            return None
        min_v, max_v = self._metric_range
        x1 = canvas_width - padding
        y1 = canvas_height - padding
        x0 = x1 - box_width
        y0 = y1 - box_height
        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill="#fefefe",
            outline="#c2cbd2",
            width=1.5,
            tags=("overlay",),
        )
        self.canvas.create_text(
            x0 + 12,
            y0 + 16,
            text=f"Escala ({unit_label})",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fill="#2c3e50",
            tags=("overlay",),
        )
        gradient_margin = 14
        grad_x0 = x0 + gradient_margin
        grad_x1 = x1 - gradient_margin
        grad_y0 = y0 + 38
        grad_y1 = grad_y0 + 18
        steps = max(2, int(grad_x1 - grad_x0))
        span = max(0.0, max_v - min_v)
        step_value = span / (steps - 1) if steps > 1 else 0.0
        current_value = min_v
        for step in range(steps):
            x = grad_x0 + step
            color = self._color_for_value(current_value)
            self.canvas.create_line(
                x,
                grad_y0,
                x,
                grad_y1,
                fill=color,
                width=1,
                tags=("overlay",),
            )
            current_value += step_value
        self.canvas.create_rectangle(
            grad_x0,
            grad_y0,
            grad_x1,
            grad_y1,
            outline="#6c7a89",
            width=1,
            tags=("overlay",),
        )
        label_y = grad_y1 + 16
        self.canvas.create_text(
            grad_x0,
            label_y,
            text=f"{self._format_per_ha_value(min_v)} (Menor)",
            anchor="w",
            font=("Segoe UI", 8),
            fill="#2c3e50",
            tags=("overlay",),
        )
        self.canvas.create_text(
            grad_x1,
            label_y,
            text=f"(Maior) {self._format_per_ha_value(max_v)}",
            anchor="e",
            font=("Segoe UI", 8),
            fill="#2c3e50",
            tags=("overlay",),
        )
        return (x0, y0, x1, y1)

    def _draw_total_box(
        self,
        canvas_width: int,
        canvas_height: int,
        scale_bbox: tuple[float, float, float, float] | None,
    ) -> None:
        if not self.canvas:
            return
        padding = 18
        box_width = 220
        box_height = 80
        y1 = canvas_height - padding
        y0 = y1 - box_height
        x0 = padding
        x1 = x0 + box_width
        if y0 < padding:
            y0 = padding
            y1 = y0 + box_height
        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill="#fefefe",
            outline="#c2cbd2",
            width=1.5,
            tags=("overlay",),
        )
        total_label = self.UNIT_TOTAL_LABELS[self._current_unit_key()].upper()
        self.canvas.create_text(
            x0 + 12,
            y0 + 18,
            text=f"TOTAL ({total_label})",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fill="#2c3e50",
            tags=("overlay",),
        )
        self.canvas.create_text(
            x0 + 12,
            y0 + 44,
            text=self._format_total_value(self._total_metric),
            anchor="w",
            font=("Segoe UI", 11),
            fill="#2c3e50",
            tags=("overlay",),
        )

    def _metric_color(self, field: FieldGeometry) -> str:
        value = self._metric_value(field)
        if value is None:
            return self.COLOR_NO_DATA
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return self.COLOR_NO_DATA
        return self._color_for_value(numeric)

    def _color_for_value(self, value: float) -> str:
        if not self._metric_range:
            return self._rgb_to_hex(self.COLOR_LOW)
        min_v, max_v = self._metric_range
        if max_v <= min_v:
            ratio = 0.0
        else:
            ratio = (value - min_v) / (max_v - min_v)
        ratio = max(0.0, min(1.0, ratio))
        rgb = self._interpolate_color(self.COLOR_LOW, self.COLOR_HIGH, ratio)
        return self._rgb_to_hex(rgb)

    def _missing_soil_fields(self, field: FieldGeometry, state: dict[str, str]) -> list[tuple[str, str]]:
        meta = field.metadata or {}
        if meta.get("modo") == "need":
            return []
        missing: list[tuple[str, str]] = []
        labels = {
            "argila": "Argila (%)",
            "ctc": "CTC pH7,0 (cmolc/dm3)",
            "mo": "Materia organica (%)",
            "p": "P (mg/dm3)",
            "k": "K (mg/dm3)",
            "s": "S (mg/dm3)",
            "ph": "pH em agua",
        }
        for key, label in labels.items():
            if self._has_value(meta.get(key)) or self._has_value(state.get(key)):
                continue
            missing.append((key, label))
        return missing
    @staticmethod
    def _has_value(value) -> bool:
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return True
        return bool(str(value).strip())

    def _bind_var(self, state: dict, key: str, var: tk.StringVar, refresh: bool = False) -> None:
        def _update(*_):
            state[key] = var.get()
            if refresh:
                self._refresh_field_cards()
        var.trace_add("write", _update)

    def _ensure_var(self, state: dict, key: str) -> tk.StringVar:
        var = tk.StringVar(value=state.get(key, ""))
        self._bind_var(state, key, var)
        return var

    def _render_form_fields(
        self,
        container: ttk.Frame,
        fields: list[tuple[str, Callable[[ttk.Frame], ttk.Widget], int]],
        columns: int = 2,
    ) -> None:
        row_frame: ttk.Frame | None = None
        used_columns = 0

        def _new_row() -> None:
            nonlocal row_frame, used_columns
            row_frame = ttk.Frame(container)
            row_frame.pack(fill="x", pady=(4, 0))
            used_columns = 0

        for label, widget_factory, span in fields:
            span = max(1, min(columns, span))
            if span == columns:
                _new_row()
                assert row_frame is not None
                cell = ttk.Frame(row_frame)
                cell.pack(fill="x")
                widget = widget_factory(cell)
                self._pack_form_widget(cell, label, widget)
                row_frame = None
                used_columns = 0
                continue

            if row_frame is None:
                _new_row()
            if used_columns + span > columns:
                _new_row()
            assert row_frame is not None
            pad_left = 0 if used_columns == 0 else 8
            cell = ttk.Frame(row_frame)
            cell.pack(
                side="left",
                expand=True,
                fill="x",
                padx=(pad_left, 0),
            )
            widget = widget_factory(cell)
            self._pack_form_widget(cell, label, widget)
            used_columns += span
            if used_columns >= columns:
                row_frame = None
                used_columns = 0

    @staticmethod
    def _pack_form_widget(parent: ttk.Frame, label: str, widget: ttk.Widget) -> None:
        ttk.Label(parent, text=label).pack(anchor="w")
        widget.pack(fill="x", pady=(2, 0))

    @staticmethod
    def _format_value(value: float | None) -> str:
        if value is None:
            return "0"
        text = f"{float(value):.2f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _current_unit_key(self) -> str:
        label = self._unit_var.get()
        for option_label, key in self.UNIT_OPTIONS:
            if option_label == label:
                return key
        return self.UNIT_OPTIONS[0][1]

    def _convert_value(self, value_kg: float) -> float:
        unit = self._current_unit_key()
        if unit == "t":
            return value_kg / 1000.0
        if unit == "sc":
            return value_kg / 50.0
        return value_kg

    def _format_per_ha_value(self, value_kg_ha: float | None) -> str:
        converted = self._convert_value(float(value_kg_ha or 0.0))
        unit_label = self.UNIT_PER_HA_LABELS[self._current_unit_key()]
        return f"{self._format_value(converted)} {unit_label}"

    def _format_total_value(self, total_kg: float | None) -> str:
        converted = self._convert_value(float(total_kg or 0.0))
        unit_label = self.UNIT_TOTAL_LABELS[self._current_unit_key()]
        return f"{self._format_value(converted)} {unit_label}"

    @staticmethod
    def _parse_productivity(value: object) -> float | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        cleaned = text.replace(",", ".")
        number = ""
        for ch in cleaned:
            if ch.isdigit() or ch == "." or ch == "-":
                number += ch
        try:
            base = float(number)
        except ValueError:
            return None
        if "sc" in cleaned or "saca" in cleaned:
            return (base * 60.0) / 1000.0
        if "kg" in cleaned:
            return base / 1000.0
        return base

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        num = AdubacaoPage._optional_float(value)
        if num is None:
            return None
        return int(num)

    @staticmethod
    def _require_float(value: object, label: str) -> float:
        num = AdubacaoPage._optional_float(value)
        if num is None:
            raise ValueError(f"Informe um valor numerico valido para {label}.")
        return num

    @staticmethod
    def _normalize_antecedente(value: str | None) -> CulturaAntecedente:
        if not value:
            return "Graminea"
        norm = value.strip().lower()
        if norm.startswith("leg"):
            return "Leguminosa"
        if norm.startswith("gra"):
            return "Graminea"
        if norm.startswith("con"):
            return "Consorcio"
        return "Graminea"

    @staticmethod
    def _resolve_mode(label: str | None) -> FertilizationMode:
        if not label:
            return FertilizationMode.INDIVIDUAL
        for text, mode in AdubacaoPage.MODE_OPTIONS:
            if text == label:
                return mode
        return FertilizationMode.INDIVIDUAL

    @staticmethod
    def _resolve_individual_source(label: str | None) -> IndividualSelection:
        if not label:
            return IndividualSelection.SOFTWARE
        if label.strip().lower() == "software":
            return IndividualSelection.SOFTWARE
        for text, mode in AdubacaoPage.INDIVIDUAL_SOURCE_OPTIONS:
            if text == label:
                return mode
        return IndividualSelection.SOFTWARE

    @staticmethod
    def _fertilizante_codigo(
        nome: str | None, finder, catalog: dict[str, object]
    ) -> str | None:
        if not nome:
            return None
        fert = finder(nome)
        if fert is None:
            return None
        return getattr(fert, "codigo", None)

    @staticmethod
    def _parse_formulated_grade(state: dict[str, str]) -> dict[str, float]:
        n = AdubacaoPage._require_float(state.get("formulado_n"), "N (%)")
        p = AdubacaoPage._require_float(state.get("formulado_p"), "P2O5 (%)")
        k = AdubacaoPage._require_float(state.get("formulado_k"), "K2O (%)")
        return {"N": n, "P2O5": p, "K2O": k}

    @staticmethod
    def _interpolate_color(
        start: tuple[int, int, int], end: tuple[int, int, int], ratio: float
    ) -> tuple[int, int, int]:
        ratio = max(0.0, min(1.0, ratio))
        r = int(start[0] + (end[0] - start[0]) * ratio)
        g = int(start[1] + (end[1] - start[1]) * ratio)
        b = int(start[2] + (end[2] - start[2]) * ratio)
        return (r, g, b)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        r, g, b = (max(0, min(255, channel)) for channel in rgb)
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
