from __future__ import annotations
from abc import ABC, abstractmethod
from tkinter import ttk


class BasePage(ABC):
    
    title: str = "Pagina"

    def __init__(self, parent: ttk.Frame, app) -> None:
        self.parent = parent
        self.app = app

    @abstractmethod
    def build(self) -> None:
        """Create widgets inside ``self.parent``."""

    def refresh(self) -> None:
        """Hook called when the tab becomes visible."""
        return
