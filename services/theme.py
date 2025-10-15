# DOU/services/theme.py
import pyqtgraph as pg

def apply_theme(app, plot_widget=None):
    # Qt 위젯 다크 QSS
    qss = """
    QWidget{background-color:#2b2b2b;color:#dcdcdc;font-family:Consolas,"Courier New",monospace;font-size:11pt;}
    QLineEdit,QComboBox,QListWidget{background-color:#3c3f41;border:1px solid #555;padding:4px;}
    QPushButton{background-color:#444;border:1px solid #666;padding:6px;border-radius:4px;}
    QPushButton:hover{background-color:#555;} QPushButton:pressed{background-color:#222;}
    QLabel{color:#dcdcdc;}
    """
    app.setStyleSheet(qss)

    # PyQtGraph 다크 스타일 동기화
    if plot_widget:
        plot_widget.setBackground("#2b2b2b")
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        for axis in ("left", "bottom"):
            plot_widget.getAxis(axis).setPen(pg.mkPen(color="#dcdcdc"))
            plot_widget.getAxis(axis).setTextPen(pg.mkPen(color="#dcdcdc"))
        plot_widget.setLabel("left", "Current (A)", color="#dcdcdc")
        plot_widget.setLabel("bottom", "Time (s)", color="#dcdcdc")
