"""
Main TkBootstrap window hosting the notebook pages.
"""

from __future__ import annotations

from tkinter import ttk

import ttkbootstrap as tb

from ..pages.add_fields import AddFieldsPage
from ..pages.base_page import BasePage
from ..pages.cultivos import CultivosPage
from ..pages.soil_conditions import SoilConditionsPage


class FerticalcApp(tb.Window):
    """TkBootstrap application shell."""

    def __init__(self) -> None:
        super().__init__(title="FertiCalc", themename="litera")
        self.geometry("1400x850")
        self.minsize(1024, 640)
        self.after(200, self._maximize_window)
        self._pages: dict[str, BasePage] = {}
        self._build_layout()

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        for page_cls in (AddFieldsPage, CultivosPage, SoilConditionsPage):
            self._add_page(page_cls)

        # Ensure the first page receives a refresh call.
        self.after(50, self._refresh_current_page)

    def _add_page(self, page_cls: type[BasePage]) -> None:
        frame = ttk.Frame(self.notebook)
        page_instance = page_cls(frame, self)
        page_instance.build()
        self.notebook.add(frame, text=page_instance.title)
        self._pages[str(frame)] = page_instance

    def _on_tab_change(self, _event) -> None:
        self._refresh_current_page()

    def _refresh_current_page(self) -> None:
        current_tab = self.notebook.select()
        page = self._pages.get(current_tab)
        if page:
            page.refresh()

    def run(self) -> None:
        """Start Tk mainloop."""
        self.mainloop()

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            pass
