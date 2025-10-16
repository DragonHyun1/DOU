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
        # 단일 위젯이거나 리스트로 전달된 경우 모두 처리
        widgets = plot_widget if isinstance(plot_widget, (list, tuple)) else [plot_widget]
        for w in widgets:
            w.setBackground("#2b2b2b")
            w.showGrid(x=True, y=True, alpha=0.3)
            for axis in ("left", "bottom"):
                w.getAxis(axis).setPen(pg.mkPen(color="#dcdcdc"))
                w.getAxis(axis).setTextPen(pg.mkPen(color="#dcdcdc"))
