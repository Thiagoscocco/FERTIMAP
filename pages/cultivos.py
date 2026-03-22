from __future__ import annotations
import tkinter as tk
from tkinter import ttk

from processing.field_colors import color_for_culture
from processing.kmz_loader import FieldGeometry
from .add_fields import AddFieldsPage


class CultivosPage(AddFieldsPage):
     
    title = "Cultivos"
    CARD_TITLE_FONT = ("Bahnschrift", 11, "bold")
    CARD_BODY_FONT = ("Bahnschrift", 10)
    CARD_EMPH_FONT = ("Bahnschrift", 9, "italic")
    CARD_SECTION_FONT = ("Bahnschrift", 9, "bold")

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self._text_fg = "#1f1f1f"
        self._manual_expanded: set[int] = set()
        self._auto_expanded_index: int | None = None

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
            card.field_index = index  

            text_kwargs = {"bg": color, "fg": self._text_fg, "anchor": "w", "justify": "left"}
            wrap_width = self.SIDEBAR_WIDTH - 72
            header = tk.Frame(card, bg=color)
            header.pack(fill="x")
            tk.Label(
                header,
                text=field.name,
                font=self.CARD_TITLE_FONT,
                **text_kwargs,
            ).pack(side="left", anchor="w")
            hidden = self._is_field_hidden(field)
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
            map_label = tk.Label(
                header,
                text="M",
                bg=color,
                fg="#b03a2e" if hidden else self._text_fg,
                font=("Segoe UI", 11, "bold"),
                cursor="hand2",
                padx=6,
            )
            if hidden:
                map_label.configure(relief="solid", bd=1)
            map_label.pack(side="right")
            map_label.bind(
                "<Button-1>",
                lambda event, idx=index: self._toggle_field_hidden(idx),
            )
            crop_name = field.cultivation or "Nao informado"
            tk.Label(
                card,
                text=f"Cultivo: {crop_name}",
                font=self.CARD_BODY_FONT,
                **text_kwargs,
            ).pack(anchor="w", pady=(4, 0))
            if expanded:
                tk.Label(
                    card,
                    text="Resumo do talhao",
                    font=self.CARD_SECTION_FONT,
                    **text_kwargs,
                ).pack(anchor="w", pady=(8, 4))
                tk.Label(
                    card,
                    text=f"Area: {field.area_ha:.2f} ha",
                    font=self.CARD_BODY_FONT,
                    **text_kwargs,
                ).pack(anchor="w", pady=(0, 4))
                produtividade = self._format_productivity(
                    field.productivity or field.metadata.get("produtividade", "")
                )
                tk.Label(
                    card,
                    text=f"Produtividade esperada: {produtividade}",
                    font=self.CARD_EMPH_FONT,
                    **text_kwargs,
                ).pack(anchor="w", pady=(0, 8))

                if crop_name.strip().lower().startswith("milh"):
                    meta = field.metadata or {}
                    tk.Label(
                        card,
                        text="Parametros do cultivo",
                        font=self.CARD_SECTION_FONT,
                        **text_kwargs,
                    ).pack(anchor="w", pady=(8, 4))
                    rotacao = (meta.get("rotacao_soja") or "").strip().lower()
                    if rotacao in {"sim", "s", "yes", "true", "1"}:
                        tk.Label(
                            card,
                            text="Rotacao anual com soja: Sim",
                            font=self.CARD_BODY_FONT,
                            wraplength=wrap_width,
                            **text_kwargs,
                        ).pack(anchor="w", pady=(0, 4))
                    densidade = (meta.get("densidade_plantas_ha") or "").strip()
                    if densidade:
                        tk.Label(
                            card,
                            text=f"Densidade de plantas: {densidade} plantas/ha",
                            font=self.CARD_BODY_FONT,
                            wraplength=wrap_width,
                            **text_kwargs,
                        ).pack(anchor="w", pady=(0, 4))

                    sistema = (meta.get("sistema_cultivo") or "Convencional").strip()
                    tk.Label(
                        card,
                        text=f"Sistema de cultivo: {sistema}",
                        font=self.CARD_BODY_FONT,
                        wraplength=wrap_width,
                        **text_kwargs,
                    ).pack(anchor="w", pady=(0, 8))

                    antecedente = (meta.get("cultura_antecedente") or "").strip().lower()
                    manejo_lines: list[str] = []
                    if sistema.lower().startswith("conv"):
                        manejo_lines = [
                            "Aplicar 10 a 30 kg N/ha na semeadura.",
                            "Aplicar o restante a lanco em V4 ou V6 (40 a 60 cm).",
                            "Se chuvas intensas ou dose de N elevada, dividir em 3 aplicacoes",
                            "com intervalos de 15 a 30 dias.",
                        ]
                    elif sistema.lower().startswith("plantio"):
                        if antecedente.startswith("gra"):
                            manejo_lines.append(
                                "Aplicar 20 a 40 kg N/ha na semeadura."
                            )
                        if antecedente.startswith("leg"):
                            manejo_lines.append(
                                "Aplicar 10 a 20 kg N/ha na semeadura."
                            )
                        manejo_lines.extend(
                            [
                                "Aplicar metade da dose em V4 a V6 e a outra metade em V8 a V9.",
                                "Se chuvas intensas ou dose de N elevada, dividir em 3 aplicacoes",
                                "com intervalos de 15 a 30 dias.",
                            ]
                        )

                    if manejo_lines:
                        tk.Label(
                            card,
                            text="INFORMACOES DE ADUBACAO",
                            font=self.CARD_SECTION_FONT,
                            wraplength=wrap_width,
                            **text_kwargs,
                        ).pack(anchor="w", pady=(6, 4))
                        for line in manejo_lines:
                            tk.Label(
                                card,
                                text=line,
                                font=self.CARD_BODY_FONT,
                                wraplength=wrap_width,
                                **text_kwargs,
                            ).pack(anchor="w", pady=(0, 4))

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

    @staticmethod
    def _format_productivity(value: str | None) -> str:
        text = value or "Nao informado"
        if isinstance(text, str):
            low = text.lower()
            if text != "Nao informado" and "t/ha" not in low and "sc" not in low and "saca" not in low:
                text = f"{text} t/ha"
        return text

    def _field_color(self, field: FieldGeometry, index: int) -> str:
        return color_for_culture(field.cultivation)

    def _field_fill_color(self, base_color: str, _is_selected: bool) -> str:
        return base_color
