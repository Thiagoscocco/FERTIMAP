"""
Notebook tab focusing on soil condition classes derived from lab analyses.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..services.field_colors import color_for_culture
from ..services.kmz_loader import FieldGeometry
from ..services.soil_conditions import SoilDataError, summarize_from_metadata
from .add_fields import AddFieldsPage


class SoilConditionsPage(AddFieldsPage):
    """Display soil availability classes per talhao."""

    title = "Condicoes do solo"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    MACRO_CODES = ("P", "K", "Ca", "Mg", "S")
    OTHER_CODES = ("Zn", "Cu", "B", "Mn")

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"
        self._manual_expanded: set[int] = set()

    def _build_sidebar_content(self) -> None:
        ttk.Label(
            self.sidebar_inner,
            text="Confira as condicoes de disponibilidade dos nutrientes em cada talhao.",
            wraplength=self.SIDEBAR_WIDTH - 36,
        ).pack(fill="x", padx=(6, 2), pady=(0, 12))

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
                text="^" if expanded else "v",
                bg=color,
                fg=self._text_fg,
                font=("Segoe UI", 11, "bold"),
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
                macro_lines, other_lines, warnings = self._build_condition_groups(field)
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
                    other_frame, "Outros nutrientes", other_lines, text_kwargs
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
        return color_for_culture(field.cultivation)

    def _field_fill_color(self, base_color: str, _is_selected: bool) -> str:
        return base_color

    def _is_card_expanded(self, index: int) -> bool:
        return index in self._manual_expanded or self.selected_index == index

    def _handle_toggle_click(self, index: int) -> str:
        expanded = self._is_card_expanded(index)
        pinned = index in self._manual_expanded
        if not expanded:
            self._manual_expanded.add(index)
            self._refresh_field_cards()
        else:
            if pinned:
                self._manual_expanded.remove(index)
                if self.selected_index == index:
                    self._select_field(None)
                else:
                    self._refresh_field_cards()
            else:
                self._select_field(None)
        return "break"

    def _build_condition_groups(self, field: FieldGeometry) -> tuple[list[str], list[str], list[str]]:
        metadata = field.metadata or {}
        if metadata.get("modo") != "soil":
            return [], [], ["Voce precisa inserir uma amostra de solo para gerar condicoes."]
        try:
            summary = summarize_from_metadata(metadata)
        except SoilDataError as exc:
            return [], [], [str(exc)]

        macro_lines = [
            f"{summary.elements[code].label}: {summary.elements[code].clazz}"
            for code in self.MACRO_CODES
            if code in summary.elements
        ]
        other_lines = [
            f"{summary.elements[code].label}: {summary.elements[code].clazz}"
            for code in self.OTHER_CODES
            if code in summary.elements
        ]
        warnings = list(summary.warnings)
        return macro_lines, other_lines, warnings

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
