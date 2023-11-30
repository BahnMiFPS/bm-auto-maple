import tkinter as tk
from src.gui.interfaces import LabelFrame, Frame
from src.common.interfaces import Configurable


class Balrog(LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Balrog', **kwargs)

        self.balrog = BalrogSettings('balrog')
        self.auto_balrog = tk.BooleanVar(
            value=self.balrog.get('Auto-balrog'))

        feed_row = Frame(self)
        feed_row.pack(side=tk.TOP, fill='x', expand=True, pady=5, padx=5)
        check = tk.Checkbutton(
            feed_row,
            variable=self.auto_balrog,
            text='Auto-balrog',
            command=self._on_change
        )
        check.pack()

    def _on_change(self):
        self.balrog.set('Auto-balrog', self.auto_balrog.get())
        self.balrog.save_config()


class BalrogSettings(Configurable):
    DEFAULT_CONFIG = {
        'Auto-balrog': False,
    }

    def get(self, key):
        return self.config[key]

    def set(self, key, value):
        assert key in self.config
        self.config[key] = value
