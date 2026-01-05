"""
Second tab focusing on crop visualization and productivity info.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..services.kmz_loader import FieldGeometry
from .add_fields import AddFieldsPage


class CultivosPage(AddFieldsPage):
    """Read-only overview of talhoes highlighting crop-specific colors."""

    title = "Cultivos"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    CROP_COLORS: dict[str, str] = {
        "soja": "#f7d154",
        "milho": "#6ec174",
        "trigo": "#f79a3b",
        "azevem": "#e2b13c",
        "aveia": "#cfc6a0",
    }
    DEFAULT_CROP_COLOR = "#d2d2d2"

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"

    def _build_sidebar_content(self) -> None:
        ttk.Label(
            self.sidebar_inner,
            text="Acompanhe os talhoes carregados e a produtividade esperada de cada cultura.",
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
            tk.Label(
                card,
                text=field.name,
                font=self.CARD_TITLE_FONT,
                **text_kwargs,
            ).pack(anchor="w")
            crop_name = field.cultivation or "Nao informado"
            tk.Label(
                card,
                text=f"Cultivo: {crop_name}",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                card,
                text=f"Area: {field.area_ha:.2f} ha",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w")
            produtividade = (
                field.productivity
                or field.metadata.get("produtividade", "")
                or "Nao informado"
            )
            tk.Label(
                card,
                text=f"Produtividade esperada: {produtividade}",
                font=self.CARD_EMPH_FONT,
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
        cultivo = (field.cultivation or "").strip().lower()
        return self.CROP_COLORS.get(cultivo, self.DEFAULT_CROP_COLOR)

    def _field_fill_color(self, base_color: str, _is_selected: bool) -> str:
        return base_color
