# Responsive layout utilities for HVPM Monitor
try:
    from PyQt6 import QtWidgets
    from PyQt6.QtWidgets import QWidget, QSizePolicy
    from PyQt6.QtCore import QSize, Qt
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Fallback classes for testing
    class QSizePolicy:
        class Policy:
            Preferred = "Preferred"
            Expanding = "Expanding"
            Fixed = "Fixed"
        def __init__(self, h, v): pass
        def setHorizontalStretch(self, s): pass
    
    class QSize:
        def __init__(self, w, h):
            self._w, self._h = w, h
        def width(self): return self._w
        def height(self): return self._h

from .adaptive_ui import get_adaptive_ui

class ResponsiveLayoutManager:
    """Manages responsive layout adjustments"""
    
    def __init__(self):
        self.adaptive_ui = get_adaptive_ui()
    
    def make_widget_responsive(self, widget, min_width_ratio=0.2, max_width_ratio=1.0):
        """Make a widget responsive to screen size changes"""
        if not widget:
            return
            
        # Calculate responsive widths
        screen_width = self.adaptive_ui.get_responsive_width(1.0)
        min_width = int(screen_width * min_width_ratio)
        max_width = int(screen_width * max_width_ratio)
        
        # Apply responsive sizing
        widget.setMinimumWidth(min_width)
        if max_width_ratio < 1.0:
            widget.setMaximumWidth(max_width)
        else:
            widget.setMaximumWidth(16777215)  # Remove max width constraint
        
        # Set size policy for better responsiveness
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(1)
        widget.setSizePolicy(size_policy)
    
    def apply_responsive_margins(self, layout):
        """Apply responsive margins to a layout"""
        if not layout:
            return
            
        base_margin = self.adaptive_ui.get_scaled_value(10)
        layout.setContentsMargins(base_margin, base_margin, base_margin, base_margin)
        layout.setSpacing(self.adaptive_ui.get_scaled_value(8))
    
    def apply_responsive_margins_recursive(self, root_widget):
        """Apply responsive margins/spacing to all layouts under a root widget"""
        if not PYQT_AVAILABLE or root_widget is None:
            return
        try:
            # Find all layouts in the widget tree
            all_layouts = root_widget.findChildren(QtWidgets.QLayout)
        except Exception:
            all_layouts = []
        # Apply margins/spacing, skipping known zero-margin layouts
        skip_names = {"graphLayout"}
        for layout in all_layouts:
            try:
                name = getattr(layout, "objectName", lambda: "")()
                if name in skip_names:
                    continue
                self.apply_responsive_margins(layout)
            except Exception:
                # Best effort; continue on any individual failure
                continue
    
    def setup_responsive_groupbox(self, groupbox, preferred_width_ratio=0.3):
        """Setup responsive behavior for a GroupBox"""
        if not groupbox:
            return
            
        self.make_widget_responsive(groupbox, 0.25, preferred_width_ratio)
        
        # Ensure minimum height is reasonable
        min_height = self.adaptive_ui.get_scaled_value(100)
        groupbox.setMinimumHeight(min_height)
    
    def setup_responsive_buttons(self, *buttons):
        """Setup responsive behavior for buttons"""
        min_button_width = self.adaptive_ui.get_scaled_value(80)
        min_button_height = self.adaptive_ui.get_scaled_value(32)
        
        for button in buttons:
            if button:
                button.setMinimumSize(QSize(min_button_width, min_button_height))
                # Allow buttons to expand horizontally
                size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                button.setSizePolicy(size_policy)
    
    def setup_responsive_combobox(self, *comboboxes):
        """Setup responsive behavior for combo boxes"""
        min_combo_width = self.adaptive_ui.get_scaled_value(100)
        min_combo_height = self.adaptive_ui.get_scaled_value(28)
        
        for combo in comboboxes:
            if combo:
                combo.setMinimumSize(QSize(min_combo_width, min_combo_height))
                size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                combo.setSizePolicy(size_policy)

# Global instance
_responsive_manager = None

def get_responsive_manager():
    """Get global ResponsiveLayoutManager instance"""
    global _responsive_manager
    if _responsive_manager is None:
        _responsive_manager = ResponsiveLayoutManager()
    return _responsive_manager