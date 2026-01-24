"""
Tab showing per-field liming configuration and recommendations.
"""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, ttk

from ..services.kmz_loader import FieldGeometry
from ..services.liming import (
    LimingError,
    LimingMethod,
    ManagementScenario,
    recommend_liming,
)
from .add_fields import AddFieldsPage


class CalagemPage(AddFieldsPage):
    """Per-field liming workflow."""

    title = "Calagem"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    PH_OPTIONS = ("5.5", "6.0", "6.5")
    SCENARIO_OPTIONS = [
        ("Convencional (graos)", ManagementScenario.CONVENCIONAL_GRAOS),
        ("Implantacao de plantio direto", ManagementScenario.IMPLANTACAO_PD_GRAOS),
        ("Plantio direto consolidado", ManagementScenario.PD_CONSOLIDADO_GRAOS),
        ("Pastagem natural", ManagementScenario.CAMPO_NATURAL),
    ]
    METRIC_OPTIONS = (
        ("Toneladas/ha", "dose_ha"),
        ("Toneladas totais", "dose_total"),
        ("Metodo de aplicacao", "application"),
    )
    UNIT_OPTIONS = (
        ("Toneladas (t)", "t"),
        ("Quilos (kg)", "kg"),
        ("Sacas de 60 kg", "sc"),
    )
    UNIT_FACTORS = {"t": 1.0, "kg": 1000.0, "sc": 1000.0 / 60.0}
    UNIT_PER_HA_LABELS = {
        "t": "t/ha",
        "kg": "kg/ha",
        "sc": "sacas (60 kg)/ha",
    }
    UNIT_TOTAL_LABELS = {
        "t": "t",
        "kg": "kg",
        "sc": "sacas (60 kg)",
    }
    CHEMISTRY_FIELD_LABELS = [
        ("sat_bases", "% saturacao por bases (V%)"),
        ("sat_al", "% saturacao por Al (m%)"),
        ("ctc", "CTC pH7,0 (cmolc/dm3)"),
        ("mo", "Materia organica (%)"),
    ]
    COLOR_LOW = (64, 168, 96)
    COLOR_HIGH = (187, 45, 33)
    COLOR_NO_DATA = "#d9d9d9"

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"
        self._manual_expanded: set[int] = set()
        self._auto_expanded_index: int | None = None
        self._metric_var = tk.StringVar(value=self.METRIC_OPTIONS[0][0])
        self._metric_var.trace_add("write", self._on_metric_change)
        self._unit_var = tk.StringVar(value=self.UNIT_OPTIONS[0][0])
        self._unit_var.trace_add("write", self._on_unit_change)
        self._dose_range: tuple[float, float] | None = None
        self._total_dose: float = 0.0

    def build(self) -> None:
        super().build()
        self._init_unit_selector()

    def _build_sidebar_content(self) -> None:
        ttk.Label(
            self.sidebar_inner,
            text="Configure a calagem de cada talhao e gere as doses por hectare.",
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

    def _refresh_field_cards(self) -> None:
        self._update_calagem_stats()
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
            result_available = bool(field.metadata and field.metadata.get("_calagem_result"))
            if result_available:
                edit_btn = ttk.Button(
                    header,
                    text="Editar",
                    command=lambda idx=index: self._show_field_editor(idx),
                    bootstyle="secondary-outline",
                )
                edit_btn.pack(side="right", padx=(0, 4))
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

    def _update_calagem_stats(self) -> None:
        values: list[float] = []
        total = 0.0
        for field in self.fields:
            metadata = field.metadata or {}
            result = metadata.get("_calagem_result")
            if not result:
                continue
            dose_ha = result.get("dose_ha")
            dose_total = result.get("dose_total")
            if dose_ha is not None:
                try:
                    values.append(float(dose_ha))
                except (TypeError, ValueError):
                    pass
            if dose_total is not None:
                try:
                    total += float(dose_total)
                except (TypeError, ValueError):
                    pass
        self._dose_range = (min(values), max(values)) if values else None
        self._total_dose = total

    def _build_attribute_viewer(self) -> None:
        container = ttk.LabelFrame(
            self.sidebar_inner,
            text="Visualizacao dos atributos",
            padding=(12, 8),
        )
        container.pack(fill="x", padx=(6, 2), pady=(0, 12))
        ttk.Label(
            container,
            text="Escolha qual informacao de calagem deseja visualizar nos talhoes.",
            wraplength=self.SIDEBAR_WIDTH - 60,
        ).pack(anchor="w")
        ttk.Combobox(
            container,
            state="readonly",
            values=[label for label, _ in self.METRIC_OPTIONS],
            textvariable=self._metric_var,
        ).pack(fill="x", pady=(10, 0))

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

    def _render_form_section(self, card, field: FieldGeometry, index: int, text_kwargs) -> None:
        state = self._get_form_state(field)
        result = field.metadata.get("_calagem_result")
        editing = self._is_edit_mode(field) or not result

        if editing:
            form = tk.Frame(card, bg=card["bg"])
            form.pack(fill="x", pady=(6, 0))
            inputs = ttk.Frame(form)
            inputs.pack(fill="x")

            form_fields: list[
                tuple[str, Callable[[ttk.Frame], ttk.Widget], int]
            ] = []
            scenario_var = tk.StringVar(value=state["scenario"])
            self._bind_var(state, "scenario", scenario_var)
            scenario_labels = [label for label, _ in self.SCENARIO_OPTIONS]
            form_fields.append(
                (
                    "Sistema de manejo",
                    lambda master, var=scenario_var: ttk.Combobox(
                        master,
                        state="readonly",
                        values=scenario_labels,
                        textvariable=var,
                        width=28,
                    ),
                    2,
                )
            )

            ph_var = tk.StringVar(value=state["ph_target"])
            self._bind_var(state, "ph_target", ph_var)
            form_fields.append(
                (
                    "pH alvo",
                    lambda master, var=ph_var: ttk.Combobox(
                        master,
                        state="readonly",
                        values=self.PH_OPTIONS,
                        textvariable=var,
                        width=10,
                    ),
                    1,
                )
            )

            prnt_var = tk.StringVar(value=state["prnt"])
            self._bind_var(state, "prnt", prnt_var)
            form_fields.append(
                (
                    "PRNT do calcario (%)",
                    lambda master, var=prnt_var: ttk.Entry(master, textvariable=var, width=12),
                    1,
                )
            )

            self._render_form_fields(inputs, form_fields)

            missing_fields = self._missing_chemistry_fields(field, state)
            if missing_fields:
                helper = ttk.LabelFrame(
                    form,
                    text="Dados do solo necessarios",
                    padding=(10, 6),
                )
                helper.pack(fill="x", pady=(8, 0))
                ttk.Label(
                    helper,
                    text="Preencha os dados ausentes para permitir o calculo da calagem.",
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
                text="Calcular calagem",
                command=lambda idx=index: self._handle_calculate(idx),
                bootstyle="primary",
            ).pack(fill="x", pady=(8, 0))
        else:
            self._render_edit_button(card, index)

        self._render_result_section(card, result, text_kwargs)

    def _bind_var(self, state: dict, key: str, var: tk.StringVar) -> None:
        def _update(*_):
            state[key] = var.get()

        var.trace_add("write", _update)

    def _render_form_fields(
        self,
        container: ttk.Frame,
        fields: list[tuple[str, Callable[[ttk.Frame], ttk.Widget], int]],
        columns: int = 2,
    ) -> None:
        """Render labeled widgets in a compact multi-column layout."""

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

    def _render_result_section(self, card, result, text_kwargs) -> None:
        output_frame = tk.Frame(card, bg=card["bg"])
        output_frame.pack(fill="x", pady=(10, 0))
        if not result:
            return
        tk.Label(
            output_frame,
            text=f"Dose: {self._format_per_ha_value(result['dose_ha'])}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        tk.Label(
            output_frame,
            text=f"Dose total: {self._format_total_value(result['dose_total'])}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        tk.Label(
            output_frame,
            text=f"Metodo: {result['method']}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        tk.Label(
            output_frame,
            text=f"Aplicacao: {result['application']}",
            font=self.CARD_BODY_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        for warning in result.get("warnings", []):
            tk.Label(
                output_frame,
                text=f"- {warning}",
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
        return self._dose_color(field)

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
        storage = meta.setdefault(
            "_calagem_form",
            {},
        )
        defaults = {
            "scenario": storage.get("scenario") or self.SCENARIO_OPTIONS[0][0],
            "ph_target": storage.get("ph_target") or "6.0",
            "prnt": storage.get("prnt") or "80",
            "sat_bases": storage.get("sat_bases") or meta.get("sat_bases", ""),
            "sat_al": storage.get("sat_al") or meta.get("sat_al", ""),
            "ctc": storage.get("ctc") or meta.get("ctc", ""),
            "mo": storage.get("mo") or meta.get("mo", ""),
        }
        storage.update(defaults)
        return storage

    def _handle_calculate(self, index: int) -> None:
        if index < 0 or index >= len(self.fields):
            return
        field = self.fields[index]
        state = self._get_form_state(field)
        try:
            result = self._compute_field_liming(field, state)
        except (ValueError, LimingError) as exc:
            messagebox.showerror("Calagem", str(exc))
            return

        field.metadata["_calagem_result"] = result
        self._set_edit_mode(field, False)
        self._manual_expanded.discard(index)
        self._focus_next_pending_field(index)
        self._refresh_field_cards()
        self._render_fields()

    def _compute_field_liming(self, field: FieldGeometry, state: dict[str, str]) -> dict:
        meta = field.metadata or {}
        scenario_label = state["scenario"]
        scenario = self._resolve_scenario(scenario_label)

        ph_alvo = self._require_float(state["ph_target"], "pH alvo")
        prnt = self._require_float(state["prnt"], "PRNT")
        v_source = meta.get("sat_bases") or state.get("sat_bases")
        m_source = meta.get("sat_al") or state.get("sat_al")
        ctc_source = meta.get("ctc") or state.get("ctc")
        mo_source = meta.get("mo") or state.get("mo")

        v_percent = self._require_float(v_source, "% saturacao por bases")
        m_percent = self._require_float(m_source, "% saturacao por Al")
        ctc = self._require_float(ctc_source, "CTC pH7,0 (cmolc/dm3)")
        mo_percent = self._require_float(mo_source, "Materia organica (%)")

        ph = self._require_float(meta.get("ph"), "pH em agua (laudo)")
        smp = self._require_float(meta.get("indice_smp"), "Indice SMP")
        al = self._require_float(meta.get("al"), "Al trocavel")
        ca = self._optional_float(meta.get("ca"))
        mg = self._optional_float(meta.get("mg"))

        recommendation = recommend_liming(
            scenario=scenario,
            ph_agua=ph,
            smp=smp,
            v_percent=v_percent,
            m_percent=m_percent,
            ctc_ph7=ctc,
            mo_percent=mo_percent,
            al_cmolc=al,
            prnt_percent=prnt,
            ph_referencia=ph_alvo,
            ca_cmolc=ca,
            mg_cmolc=mg,
        )
        total = recommendation.dose_produto_t_ha * field.area_ha
        return {
            "dose_ha": recommendation.dose_produto_t_ha,
            "dose_total": round(total, 3),
            "method": recommendation.metodo_usado.value,
            "application": recommendation.modo_aplicacao,
            "warnings": recommendation.avisos,
        }

    def _resolve_scenario(self, label: str) -> ManagementScenario:
        for option_label, scenario in self.SCENARIO_OPTIONS:
            if option_label == label:
                return scenario
        raise ValueError(f"Cenario desconhecido: {label}")

    @staticmethod
    def _require_float(value: str | float | None, label: str) -> float:
        try:
            if value is None:
                raise ValueError
            if isinstance(value, (int, float)):
                return float(value)
            cleaned = value.replace("%", "").replace(",", ".").strip()
            if not cleaned:
                raise ValueError
            return float(cleaned)
        except ValueError:
            raise ValueError(f"Informe um valor numerico valido para {label}.") from None

    @staticmethod
    def _optional_float(value: str | float | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = value.replace("%", "").replace(",", ".").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _render_fields(self) -> None:
        self._update_calagem_stats()
        super()._render_fields()
        if not getattr(self, "canvas", None):
            return
        for index, field in enumerate(self.fields):
            label = self._canvas_label(field)
            for item in self.canvas.find_withtag(f"field-{index}"):
                if "label" in self.canvas.gettags(item):
                    self.canvas.itemconfigure(item, text=label)

    def _canvas_label(self, field: FieldGeometry) -> str:
        return self._metric_display(field)

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
        if not meta.get("_calagem_result"):
            return True
        return bool(meta.get("_calagem_editing", True))

    def _set_edit_mode(self, field: FieldGeometry, value: bool) -> None:
        if field.metadata is None:
            field.metadata = {}
        field.metadata["_calagem_editing"] = value

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
            if not meta.get("_calagem_result"):
                return idx
        return None

    def _current_metric_key(self) -> str:
        selected = self._metric_var.get()
        for label, key in self.METRIC_OPTIONS:
            if label == selected:
                return key
        return self.METRIC_OPTIONS[0][1]

    def _metric_display(self, field: FieldGeometry) -> str:
        result = field.metadata.get("_calagem_result") if field.metadata else None
        if not result:
            return "Aguardando calculo"
        metric_key = self._current_metric_key()
        if metric_key == "dose_ha":
            return self._format_per_ha_value(result["dose_ha"])
        if metric_key == "dose_total":
            return self._format_total_value(result["dose_total"])
        if metric_key == "application":
            return result.get("application", "Sem dado")
        value = result.get(metric_key)
        return str(value) if value is not None else "Sem dado"

    def _current_unit_key(self) -> str:
        label = self._unit_var.get()
        for option_label, key in self.UNIT_OPTIONS:
            if option_label == label:
                return key
        return self.UNIT_OPTIONS[0][1]

    def _format_per_ha_value(self, value: float | None) -> str:
        converted = self._convert_value(value or 0.0)
        unit_label = self.UNIT_PER_HA_LABELS[self._current_unit_key()]
        return f"{self._format_number(converted)} {unit_label}"

    def _format_total_value(self, value: float | None, uppercase: bool = False) -> str:
        converted = self._convert_value(value or 0.0)
        unit_label = self.UNIT_TOTAL_LABELS[self._current_unit_key()]
        if uppercase:
            unit_label = unit_label.upper() if unit_label != "t" else "t"
        return f"{self._format_number(converted)} {unit_label}"

    def _convert_value(self, value: float) -> float:
        factor = self.UNIT_FACTORS[self._current_unit_key()]
        return value * factor

    @staticmethod
    def _format_number(value: float) -> str:
        text = f"{value:.2f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _missing_chemistry_fields(
        self, field: FieldGeometry, state: dict[str, str]
    ) -> list[tuple[str, str]]:
        meta = field.metadata or {}
        missing: list[tuple[str, str]] = []
        for key, label in self.CHEMISTRY_FIELD_LABELS:
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

    def _render_canvas_overlays(self, width: int, height: int) -> None:
        super()._render_canvas_overlays(width, height)
        if not getattr(self, "canvas", None):
            return
        scale_bbox = None
        if self._dose_range:
            scale_bbox = self._draw_dose_scale(width, height)
        self._draw_total_box(width, height, scale_bbox)

    def _draw_dose_scale(self, canvas_width: int, canvas_height: int) -> tuple[float, float, float, float] | None:
        if not self.canvas or not self._dose_range:
            return None
        padding = 18
        box_width = 240
        box_height = 94
        if canvas_width < box_width + padding * 2 or canvas_height < box_height + padding * 2:
            return None
        min_v, max_v = self._dose_range
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
        unit_label = self.UNIT_PER_HA_LABELS[self._current_unit_key()]
        self.canvas.create_text(
            x0 + 12,
            y0 + 16,
            text=f"Escala de doses ({unit_label})",
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
        box_width = 200
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
        self.canvas.create_text(
            x0 + 12,
            y0 + 18,
            text="QUANTIDADE TOTAL",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fill="#2c3e50",
            tags=("overlay",),
        )
        self.canvas.create_text(
            x0 + 12,
            y0 + 44,
            text=self._format_total_value(self._total_dose, uppercase=True),
            anchor="w",
            font=("Segoe UI", 11),
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


    def _dose_color(self, field: FieldGeometry) -> str:
        metadata = field.metadata or {}
        result = metadata.get("_calagem_result")
        if not result:
            return self.COLOR_NO_DATA
        dose = result.get("dose_ha")
        if dose is None:
            return self.COLOR_NO_DATA
        try:
            value = float(dose)
        except (TypeError, ValueError):
            return self.COLOR_NO_DATA
        return self._color_for_value(value)

    def _color_for_value(self, value: float) -> str:
        if not self._dose_range:
            return self._rgb_to_hex(self.COLOR_LOW)
        min_v, max_v = self._dose_range
        if max_v <= min_v:
            ratio = 0.0
        else:
            ratio = (value - min_v) / (max_v - min_v)
        ratio = max(0.0, min(1.0, ratio))
        rgb = self._interpolate_color(self.COLOR_LOW, self.COLOR_HIGH, ratio)
        return self._rgb_to_hex(rgb)

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
