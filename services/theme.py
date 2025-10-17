# DOU/services/theme.py
import pyqtgraph as pg

def apply_theme(app, plot_widget=None):
    # Qt widgets dark QSS
    qss = """
    QWidget { background-color: #2b2b2b; color: #dcdcdc; font-family: Consolas, "Courier New", monospace; font-size: 11pt; }
    QLineEdit, QComboBox, QListWidget { background-color: #3c3f41; border: 1px solid #555; padding: 4px; }
    QListWidget { background-color: #1f2123; }
    QComboBox QAbstractItemView { background-color: #2b2b2b; selection-background-color: #555; }
    QPushButton { background-color: #444; border: 1px solid #666; padding: 6px; border-radius: 4px; }
    QPushButton:hover { background-color: #555; }
    QPushButton:pressed { background-color: #222; }
    QPushButton:disabled { color: #888; background-color: #333; border-color: #444; }
    QLabel { color: #dcdcdc; }
    QGroupBox { border: 1px solid #555; border-radius: 6px; margin-top: 8px; padding-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #a7c7ff; font-weight: bold; }
    """
    app.setStyleSheet(qss)

    # PyQtGraph dark style sync
    if plot_widget:
        # Handle single widget or a list/tuple
        widgets = plot_widget if isinstance(plot_widget, (list, tuple)) else [plot_widget]
        for w in widgets:
            w.setBackground("#2b2b2b")
            w.showGrid(x=True, y=True, alpha=0.3)
            for axis in ("left", "bottom"):
                w.getAxis(axis).setPen(pg.mkPen(color="#dcdcdc"))
                w.getAxis(axis).setTextPen(pg.mkPen(color="#dcdcdc"))
