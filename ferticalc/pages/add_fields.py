"""
First tab: UI to add and visualize talhoes as a navigable map.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..services.kmz_loader import FieldGeometry, KMZLoader
from .base_page import BasePage


FIELD_FORM_DEFAULTS = {
    "nome": "TESTE 1",
    "municipio": "Nao informado",
    "cultivo": "Soja",
    "cultivo_safra": "1",
    "produtividade": "3",
    "cultura_antecedente": "",
    "producao_cultura_antecedente": "",
    "argila": "13%",
    "ph": "4.7",
    "indice_smp": "6.7",
    "p": "2.6",
    "k": "21",
    "mo": "0.6",
    "al": "0.6",
    "ca": "0.3",
    "mg": "0.2",
    "h_al": "2.0",
    "ctc": "2.5",
    "sat_bases": "22",
    "sat_al": "51.7",
    "ca_mg": "1.5",
    "ca_k": "6",
    "mg_k": "3.7",
    "s": "2.8",
    "zn": "0.3",
    "cu": "0.5",
    "b": "0.1",
    "mn": "4",
    "densidade_plantas_ha": "65000",
    "ajuste_n_rendimento": "Nao",
    "rotacao_soja": "Nao",
    "sistema_cultivo": "Convencional",
}

NEED_FORM_DEFAULTS = {
    "nome": "Necessidade teste",
    "municipio": "Nao informado",
    "cultivo": "Soja",
    "cultivo_safra": "1",
    "produtividade": "3",
    "cultura_antecedente": "",
    "producao_cultura_antecedente": "",
    "argila": "13%",
    "ph": "4.7",
    "indice_smp": "6.7",
    "al": "0.6",
    "ca": "0.3",
    "mg": "0.2",
    "h_al": "2.0",
    "ctc": "2.5",
    "mo": "0.6",
    "sat_bases": "22",
    "sat_al": "51.7",
    "n": "100",
    "p": "160",
    "k": "160",
    "densidade_plantas_ha": "65000",
    "ajuste_n_rendimento": "Nao",
    "rotacao_soja": "Nao",
    "sistema_cultivo": "Convencional",
}

SOIL_ANALYSIS_FIELDS = [
    ("argila", "Argila"),
    ("ph", "pH"),
    ("indice_smp", "Indice SMP"),
    ("p", "P"),
    ("k", "K"),
    ("mo", "M.O"),
    ("al", "Al"),
    ("ca", "Ca"),
    ("mg", "Mg"),
    ("h_al", "H + Al"),
    ("ctc", "CTC"),
    ("sat_bases", "% Sat Bases"),
    ("sat_al", "% Sat Al"),
    ("ca_mg", "Ca/Mg"),
    ("ca_k", "Ca/K"),
    ("mg_k", "Mg/K"),
    ("s", "S"),
    ("zn", "Zn"),
    ("cu", "Cu"),
    ("b", "B"),
    ("mn", "Mn"),
]
SOIL_ANALYSIS_KEYS = [key for key, _ in SOIL_ANALYSIS_FIELDS]

# Validation helper: prefilled soil samples for testing (easy to remove).
SOIL_SAMPLE_OPTIONS = (
    "Analise 1",
    "Analise 2",
    "Analise 3",
    "Analise 4",
    "JOSE 1",
    "JOSE 2",
    "JOSE 3",
)
SOIL_SAMPLE_VALUES = {
    "Analise 1": {
        "argila": "13%",
        "ph": "5.5",
        "indice_smp": "6.8",
        "k": "44",
        "p": "7.3",
        "mo": "1.4",
        "al": "0",
        "ca": "1,1",
        "mg": "0.5",
        "h_al": "1.7",
        "ctc": "3.42",
        "sat_bases": "50",
        "sat_al": "0",
        "ca_mg": "2.2",
        "ca_k": "10",
        "mg_k": "4.4",
        "s": "5.2",
        "zn": "1.2",
        "cu": "0.2",
        "b": "0.2",
        "mn": "5",
    },
    "Analise 2": {
        "argila": "17%",
        "ph": "5.2",
        "indice_smp": "6.5",
        "p": "12",
        "k": "29",
        "mo": "1.5",
        "al": "0.2",
        "ca": "0.7",
        "mg": "0.3",
        "h_al": "2.5",
        "ctc": "3.59",
        "sat_bases": "30",
        "sat_al": "15.4",
        "ca_mg": "2.3",
        "ca_k": "9",
        "mg_k": "3.5",
        "s": "6.7",
        "zn": "1.3",
        "cu": "0.2",
        "b": "0.2",
        "mn": "14",
    },
    "Analise 3": {
        "argila": "15%",
        "ph": "5.3",
        "indice_smp": "6.6",
        "p": "5.7",
        "k": "78",
        "mo": "2.2",
        "al": "0.1",
        "ca": "1.2",
        "mg": "0.7",
        "h_al": "2.2",
        "ctc": "4.31",
        "sat_bases": "49",
        "sat_al": "4.5",
        "ca_mg": "1.7",
        "ca_k": "6",
        "mg_k": "3.5",
        "s": "5.5",
        "zn": "1.8",
        "cu": "0,1",
        "b": "0.4",
        "mn": "11",
    },
    "Analise 4": {
        "argila": "18%",
        "ph": "5.2",
        "indice_smp": "6.6",
        "p": "4.6",
        "k": "46",
        "mo": "1.4",
        "al": "0.1",
        "ca": "1.6",
        "mg": "0.6",
        "h_al": "2.2",
        "ctc": "4.53",
        "sat_bases": "51",
        "sat_al": "4.1",
        "ca_mg": "2.7",
        "ca_k": "14",
        "mg_k": "5",
        "s": "5.7",
        "zn": "2.2",
        "cu": "0.4",
        "b": "0.3",
        "mn": "10",
    },
    "JOSE 1": {
        "argila": "18%",
        "ph": "5",
        "indice_smp": "5",
        "p": "0.7",
        "k": "24",
        "mo": "1.7",
        "al": "14",
        "ca": "1",
        "mg": "0.3",
        "h_al": "13.7",
        "ctc": "15",
        "sat_bases": "9",
        "sat_al": "50.2",
        "ca_mg": "3.3",
        "ca_k": "16",
        "mg_k": "4.9",
        "s": "7.9",
        "zn": "0.6",
        "cu": "1.6",
        "b": "1,6",
        "mn": "15",
    },
    "JOSE 2": {
        "argila": "22%",
        "ph": "5.4",
        "indice_smp": "5.7",
        "p": "5.9",
        "k": "58",
        "mo": "2.1",
        "al": "0.6",
        "ca": "3.6",
        "mg": "2.7",
        "h_al": "6.2",
        "ctc": "12.6",
        "sat_bases": "51",
        "sat_al": "8.5",
        "ca_mg": "1.3",
        "ca_k": "24",
        "mg_k": "18",
        "s": "5.9",
        "zn": "0.9",
        "cu": "2.2",
        "b": "0.5",
        "mn": "20",
    },
    "JOSE 3": {
        "argila": "20%",
        "ph": "5.4",
        "indice_smp": "5.9",
        "p": "2.7",
        "k": "66",
        "mo": "1.4",
        "al": "0.4",
        "ca": "3.1",
        "mg": "2.4",
        "h_al": "4.9",
        "ctc": "10.5",
        "sat_bases": "54",
        "sat_al": "6.6",
        "ca_mg": "1.3",
        "ca_k": "18",
        "mg_k": "14",
        "s": "5.2",
        "zn": "0.8",
        "cu": "1.6",
        "b": "0.5",
        "mn": "16",
    },
}

NEED_LIME_FIELDS = [
    ("argila", "Argila"),
    ("ph", "pH"),
    ("indice_smp", "Indice SMP"),
    ("al", "Al"),
    ("ca", "Ca"),
    ("mg", "Mg"),
    ("h_al", "H + Al"),
    ("ctc", "CTC"),
    ("mo", "M.O"),
    ("sat_bases", "% Sat Bases"),
    ("sat_al", "% Sat Al"),
]

NEED_NPK_FIELDS = [
    ("n", "N"),
    ("p", "P"),
    ("k", "K"),
]

CULTIVO_OPTIONS = (
    "Soja",
    "Milho",
    "Trigo",
    "Aveia",
    "Gramineas de estacao fria",
    "Gramineas de estacao quente",
)
ANTECEDENTE_OPTIONS = ("Graminea", "Leguminosa")
SAFRA_OPTIONS = ("1", "2")


@dataclass
class FieldFormResult:
    file_path: str
    nome: str
    cultivo: str
    municipio: str
    produtividade: str
    mode: str
    attributes: dict[str, str]


SHARED_FIELDS: list[FieldGeometry] = []


class AddFieldsPage(BasePage):
    """Load KMZ/KML files, list talhoes, and draw them on the canvas."""

    title = "Adicionar Talhões"
    CANVAS_BG = "#d8d8d8"
    FIELD_COLORS = ("#9ad19a", "#7ab5d3", "#f4b183", "#c9b8ff", "#f8d25c")
    SIDEBAR_WIDTH = 480

    def __init__(self, parent: ttk.Frame, app) -> None:
        super().__init__(parent, app)
        self.fields: list[FieldGeometry] = SHARED_FIELDS
        self.selected_index: int | None = None
        self.zoom_level: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.status_var = tk.StringVar(value="Nenhum talhao carregado.")
        self.total_area_var = tk.StringVar(value="Area total: 0.00 ha")
        self.municipality_var = tk.StringVar(value="Municipio: Nao informado")
        self.sidebar_canvas: tk.Canvas | None = None
        self._drag_origin: tuple[float, float, float, float] | None = None
        self._dragging = False
        self._world_origin: tuple[float, float] | None = None
        self._world_scale: float | None = None

    def build(self) -> None:
        self.style = ttk.Style()
        self.style.configure(
            "Card.TFrame",
            relief="ridge",
            borderwidth=2,
            padding=8,
        )
        self.style.configure(
            "CardSelected.TFrame",
            relief="solid",
            borderwidth=3,
            background="#e8f2ff",
        )

        self.container = ttk.Frame(self.parent)
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        self.container.columnconfigure(1, weight=0)

        self._build_canvas_area()
        self._build_sidebar()

        self.parent.after(100, self._draw_placeholder)

    def _build_canvas_area(self) -> None:
        canvas_wrapper = tk.Frame(self.container, background=self.CANVAS_BG, bd=0)
        canvas_wrapper.grid(row=0, column=0, sticky="nsew", padx=(20, 12), pady=(12, 12))
        canvas_wrapper.rowconfigure(0, weight=1)
        canvas_wrapper.columnconfigure(0, weight=1)

        canvas_holder = tk.Frame(
            canvas_wrapper,
            background=self.CANVAS_BG,
            highlightthickness=0,
            bd=0,
        )
        canvas_holder.grid(row=0, column=0, sticky="nsew")
        canvas_holder.rowconfigure(1, weight=1)
        canvas_holder.columnconfigure(0, weight=1)

        self.top_info = tk.Frame(canvas_holder, background=self.CANVAS_BG)
        self.top_info.grid(row=0, column=0, sticky="ew", pady=(8, 8))
        self.top_info.columnconfigure(0, weight=1)
        tk.Label(
            self.top_info,
            textvariable=self.total_area_var,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            background=self.CANVAS_BG,
        ).grid(row=0, column=0, sticky="w")

        self.canvas = tk.Canvas(
            canvas_holder,
            background=self.CANVAS_BG,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.configure(bg=self.CANVAS_BG)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda event: self._render_fields())
        self.canvas.bind("<MouseWheel>", self._on_canvas_scroll)
        self.canvas.bind("<Button-4>", self._on_canvas_scroll)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_canvas_scroll)  # Linux scroll down
        self.canvas.bind("<ButtonPress-1>", self._start_pan, add="+")
        self.canvas.bind("<B1-Motion>", self._pan_motion, add="+")
        self.canvas.bind("<ButtonRelease-1>", self._end_pan, add="+")
        self.canvas.tag_bind("field", "<ButtonRelease-1>", self._on_canvas_click)
        self.canvas.tag_bind("label", "<ButtonRelease-1>", self._on_canvas_click)

        self.bottom_info = tk.Frame(canvas_holder, background=self.CANVAS_BG)
        self.bottom_info.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        tk.Label(
            self.bottom_info,
            textvariable=self.municipality_var,
            anchor="w",
            font=("Segoe UI", 10),
            background=self.CANVAS_BG,
        ).grid(row=0, column=0, sticky="w")

    def _build_sidebar(self) -> None:
        wrapper = ttk.Frame(self.container, padding=(0, 16, 16, 16))
        wrapper.grid(row=0, column=1, sticky="ns")
        wrapper.rowconfigure(0, weight=1)

        self.sidebar_canvas = tk.Canvas(
            wrapper,
            highlightthickness=0,
            borderwidth=0,
            width=self.SIDEBAR_WIDTH,
        )
        sidebar_scroll = ttk.Scrollbar(
            wrapper, orient="vertical", command=self.sidebar_canvas.yview
        )
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        self.sidebar_canvas.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        sidebar_scroll.grid(row=0, column=1, sticky="ns")

        self.sidebar_inner = ttk.Frame(self.sidebar_canvas)
        self.sidebar_canvas.create_window(
            (0, 0),
            window=self.sidebar_inner,
            anchor="nw",
            width=self.SIDEBAR_WIDTH - 4,
        )
        self.sidebar_inner.bind(
            "<Configure>",
            lambda event: self.sidebar_canvas.configure(
                scrollregion=self.sidebar_canvas.bbox("all")
            ),
        )
        self.sidebar_canvas.bind("<Enter>", self._enable_sidebar_scroll)
        self.sidebar_canvas.bind("<Leave>", self._disable_sidebar_scroll)

        self._build_sidebar_content()

    def _build_sidebar_content(self) -> None:
        cards: list[ttk.Labelframe] = []
        cards.append(self._create_card("Inserir talhoes"))
        ttk.Label(
            cards[-1],
            text="Gerencie aqui os arquivos KMZ/KML e os talhoes carregados.",
            wraplength=self.SIDEBAR_WIDTH - 40,
        ).pack(anchor="w", fill="x")
        ttk.Button(
            cards[-1],
            text="Carregar talhao",
            command=self._handle_import,
            bootstyle="primary",
        ).pack(fill="x", pady=(12, 0))

        self.field_cards_frame = ttk.Frame(self.sidebar_inner)
        self.field_cards_frame.pack(fill="both", expand=True, padx=(6, 2))
        self.field_cards_frame.columnconfigure(0, weight=1)
        self._refresh_field_cards()

        self.status_label = ttk.Label(
            self.sidebar_inner,
            textvariable=self.status_var,
            padding=(8, 4),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=(6, 2))

    def _create_card(self, title: str) -> ttk.Labelframe:
        card = ttk.Labelframe(
            self.sidebar_inner,
            text=title,
            padding=(14, 10),
        )
        card.pack(fill="x", expand=False, pady=(0, 12), padx=(6, 2))
        return card

    def _refresh_field_cards(self) -> None:
        for child in self.field_cards_frame.winfo_children():
            child.destroy()
        if not self.fields:
            ttk.Label(
                self.field_cards_frame,
                text="Nenhum talhao inserido.",
                anchor="w",
            ).grid(row=0, column=0, sticky="ew")
            return
        for index, field in enumerate(self.fields):
            card = ttk.Frame(
                self.field_cards_frame,
                padding=12,
                style="Card.TFrame",
            )
            card.pack(fill="x", pady=4)
            card.field_index = index  # type: ignore[attr-defined]

            header = ttk.Frame(card)
            header.pack(fill="x")
            ttk.Label(
                header,
                text=field.name,
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", anchor="w")
            ttk.Button(
                header,
                text="Remover",
                command=lambda idx=index: self._confirm_remove_field(idx),
                bootstyle="danger-outline",
            ).pack(side="right")

            ttk.Label(
                card,
                text=f"Cultivo: {field.cultivation or 'Nao informado'}",
                anchor="w",
            ).pack(anchor="w", pady=(4, 0))
            ttk.Label(
                card,
                text=f"Area: {field.area_ha:.2f} ha",
                anchor="w",
            ).pack(anchor="w")

            self._bind_card_selection(card, index)

        self._highlight_selected_card()

    def _highlight_selected_card(self) -> None:
        for card in self.field_cards_frame.winfo_children():
            idx = getattr(card, "field_index", None)
            if idx is None:
                continue
            style = "CardSelected.TFrame" if idx == self.selected_index else "Card.TFrame"
            card.configure(style=style)

    def _confirm_remove_field(self, index: int) -> None:
        field = self.fields[index]
        if not messagebox.askyesno(
            "Remover talhao",
            f"Tem certeza que deseja remover '{field.name}'?",
        ):
            return
        del self.fields[index]
        if self.selected_index == index:
            self.selected_index = None
        elif self.selected_index is not None and self.selected_index > index:
            self.selected_index -= 1
        self.status_var.set(f"{len(self.fields)} talhao(oes) carregado(s).")
        self._update_area_labels()
        self._refresh_field_cards()
        self._render_fields()

    def _bind_card_selection(self, widget, index: int) -> None:
        interactive_types = (
            ttk.Entry,
            tk.Entry,
            ttk.Combobox,
            ttk.Spinbox,
            tk.Text,
            ttk.Button,
            tk.Button,
            ttk.Checkbutton,
            ttk.Radiobutton,
        )

        def _handle_click(event, idx=index):
            if isinstance(event.widget, interactive_types):
                return None
            # Defer selection so widget-specific bindings (e.g., expand/collapse)
            # run before the sidebar is rebuilt.
            self.parent.after_idle(lambda: self._select_field(idx, False))
            return None

        widget.bind("<Button-1>", _handle_click, add="+")
        for child in getattr(widget, "winfo_children", lambda: [])():
            self._bind_card_selection(child, index)

    def _enable_sidebar_scroll(self, _event) -> None:
        if self.sidebar_canvas is None:
            return
        self.sidebar_canvas.bind_all("<MouseWheel>", self._on_sidebar_scroll)

    def _disable_sidebar_scroll(self, _event) -> None:
        if self.sidebar_canvas is None:
            return
        self.sidebar_canvas.unbind_all("<MouseWheel>")

    def _on_sidebar_scroll(self, event) -> None:
        if self.sidebar_canvas is None:
            return
        delta = int(-1 * (event.delta / 120))
        self.sidebar_canvas.yview_scroll(delta, "units")

    def _reset_view(self) -> None:
        self.zoom_level = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._render_fields()

    def _reset_world_reference(self) -> None:
        self._world_origin = None
        self._world_scale = None

    def _initialize_world_reference(
        self,
        world_points: list[tuple[float, float]],
        draw_width: float,
        draw_height: float,
    ) -> None:
        if self._world_origin is not None and self._world_scale is not None:
            return
        if not world_points:
            return
        min_x = min(x for x, _ in world_points)
        max_x = max(x for x, _ in world_points)
        min_y = min(y for _, y in world_points)
        max_y = max(y for _, y in world_points)
        world_width = max(max_x - min_x, 1.0)
        world_height = max(max_y - min_y, 1.0)
        scale_x = max(draw_width / world_width, 1e-6)
        scale_y = max(draw_height / world_height, 1e-6)
        self._world_scale = min(scale_x, scale_y)
        self._world_origin = ((min_x + max_x) / 2, (min_y + max_y) / 2)

    # Canvas interaction -------------------------------------------------
    def _start_pan(self, event) -> None:
        self._drag_origin = (event.x, event.y, self.pan_x, self.pan_y)
        self._dragging = False

    def _pan_motion(self, event) -> None:
        if not self._drag_origin:
            return
        start_x, start_y, initial_pan_x, initial_pan_y = self._drag_origin
        dx = event.x - start_x
        dy = event.y - start_y
        if abs(dx) > 2 or abs(dy) > 2:
            self._dragging = True
        self.pan_x = initial_pan_x + dx
        self.pan_y = initial_pan_y + dy
        self._render_fields()

    def _end_pan(self, _event) -> None:
        self._drag_origin = None
        if self._dragging:
            self.canvas.after(50, self._clear_drag_flag)
        else:
            self._dragging = False

    def _clear_drag_flag(self) -> None:
        self._dragging = False

    def _on_canvas_scroll(self, event) -> None:
        if event.num == 4 or event.delta > 0:
            self._zoom(1.15, (event.x, event.y))
        elif event.num == 5 or event.delta < 0:
            self._zoom(1 / 1.15, (event.x, event.y))

    def _zoom(self, factor: float, anchor: tuple[float, float]) -> None:
        if not self.fields:
            return
        old_zoom = self.zoom_level
        new_zoom = min(max(old_zoom * factor, 0.2), 16.0)
        if abs(new_zoom - old_zoom) < 1e-6:
            return
        width = max(self.canvas.winfo_width(), 10)
        height = max(self.canvas.winfo_height(), 10)
        padding = 30
        draw_width = max(width - padding * 2, 10)
        draw_height = max(height - padding * 2, 10)
        center_x = padding + draw_width / 2
        center_y = padding + draw_height / 2
        anchor_x, anchor_y = anchor

        if abs(old_zoom) < 1e-6:
            old_zoom = 1.0
        self.pan_x = anchor_x - center_x - (anchor_x - center_x - self.pan_x) * (
            new_zoom / old_zoom
        )
        self.pan_y = anchor_y - center_y - (anchor_y - center_y - self.pan_y) * (
            new_zoom / old_zoom
        )
        self.zoom_level = new_zoom
        self._render_fields()

    def _on_canvas_click(self, event) -> None:
        if self._dragging:
            self._dragging = False
            return
        current = self.canvas.find_withtag("current")
        if not current:
            return
        tags = self.canvas.gettags(current)
        for tag in tags:
            if tag.startswith("field-"):
                try:
                    idx = int(tag.split("-", 1)[1])
                except ValueError:
                    continue
                self._select_field(idx)
                return

    # Data handling ------------------------------------------------------
    def _handle_import(self) -> None:
        mode_choice = FieldModeDialog(self.parent).show()
        if mode_choice is None:
            return
        if mode_choice == "soil":
            dialog: BaseFormDialog = FieldMetadataDialog(self.parent)
        else:
            dialog = FertilizationNeedDialog(self.parent)

        result = dialog.show()
        if result is None:
            return

        loaded_total = 0
        try:
            new_fields = KMZLoader.load_fields(result.file_path)
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror(
                "Erro ao carregar talhao",
                f"Arquivo: {Path(result.file_path).name}\n\nDetalhes: {exc}",
            )
            return
        if not new_fields:
            messagebox.showwarning(
                "Sem poligonos encontrados",
                f"Nenhum poligono foi detectado em {Path(result.file_path).name}.",
            )
            return

        for idx, field in enumerate(new_fields, start=1):
            suffix = f" #{idx}" if len(new_fields) > 1 else ""
            field.name = f"{result.nome}{suffix}"
            field.cultivation = result.cultivo
            field.municipality = result.municipio or "Nao informado"
            field.productivity = result.produtividade or None
            field.metadata = result.attributes | {
                "nome": field.name,
                "cultivo": result.cultivo,
                "municipio": field.municipality,
                "arquivo": Path(result.file_path).name,
                "modo": result.mode,
            }
        self.fields.extend(new_fields)
        loaded_total = len(new_fields)

        if loaded_total:
            self.status_var.set(f"{len(self.fields)} talhao(oes) carregado(s).")
            self.selected_index = None
            self._update_area_labels()
            self._refresh_field_cards()
            self._reset_view()

    def _select_field(self, index: int | None, _sync_tree: bool = False) -> None:
        if index is None or index < 0 or index >= len(self.fields):
            self.selected_index = None
        else:
            self.selected_index = index
        self._update_area_labels()
        self._highlight_selected_card()
        self._render_fields()

    def _update_area_labels(self) -> None:
        total = sum(field.area_ha for field in self.fields)
        self.total_area_var.set(f"Area total: {total:.2f} ha")
        if self.selected_index is not None and 0 <= self.selected_index < len(self.fields):
            selected_field = self.fields[self.selected_index]
            municipality = selected_field.municipality or "Nao informado"
            self.municipality_var.set(f"Municipio: {municipality}")
        else:
            self.municipality_var.set("Municipio: Selecione um talhao")

    # Drawing ------------------------------------------------------------
    def _draw_placeholder(self) -> None:
        self.canvas.delete("placeholder")
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Carregue arquivos KMZ/KML\npara visualizar os talhoes.",
            fill="#8d8d8d",
            font=("Segoe UI", 13),
            tags="placeholder",
            justify="center",
        )

    def _render_fields(self) -> None:
        self.canvas.delete("field")
        self.canvas.delete("label")
        self.canvas.delete("overlay")
        self.canvas.delete("placeholder")
        if not self.fields:
            self._reset_world_reference()
            self._draw_placeholder()
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 20 or height <= 20:
            return

        all_points = [
            point for field in self.fields for point in field.coordinates if point
        ]
        if not all_points:
            self._reset_world_reference()
            self._draw_placeholder()
            return

        world_points_by_field: list[list[tuple[float, float]]] = []
        world_points_flat: list[tuple[float, float]] = []
        for field in self.fields:
            if not field.coordinates:
                world_points_by_field.append([])
                continue
            transformed: list[tuple[float, float]] = []
            for point in field.coordinates:
                if not point:
                    continue
                lat, lon = point
                transformed.append(self._latlon_to_world(lat, lon))
            world_points_by_field.append(transformed)
            world_points_flat.extend(transformed)
        if not world_points_flat:
            self._reset_world_reference()
            self._draw_placeholder()
            return

        padding = 30
        draw_width = max(width - padding * 2, 10)
        draw_height = max(height - padding * 2, 10)
        center_x = padding + draw_width / 2
        center_y = padding + draw_height / 2

        self._initialize_world_reference(world_points_flat, draw_width, draw_height)
        if self._world_origin is None or self._world_scale is None:
            return
        origin_x, origin_y = self._world_origin
        scale = self._world_scale

        for index, (field, world_points) in enumerate(
            zip(self.fields, world_points_by_field)
        ):
            if not field.coordinates or not world_points:
                continue
            projected = [
                (
                    center_x + (x - origin_x) * scale,
                    center_y - (y - origin_y) * scale,
                )
                for x, y in world_points
            ]
            adjusted = [
                (
                    center_x + (x - center_x) * self.zoom_level + self.pan_x,
                    center_y + (y - center_y) * self.zoom_level + self.pan_y,
                )
                for x, y in projected
            ]
            flat = [coord for point in adjusted for coord in point]
            color = self._field_color(field, index)
            is_selected = index == self.selected_index
            outline = "#2c3e50" if is_selected else "#7f8c8d"
            width_px = 3 if is_selected else 1.5
            fill = self._field_fill_color(color, is_selected)
            self.canvas.create_polygon(
                *flat,
                fill=fill,
                outline=outline,
                width=width_px,
                tags=("field", f"field-{index}"),
                smooth=False,
            )
            centroid_x = sum(point[0] for point in adjusted) / len(adjusted)
            centroid_y = sum(point[1] for point in adjusted) / len(adjusted)
            self.canvas.create_text(
                centroid_x,
                centroid_y,
                text=self._field_label_text(field),
                fill="#2f3640",
                font=("Segoe UI", 10, "bold"),
                tags=("label", f"field-{index}"),
            )

        self._render_canvas_overlays(width, height)

    def _field_color(self, field: FieldGeometry, index: int) -> str:
        return self.FIELD_COLORS[index % len(self.FIELD_COLORS)]

    def _field_fill_color(self, base_color: str, is_selected: bool) -> str:
        return base_color if is_selected else self._lighten(base_color, 0.55)

    def _field_label_text(self, field: FieldGeometry) -> str:
        """Text displayed at the field centroid inside the canvas."""

        return field.name

    def _render_canvas_overlays(self, _width: int, _height: int) -> None:
        """Optional hook for subclasses to draw extra information over the map."""

        return

    @staticmethod
    def _lighten(color: str, factor: float) -> str:
        """Return a lighter version of ``color``."""
        color = color.lstrip("#")
        if len(color) != 6:
            return color
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _latlon_to_world(lat: float, lon: float) -> tuple[float, float]:
        """Project latitude/longitude to a planar metric system (Web Mercator)."""
        clamped_lat = max(min(lat, 89.9999), -89.9999)
        radius = 6378137.0
        x = radius * math.radians(lon)
        y = radius * math.log(math.tan(math.pi / 4 + math.radians(clamped_lat) / 2))
        return x, y

class FieldModeDialog:
    """Prompt user to escolher o tipo de insercao."""

    def __init__(self, master) -> None:
        self.master = master
        self.choice: str | None = None

    def show(self) -> str | None:
        self.window = tk.Toplevel(self.master)
        self.window.title("Tipo de insercao")
        self.window.transient(self.master.winfo_toplevel())
        self.window.grab_set()

        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Como deseja inserir o talhao?",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        ttk.Button(
            frame,
            text="Adicionar analise de solo completa",
            command=lambda: self._select("soil"),
            padding=10,
            bootstyle="primary",
        ).pack(fill="x", pady=6)
        ttk.Button(
            frame,
            text="Adicionar necessidade de adubacao",
            command=lambda: self._select("need"),
            padding=10,
        ).pack(fill="x", pady=6)
        ttk.Button(frame, text="Cancelar", command=self._cancel).pack(pady=(12, 0))

        self._center_window()
        self.master.wait_window(self.window)
        return self.choice

    def _select(self, value: str) -> None:
        self.choice = value
        self.window.destroy()

    def _cancel(self) -> None:
        self.choice = None
        self.window.destroy()

    def _center_window(self) -> None:
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        master_geo = self.master.winfo_toplevel().geometry()
        try:
            _, rest = master_geo.split('+', 1)
            mx, my = rest.split('+')
            mx, my = int(mx), int(my)
        except ValueError:
            mx = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
        x = mx + (self.master.winfo_width() // 2) - width // 2
        y = my + (self.master.winfo_height() // 2) - height // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")


class BaseFormDialog:
    """Base class for as janelas de cadastro de talhoes."""

    def __init__(
        self,
        master,
        title: str,
        defaults: dict[str, str],
        sections: list[tuple[str, list[tuple[str, str]]]],
        mode: str,
    ) -> None:
        self.master = master
        self.title = title
        self.defaults = defaults
        self.sections = sections
        self.mode = mode
        self.result: FieldFormResult | None = None
        self._entries: dict[str, tk.StringVar] = {}
        self._widgets: dict[str, tk.Widget] = {}
        self._file_var = tk.StringVar(value="")
        self._form_columns = 3
        self._grid_row = 0
        self._grid_col = 0
        self._form_frame: ttk.Frame | None = None
        self._density_frame: ttk.Frame | None = None

    def show(self) -> FieldFormResult | None:
        self.window = tk.Toplevel(self.master)
        self.window.title(self.title)
        self.window.transient(self.master.winfo_toplevel())
        self.window.grab_set()
        self.window.geometry("600x600")
        self.window.minsize(520, 520)

        container = ttk.Frame(self.window, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        frame = ttk.Frame(canvas, padding=10)
        frame_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        self._form_frame = frame

        def _update_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        frame.bind("<Configure>", _update_scrollregion)
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(frame_window, width=event.width),
        )

        for column in range(self._form_columns * 2):
            frame.columnconfigure(column, weight=1 if column % 2 else 0)

        self._add_entry("nome", "Nome do talhao", full_width=True)
        self._add_entry("municipio", "Municipio", full_width=True)
        cultivo_widget = self._add_combobox(
            "cultivo", "Cultivo", CULTIVO_OPTIONS, full_width=True
        )
        self._add_density_field()
        if isinstance(cultivo_widget, ttk.Combobox):
            cultivo_widget.bind(
                "<<ComboboxSelected>>",
                lambda _event: self._toggle_density_field(
                    self._entries.get("cultivo", tk.StringVar()).get()
                ),
            )
        self._toggle_density_field(self._entries.get("cultivo", tk.StringVar()).get())
        self._add_combobox("cultivo_safra", "Cultivo (1 ou 2)", SAFRA_OPTIONS, full_width=True)
        self._add_entry("produtividade", "Produtividade esperada (t/ha)", full_width=True)
        self._add_combobox(
            "cultura_antecedente",
            "Cultura antecedente",
            ANTECEDENTE_OPTIONS,
            full_width=True,
        )
        self._add_helper_text("Padrao: Graminea (se nao informado).")
        self._add_entry(
            "producao_cultura_antecedente",
            "Producao da cultura antecedente (t/ha)",
            full_width=True,
        )

        for title, fields in self.sections:
            self._add_separator(title)
            for key, label in fields:
                self._add_entry(key, label)

        ttk.Label(frame, text="Arquivo KMZ/KML").grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            sticky="w",
            pady=(12, 2),
        )
        self._grid_row += 1
        file_row = ttk.Frame(frame)
        file_row.grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            sticky="ew",
            pady=(0, 2),
        )
        file_row.columnconfigure(0, weight=1)
        ttk.Entry(file_row, textvariable=self._file_var, state="readonly").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(file_row, text="Escolher", command=self._choose_file).grid(row=0, column=1, padx=(6, 0))
        self._grid_row += 1

        button_row = ttk.Frame(frame)
        button_row.grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            pady=(16, 0),
            sticky="ew",
        )
        button_row.columnconfigure(0, weight=1)
        self._populate_button_row(button_row)

        self.window.update_idletasks()
        self._center_window()
        self.master.wait_window(self.window)
        return self.result

    def _populate_button_row(self, button_row: ttk.Frame) -> None:
        actions = ttk.Frame(button_row)
        actions.pack(side="right")
        ttk.Button(actions, text="Cancelar", command=self._on_cancel).pack(side="right", padx=(6, 0))
        ttk.Button(
            actions,
            text="Inserir talhao",
            command=self._on_submit,
            bootstyle="primary",
        ).pack(side="right")

    def _add_entry(self, key: str, label: str, full_width: bool = False) -> None:
        def widget_factory():
            return ttk.Entry(self._form_frame, textvariable=var)

        var = tk.StringVar(value=self.defaults.get(key, ""))
        entry = self._place_field(label, widget_factory, full_width)
        entry.configure(textvariable=var)
        self._entries[key] = var
        self._widgets[key] = entry

    def _add_combobox(self, key: str, label: str, values: tuple[str, ...], full_width: bool = False):
        var = tk.StringVar(value=self.defaults.get(key, values[0]))

        def widget_factory():
            return ttk.Combobox(
                self._form_frame,
                textvariable=var,
                values=values,
                state="readonly",
            )

        widget = self._place_field(label, widget_factory, full_width)
        self._entries[key] = var
        self._widgets[key] = widget
        return widget

    def _add_density_field(self) -> None:
        form = self._form_frame
        if form is None:
            raise RuntimeError("Form frame not initialized")
        columns = self._form_columns * 2
        var = tk.StringVar(value=self.defaults.get("densidade_plantas_ha", "65000"))
        self._entries["densidade_plantas_ha"] = var
        ajuste_var = tk.StringVar(value=self.defaults.get("ajuste_n_rendimento", "Nao"))
        self._entries["ajuste_n_rendimento"] = ajuste_var
        rotacao_var = tk.StringVar(value=self.defaults.get("rotacao_soja", "Nao"))
        self._entries["rotacao_soja"] = rotacao_var
        sistema_var = tk.StringVar(value=self.defaults.get("sistema_cultivo", "Convencional"))
        self._entries["sistema_cultivo"] = sistema_var
        frame = ttk.Frame(form)
        frame.grid(
            row=self._grid_row,
            column=0,
            columnspan=columns,
            sticky="ew",
            pady=(0, 2),
        )
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Densidade de plantas/ha").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(8, 2),
        )
        entry = ttk.Entry(frame, textvariable=var)
        entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=(0, 2),
        )
        ttk.Label(
            frame,
            text="Padrao: 65000 plantas/ha. Informe outro valor se desejar.",
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=(0, 2),
        )
        ttk.Label(
            frame,
            text="Ajustar doses de N de acordo com rendimento esperado",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 2),
        )
        radio_frame = ttk.Frame(frame)
        radio_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ttk.Radiobutton(
            radio_frame,
            text="Nao",
            variable=ajuste_var,
            value="Nao",
        ).pack(side="left")
        ttk.Radiobutton(
            radio_frame,
            text="Sim",
            variable=ajuste_var,
            value="Sim",
        ).pack(side="left", padx=(12, 0))
        ttk.Label(
            frame,
            text="Rotacao anual com soja",
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 2),
        )
        rotacao_frame = ttk.Frame(frame)
        rotacao_frame.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ttk.Radiobutton(
            rotacao_frame,
            text="Nao",
            variable=rotacao_var,
            value="Nao",
        ).pack(side="left")
        ttk.Radiobutton(
            rotacao_frame,
            text="Sim",
            variable=rotacao_var,
            value="Sim",
        ).pack(side="left", padx=(12, 0))
        ttk.Label(
            frame,
            text="Sistema de cultivo (milho)",
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 2),
        )
        sistema_frame = ttk.Frame(frame)
        sistema_frame.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ttk.Radiobutton(
            sistema_frame,
            text="Convencional",
            variable=sistema_var,
            value="Convencional",
        ).pack(side="left")
        ttk.Radiobutton(
            sistema_frame,
            text="Plantio direto",
            variable=sistema_var,
            value="Plantio direto",
        ).pack(side="left", padx=(12, 0))
        self._widgets["densidade_plantas_ha"] = entry
        self._density_frame = frame
        self._grid_row += 1
        self._grid_col = 0

    def _toggle_density_field(self, cultivo: str | None) -> None:
        if not self._density_frame:
            return
        if cultivo and cultivo.strip().lower().startswith("milh"):
            if not self._entries["densidade_plantas_ha"].get().strip():
                self._entries["densidade_plantas_ha"].set("65000")
            if not self._entries["ajuste_n_rendimento"].get().strip():
                self._entries["ajuste_n_rendimento"].set("Nao")
            if not self._entries["rotacao_soja"].get().strip():
                self._entries["rotacao_soja"].set("Nao")
            if not self._entries["sistema_cultivo"].get().strip():
                self._entries["sistema_cultivo"].set("Convencional")
            self._density_frame.grid()
        else:
            self._density_frame.grid_remove()

    def _place_field(self, label: str, widget_factory, full_width: bool):
        form = self._form_frame
        columns = self._form_columns * 2
        if form is None:
            raise RuntimeError("Form frame not initialized")
        if full_width:
            ttk.Label(form, text=label).grid(
                row=self._grid_row,
                column=0,
                columnspan=1,
                sticky="w",
                pady=(8, 2),
            )
            widget = widget_factory()
            widget.grid(
                row=self._grid_row,
                column=1,
                columnspan=columns - 1,
                sticky="ew",
                pady=(0, 2),
            )
            self._grid_row += 1
            self._grid_col = 0
        else:
            col = self._grid_col * 2
            ttk.Label(form, text=label).grid(
                row=self._grid_row,
                column=col,
                sticky="w",
                pady=(8, 2),
            )
            widget = widget_factory()
            widget.grid(
                row=self._grid_row,
                column=col + 1,
                sticky="ew",
                pady=(0, 2),
                padx=(0, 8),
            )
            self._grid_col += 1
            if self._grid_col >= self._form_columns:
                self._grid_col = 0
                self._grid_row += 1
        return widget

    def _add_separator(self, label: str) -> None:
        form = self._form_frame
        if form is None:
            return
        ttk.Separator(form).grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            pady=(16, 6),
            sticky="ew",
        )
        self._grid_row += 1
        ttk.Label(form, text=label).grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            sticky="w",
        )
        self._grid_row += 1
        self._grid_col = 0

    def _add_helper_text(self, text: str) -> None:
        form = self._form_frame
        if form is None:
            return
        ttk.Label(
            form,
            text=text,
            foreground="#5f5f5f",
        ).grid(
            row=self._grid_row,
            column=0,
            columnspan=self._form_columns * 2,
            sticky="w",
            pady=(0, 4),
        )
        self._grid_row += 1
        self._grid_col = 0

    def _choose_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecione arquivo KMZ ou KML",
            filetypes=(("Arquivos KMZ", "*.kmz"), ("Arquivos KML", "*.kml")),
        )
        if file_path:
            self._file_var.set(file_path)

    def _on_cancel(self) -> None:
        self.result = None
        self.window.destroy()

    def _on_submit(self) -> None:
        if not self._file_var.get():
            messagebox.showwarning("Arquivo obrigatorio", "Selecione um arquivo KMZ/KML.")
            return
        nome = self._entries["nome"].get().strip() or self.defaults["nome"]
        cultivo = self._entries["cultivo"].get().strip() or self.defaults["cultivo"]
        municipio = self._entries["municipio"].get().strip() or "Nao informado"
        produtividade = self._entries["produtividade"].get().strip()
        attributes = {
            key: var.get().strip()
            for key, var in self._entries.items()
            if key not in {"nome", "cultivo", "municipio"}
        }
        antecedente_value = (attributes.get("cultura_antecedente") or "").strip()
        valid_antecedentes = {value for value in ANTECEDENTE_OPTIONS if value}
        if antecedente_value and antecedente_value not in valid_antecedentes:
            messagebox.showwarning(
                "Cultura antecedente",
                "Selecione uma cultura antecedente valida (Graminea ou Leguminosa).",
            )
            return
        if not antecedente_value:
            attributes["cultura_antecedente"] = "Graminea"
        if not cultivo.strip().lower().startswith("milh"):
            attributes.pop("densidade_plantas_ha", None)
            attributes.pop("ajuste_n_rendimento", None)
            attributes.pop("rotacao_soja", None)
            attributes.pop("sistema_cultivo", None)
        elif not attributes.get("densidade_plantas_ha"):
            attributes["densidade_plantas_ha"] = "65000"
        if cultivo.strip().lower().startswith("milh") and not attributes.get("ajuste_n_rendimento"):
            attributes["ajuste_n_rendimento"] = "Nao"
        if cultivo.strip().lower().startswith("milh") and not attributes.get("rotacao_soja"):
            attributes["rotacao_soja"] = "Nao"
        if cultivo.strip().lower().startswith("milh") and not attributes.get("sistema_cultivo"):
            attributes["sistema_cultivo"] = "Convencional"
        cultura_antecedente = attributes.get("cultura_antecedente", "").strip().lower()
        if cultura_antecedente == "indiferente":
            attributes.pop("producao_cultura_antecedente", None)
        self.result = FieldFormResult(
            file_path=self._file_var.get(),
            nome=nome,
            cultivo=cultivo,
            municipio=municipio,
            produtividade=produtividade,
            mode=self.mode,
            attributes=attributes,
        )
        self.window.destroy()

    def _center_window(self) -> None:
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        master_geo = self.master.winfo_toplevel().geometry()
        try:
            _, rest = master_geo.split('+', 1)
            mx, my = rest.split('+')
            mx, my = int(mx), int(my)
        except ValueError:
            mx = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
        x = mx + (self.master.winfo_width() // 2) - width // 2
        y = my + (self.master.winfo_height() // 2) - height // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")


class FieldMetadataDialog(BaseFormDialog):
    def __init__(self, master) -> None:
        super().__init__(
            master,
            title="Adicionar analise de solo completa",
            defaults=FIELD_FORM_DEFAULTS,
            sections=[("Analises de solo", SOIL_ANALYSIS_FIELDS)],
            mode="soil",
        )
        self._sample_var = tk.StringVar(value="")

    MICRO_FIELDS = {"s", "cu", "zn", "b", "mn"}
    PERCENT_FIELDS = {"argila", "mo", "sat_bases", "sat_al"}
    SPECIAL_RANGES = {
        "ph": (4.0, 8.0),
        "indice_smp": (5.0, 7.0),
    }
    FIELD_DECIMALS = {
        "argila": 1,
        "ph": 1,
        "indice_smp": 1,
        "k": 0,
        "sat_bases": 1,
        "sat_al": 1,
        "ca_mg": 1,
        "ca_k": 1,
        "mg_k": 1,
        "cu": 2,
        "zn": 2,
        "b": 2,
    }

    def show(self) -> FieldFormResult | None:
        self._apply_random_defaults()
        return super().show()

    def _populate_button_row(self, button_row: ttk.Frame) -> None:
        left = ttk.Frame(button_row)
        left.pack(side="left")
        ttk.Label(left, text="Amostra de validacao").pack(anchor="w")
        sample_combo = ttk.Combobox(
            left,
            state="readonly",
            values=SOIL_SAMPLE_OPTIONS,
            textvariable=self._sample_var,
            width=16,
        )
        sample_combo.pack(anchor="w", pady=(2, 0))
        sample_combo.bind("<<ComboboxSelected>>", self._apply_sample_values)
        ttk.Button(
            left,
            text="Limpar espacos",
            command=self._clear_analysis_fields,
        ).pack(anchor="w", pady=(6, 0))
        super()._populate_button_row(button_row)

    def _apply_random_defaults(self) -> None:
        randomized = dict(FIELD_FORM_DEFAULTS)
        for key in SOIL_ANALYSIS_KEYS:
            randomized[key] = self._random_value_for_field(key)
        self.defaults = randomized

    def _random_value_for_field(self, key: str) -> str:
        span = self.SPECIAL_RANGES.get(key)
        if span is None:
            span = (0.0, 7.0) if key in self.MICRO_FIELDS else (0.0, 70.0)
        low, high = span
        decimals = self.FIELD_DECIMALS.get(key, 1)
        value = random.uniform(low, high)
        text = f"{value:.{decimals}f}" if decimals > 0 else f"{int(round(value))}"
        if decimals > 0 and "." in text:
            text = text.rstrip("0").rstrip(".")
        if key in self.PERCENT_FIELDS:
            return f"{text}%"
        return text

    def _clear_analysis_fields(self) -> None:
        for key in SOIL_ANALYSIS_KEYS:
            if key in self._entries:
                self._entries[key].set("")

    def _apply_sample_values(self, _event=None) -> None:
        sample_name = self._sample_var.get()
        if not sample_name or sample_name not in SOIL_SAMPLE_VALUES:
            return
        sample = SOIL_SAMPLE_VALUES[sample_name]
        for key in SOIL_ANALYSIS_KEYS:
            if key not in self._entries:
                continue
            if key in sample:
                self._entries[key].set(sample[key])
            else:
                self._entries[key].set("")


class FertilizationNeedDialog(BaseFormDialog):
    def __init__(self, master) -> None:
        sections = [
            ("Parametros para calcario", NEED_LIME_FIELDS),
            ("Necessidades de adubacao", NEED_NPK_FIELDS),
        ]
        super().__init__(
            master,
            title="Adicionar necessidade de adubacao",
            defaults=NEED_FORM_DEFAULTS,
            sections=sections,
            mode="need",
        )
