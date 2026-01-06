"""
Notebook tab focusing on soil condition classes derived from lab analyses.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import tkinter as tk
from tkinter import ttk

from ..services.field_colors import color_for_culture
from ..services.kmz_loader import FieldGeometry
from ..services.soil_conditions import SoilDataError, summarize_from_metadata
from .add_fields import AddFieldsPage


@dataclass(frozen=True)
class AttributeConfig:
    label: str
    meta_key: str
    min_value: float
    ideal_value: float
    max_value: float
    include_blue: bool = True
    decimals: int = 1


class SoilConditionsPage(AddFieldsPage):
    """Display soil availability classes per talhao."""

    title = "Condicoes do solo"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    SOIL_CHARACTERISTIC_CODES = ("ARGILA", "MO", "CTC")
    MACRO_CODES = ("P", "K", "Ca", "Mg", "S")
    MICRO_CODES = ("Zn", "Cu", "B", "Mn")
    ATTRIBUTE_CONFIGS: dict[str, AttributeConfig] = {
        "argila": AttributeConfig("Argila", "argila", 10.0, 30.0, 40.0, decimals=0),
        "mo": AttributeConfig("M.O", "mo", 0.3, 3.0, 60.0),
        "ctc": AttributeConfig("CTC", "ctc", 0.8, 30.0, 40.0),
        "p": AttributeConfig("Fosforo", "p", 0.0, 30.0, 70.0),
        "k": AttributeConfig("Potassio", "k", 15.0, 100.0, 220.0, decimals=0),
        "s": AttributeConfig("Enxofre", "s", 0.5, 6.0, 6.0, include_blue=False),
        "cu": AttributeConfig("Cobre", "cu", 0.1, 0.8, 0.8, include_blue=False, decimals=2),
        "zn": AttributeConfig("Zinco", "zn", 0.2, 0.8, 0.8, include_blue=False, decimals=2),
        "b": AttributeConfig("Boro", "b", 0.0, 0.4, 0.4, include_blue=False, decimals=2),
        "mn": AttributeConfig("Manganes", "mn", 1.0, 6.0, 6.0, include_blue=False),
        "ph": AttributeConfig("pH", "ph", 4.0, 5.6, 8.0),
    }
    ATTRIBUTE_ORDER = ("argila", "mo", "ctc", "p", "k", "s", "cu", "zn", "b", "mn", "ph")
    COLOR_RED = (187, 45, 33)
    COLOR_GREEN = (64, 168, 96)
    COLOR_BLUE = (46, 109, 196)
    COLOR_PINK = "#f7b4cf"

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"
        self._manual_expanded: set[int] = set()
        self._auto_expanded_index: int | None = None
        self._attribute_label_to_key = {
            self.ATTRIBUTE_CONFIGS[key].label: key for key in self.ATTRIBUTE_ORDER
        }
        default_key = self.ATTRIBUTE_ORDER[0]
        self._selected_attribute_key: str | None = default_key
        default_label = self.ATTRIBUTE_CONFIGS[default_key].label
        self._attribute_var = tk.StringVar(value=default_label)

    def _build_sidebar_content(self) -> None:
        ttk.Label(
            self.sidebar_inner,
            text="Confira as condicoes de disponibilidade dos nutrientes em cada talhao.",
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
        self._manual_expanded = {
            idx for idx in self._manual_expanded if 0 <= idx < len(self.fields)
        }
        if self._auto_expanded_index is not None and not (
            0 <= self._auto_expanded_index < len(self.fields)
        ):
            self._auto_expanded_index = None
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

            if expanded:
                characteristics, macro_lines, micro_lines, warnings = self._build_condition_groups(field)
                features_frame = tk.Frame(card, bg=color)
                features_frame.pack(fill="x")
                self._render_condition_column(
                    features_frame,
                    "Caracteristicas do solo (argila, m.o e ctc)",
                    characteristics,
                    text_kwargs,
                )
                columns = tk.Frame(card, bg=color)
                columns.pack(fill="x", pady=(6, 0))
                macro_frame = tk.Frame(columns, bg=color)
                macro_frame.pack(side="left", expand=True, fill="both", padx=(0, 6))
                other_frame = tk.Frame(columns, bg=color)
                other_frame.pack(side="left", expand=True, fill="both")
                self._render_condition_column(
                    macro_frame, "Macronutrientes", macro_lines, text_kwargs
                )
                self._render_condition_column(
                    other_frame, "Micronutrientes", micro_lines, text_kwargs
                )

                for message in warnings:
                    tk.Label(
                        card,
                        text=message,
                        font=self.CARD_BODY_FONT,
                        **text_kwargs,
                    ).pack(anchor="w", pady=(4, 0))

            self._bind_card_selection(card, index)

        self._highlight_selected_card()

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
        config = self._get_current_attribute_config()
        if config is None:
            return color_for_culture(field.cultivation)
        color, _ = self._attribute_display(field, config)
        return color

    def _field_fill_color(self, base_color: str, _is_selected: bool) -> str:
        if self._get_current_attribute_config() is None:
            return base_color
        return base_color

    def _field_label_text(self, field: FieldGeometry) -> str:
        config = self._get_current_attribute_config()
        if config is None:
            return super()._field_label_text(field)
        _, label = self._attribute_display(field, config)
        return label

    def _select_field(self, index: int | None, _sync_tree: bool = False) -> None:
        self._auto_expanded_index = index
        super()._select_field(index, _sync_tree)
        self._refresh_field_cards()

    def _is_card_expanded(self, index: int) -> bool:
        return index in self._manual_expanded or self._auto_expanded_index == index

    def _handle_toggle_click(self, index: int) -> str:
        expanded = self._is_card_expanded(index)
        pinned = index in self._manual_expanded
        if not expanded:
            self._manual_expanded.add(index)
            self._refresh_field_cards()
        else:
            if pinned:
                self._manual_expanded.remove(index)
                if self._auto_expanded_index == index:
                    self._auto_expanded_index = None
                if self.selected_index == index:
                    self._select_field(None)
                else:
                    self._refresh_field_cards()
            else:
                self._select_field(None)
        return "break"

    def _render_canvas_overlays(self, width: int, height: int) -> None:
        super()._render_canvas_overlays(width, height)
        if not self.canvas:
            return
        config = self._get_current_attribute_config()
        if config is None:
            return
        self._draw_attribute_scale(width, height, config)

    def _build_attribute_viewer(self) -> None:
        container = ttk.LabelFrame(
            self.sidebar_inner,
            text="Visualizacao dos atributos",
            padding=(10, 8),
        )
        container.pack(fill="x", padx=(6, 2), pady=(0, 12))
        ttk.Label(
            container,
            text="Escolha o atributo que deseja visualizar no mapa.",
            wraplength=self.SIDEBAR_WIDTH - 60,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 6))
        values = [self.ATTRIBUTE_CONFIGS[key].label for key in self.ATTRIBUTE_ORDER]
        combobox = ttk.Combobox(
            container,
            state="readonly",
            values=values,
            textvariable=self._attribute_var,
        )
        combobox.pack(fill="x")
        combobox.bind("<<ComboboxSelected>>", self._on_attribute_change)

    def _on_attribute_change(self, _event=None) -> None:
        label = self._attribute_var.get()
        self._selected_attribute_key = self._attribute_label_to_key.get(label)
        self._render_fields()

    def _get_current_attribute_config(self) -> AttributeConfig | None:
        if not self._selected_attribute_key:
            return None
        return self.ATTRIBUTE_CONFIGS.get(self._selected_attribute_key)

    def _attribute_display(
        self, field: FieldGeometry, config: AttributeConfig
    ) -> tuple[str, str]:
        metadata = field.metadata or {}
        raw_value = metadata.get(config.meta_key)
        parsed = self._parse_attribute_value(raw_value)
        if parsed is None:
            return self.COLOR_PINK, "Sem informacoes"
        color = self._attribute_color_for_value(parsed, config)
        return color, self._format_attribute_value(parsed, config.decimals)

    @staticmethod
    def _parse_attribute_value(raw_value: object) -> float | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        text = str(raw_value).strip()
        if not text:
            return None
        normalized = text.replace(",", ".")
        cleaned = re.sub(r"[^0-9\\.\\-]", "", normalized)
        if cleaned in {"", "-", ".", "-.", ".-"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _format_attribute_value(value: float, decimals: int) -> str:
        decimals = max(0, min(decimals, 3))
        fmt = f"{{:.{decimals}f}}"
        text = fmt.format(value)
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _attribute_color_for_value(self, value: float, config: AttributeConfig) -> str:
        min_v = config.min_value
        ideal = config.ideal_value
        max_v = config.max_value
        if not config.include_blue or max_v <= ideal:
            ratio = self._normalize_ratio(value, min_v, max_v)
            rgb = self._interpolate_color(self.COLOR_RED, self.COLOR_GREEN, ratio)
            return self._rgb_to_hex(rgb)
        if value <= ideal:
            ratio = self._normalize_ratio(value, min_v, ideal)
            rgb = self._interpolate_color(self.COLOR_RED, self.COLOR_GREEN, ratio)
            return self._rgb_to_hex(rgb)
        ratio = self._normalize_ratio(value, ideal, max_v)
        rgb = self._interpolate_color(self.COLOR_GREEN, self.COLOR_BLUE, ratio)
        return self._rgb_to_hex(rgb)

    @staticmethod
    def _normalize_ratio(value: float, start: float, end: float) -> float:
        if end <= start:
            return 1.0
        ratio = (value - start) / (end - start)
        return max(0.0, min(1.0, ratio))

    @staticmethod
    def _interpolate_color(
        color_a: tuple[int, int, int], color_b: tuple[int, int, int], ratio: float
    ) -> tuple[int, int, int]:
        ratio = max(0.0, min(1.0, ratio))
        r = int(color_a[0] + (color_b[0] - color_a[0]) * ratio)
        g = int(color_a[1] + (color_b[1] - color_a[1]) * ratio)
        b = int(color_a[2] + (color_b[2] - color_a[2]) * ratio)
        return (r, g, b)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        r, g, b = (max(0, min(255, channel)) for channel in rgb)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw_attribute_scale(self, canvas_width: int, canvas_height: int, config: AttributeConfig) -> None:
        if not self.canvas:
            return
        padding = 18
        box_width = 240
        box_height = 90
        if canvas_width < box_width + padding * 2 or canvas_height < box_height + padding * 2:
            return
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
            text=f"Escala {config.label}",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fill="#2c3e50",
            tags=("overlay",),
        )
        gradient_margin = 14
        grad_x0 = x0 + gradient_margin
        grad_x1 = x1 - gradient_margin
        grad_y0 = y0 + 36
        grad_y1 = grad_y0 + 18
        steps = max(2, int(grad_x1 - grad_x0))
        span = config.max_value - config.min_value
        step_value = span / (steps - 1) if steps > 1 else 0
        current_value = config.min_value
        for step in range(steps):
            x = grad_x0 + step
            color = self._attribute_color_for_value(current_value, config)
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

    def _build_condition_groups(self, field: FieldGeometry) -> tuple[list[str], list[str], list[str], list[str]]:
        metadata = field.metadata or {}
        if metadata.get("modo") != "soil":
            return [], [], [], ["Voce precisa inserir uma amostra de solo para gerar condicoes."]
        try:
            summary = summarize_from_metadata(metadata)
        except SoilDataError as exc:
            return [], [], [], [str(exc)]

        def _lines(codes: tuple[str, ...]) -> list[str]:
            return [
                f"{summary.elements[code].label}: {summary.elements[code].clazz}"
                for code in codes
                if code in summary.elements
            ]

        characteristic_lines = _lines(self.SOIL_CHARACTERISTIC_CODES)
        macro_lines = _lines(self.MACRO_CODES)
        micro_lines = _lines(self.MICRO_CODES)
        warnings = list(summary.warnings)
        return characteristic_lines, macro_lines, micro_lines, warnings

    def _render_condition_column(
        self,
        container: tk.Frame,
        title: str,
        lines: list[str],
        text_kwargs: dict,
    ) -> None:
        tk.Label(
            container,
            text=title,
            font=self.CARD_EMPH_FONT,
            **text_kwargs,
        ).pack(anchor="w")
        if not lines:
            tk.Label(
                container,
                text="Sem dados",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(2, 0))
            return
        for line in lines:
            tk.Label(
                container,
                text=line,
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(2, 0))
