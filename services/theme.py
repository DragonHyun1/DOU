# Enhanced theme for HVPM Monitor
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

class ModernTheme:
    # Color palette
    COLORS = {
        'primary': '#2b2b2b',           # Main background
        'secondary': '#3a3a3a',        # Secondary background
        'surface': '#4a4a4a',          # Surface elements
        'accent': '#4CAF50',           # Accent color (green)
        'accent_hover': '#45a049',     # Accent hover
        'text_primary': '#ffffff',     # Primary text
        'text_secondary': '#dcdcdc',   # Secondary text
        'text_muted': '#aaaaaa',       # Muted text
        'border': '#555555',           # Border color
        'error': '#ff6b6b',            # Error color
        'warning': '#ffa726',          # Warning color
        'info': '#42a5f5',             # Info color
        'success': '#66bb6a',          # Success color
    }

def apply_theme(app, plot_widget=None):
    """Apply modern dark theme to the application"""
    colors = ModernTheme.COLORS
    
    # Enhanced Qt stylesheet with modern design
    qss = f"""
    /* Main application styling */
    QMainWindow {{
        background-color: {colors['primary']};
        color: {colors['text_primary']};
    }}
    
    QWidget {{
        background-color: {colors['primary']};
        color: {colors['text_secondary']};
        font-family: 'Segoe UI', 'Arial', sans-serif;
        font-size: 11pt;
    }}
    
    /* Group boxes with modern styling */
    QGroupBox {{
        font-weight: bold;
        font-size: 12pt;
        color: {colors['text_primary']};
        border: 2px solid {colors['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        background-color: {colors['secondary']};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 8px 0 8px;
        color: {colors['accent']};
        background-color: {colors['secondary']};
    }}
    
    /* Input fields */
    QLineEdit {{
        background-color: {colors['surface']};
        border: 2px solid {colors['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12pt;
        color: {colors['text_primary']};
        selection-background-color: {colors['accent']};
    }}
    
    QLineEdit:focus {{
        border: 2px solid {colors['accent']};
        background-color: {colors['secondary']};
    }}
    
    QLineEdit:disabled {{
        background-color: #2a2a2a;
        color: {colors['text_muted']};
        border: 2px solid #333;
    }}
    
    /* Combo boxes */
    QComboBox {{
        background-color: {colors['surface']};
        border: 2px solid {colors['border']};
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 11pt;
        color: {colors['text_primary']};
        min-width: 120px;
    }}
    
    QComboBox:hover {{
        border: 2px solid {colors['accent']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {colors['text_secondary']};
        margin-right: 5px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['accent']};
        color: {colors['text_primary']};
        outline: none;
    }}
    
    /* Buttons with enhanced styling */
    QPushButton {{
        background-color: {colors['surface']};
        border: 2px solid {colors['border']};
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 11pt;
        font-weight: 500;
        color: {colors['text_primary']};
        min-height: 20px;
    }}
    
    QPushButton:hover {{
        background-color: {colors['border']};
        border: 2px solid {colors['accent']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['primary']};
        border: 2px solid {colors['accent']};
    }}
    
    QPushButton:disabled {{
        background-color: #2a2a2a;
        border: 2px solid #333;
        color: {colors['text_muted']};
    }}
    
    /* Labels */
    QLabel {{
        color: {colors['text_secondary']};
        background-color: transparent;
    }}
    
    /* List widgets */
    QListWidget {{
        background-color: {colors['primary']};
        border: 2px solid {colors['border']};
        border-radius: 6px;
        padding: 4px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 10pt;
        color: {colors['text_secondary']};
        alternate-background-color: {colors['secondary']};
    }}
    
    QListWidget::item {{
        padding: 4px 8px;
        border-bottom: 1px solid {colors['border']};
    }}
    
    QListWidget::item:selected {{
        background-color: {colors['accent']};
        color: white;
    }}
    
    QListWidget::item:hover {{
        background-color: {colors['secondary']};
    }}
    
    /* Frames */
    QFrame {{
        border-radius: 6px;
    }}
    
    /* Scroll bars */
    QScrollBar:vertical {{
        background-color: {colors['secondary']};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {colors['border']};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {colors['accent']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}
    
    /* Menu bar */
    QMenuBar {{
        background-color: {colors['secondary']};
        color: {colors['text_primary']};
        border-bottom: 1px solid {colors['border']};
        padding: 4px;
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {colors['accent']};
    }}
    
    QMenu {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 8px 16px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {colors['accent']};
    }}
    
    /* Status bar */
    QStatusBar {{
        background-color: {colors['secondary']};
        color: {colors['text_secondary']};
        border-top: 1px solid {colors['border']};
        padding: 4px;
    }}
    
    /* Separator lines */
    QFrame[frameShape="4"] {{
        color: {colors['border']};
        background-color: {colors['border']};
    }}
    
    QFrame[frameShape="5"] {{
        color: {colors['border']};
        background-color: {colors['border']};
    }}
    """
    
    app.setStyleSheet(qss)

    # PyQtGraph styling for plots
    if plot_widget:
        widgets = plot_widget if isinstance(plot_widget, (list, tuple)) else [plot_widget]
        for w in widgets:
            # Set background
            w.setBackground(colors['primary'])
            
            # Configure grid
            w.showGrid(x=True, y=True, alpha=0.2)
            
            # Style axes
            for axis_name in ('left', 'bottom', 'right', 'top'):
                axis = w.getAxis(axis_name)
                if axis:
                    # Set axis colors
                    axis.setPen(pg.mkPen(color=colors['text_secondary'], width=1))
                    axis.setTextPen(pg.mkPen(color=colors['text_secondary']))
                    
                    # Set tick colors
                    axis.setStyle(tickTextOffset=10)
                    
            # Set plot area background
            w.plotItem.getViewBox().setBackgroundColor(colors['primary'])
            
            # Style the plot border
            w.plotItem.getViewBox().border = pg.mkPen(color=colors['border'], width=1)

def get_color(color_name):
    """Get color from theme palette"""
    return ModernTheme.COLORS.get(color_name, '#ffffff')

def get_status_color(status):
    """Get appropriate color for status messages"""
    status_colors = {
        'error': ModernTheme.COLORS['error'],
        'warn': ModernTheme.COLORS['warning'],
        'warning': ModernTheme.COLORS['warning'],
        'info': ModernTheme.COLORS['info'],
        'success': ModernTheme.COLORS['success'],
        'connected': ModernTheme.COLORS['success'],
        'disconnected': ModernTheme.COLORS['error'],
    }
    return status_colors.get(status.lower(), ModernTheme.COLORS['text_secondary'])
