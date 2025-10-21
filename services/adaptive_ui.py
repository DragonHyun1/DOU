# Adaptive UI sizing system for cross-platform compatibility
import sys

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QSize
    from PyQt6.QtGui import QScreen
    PYQT_AVAILABLE = True
except ImportError:
    # Fallback for testing without PyQt6
    PYQT_AVAILABLE = False
    
    class QSize:
        def __init__(self, width, height):
            self._width = width
            self._height = height
        def width(self): return self._width
        def height(self): return self._height

class AdaptiveUI:
    """
    Adaptive UI system that adjusts sizes based on screen DPI and resolution
    """
    
    def __init__(self):
        self.app = QApplication.instance() if PYQT_AVAILABLE else None
        self.base_dpi = 96  # Standard Windows DPI
        self.base_font_size = 11  # Base font size in pt
        self.scale_factor = self._calculate_scale_factor()
        
    def _calculate_scale_factor(self):
        """Calculate scale factor based on screen DPI"""
        if not PYQT_AVAILABLE or not self.app:
            # Fallback: try to detect DPI from system
            try:
                import tkinter as tk
                root = tk.Tk()
                dpi = root.winfo_fpixels('1i')
                root.destroy()
            except:
                dpi = self.base_dpi  # Default DPI
                
            scale = dpi / self.base_dpi
            scale = max(0.8, min(scale, 2.5))
            print(f"[AdaptiveUI] Estimated DPI: {dpi}, Scale Factor: {scale:.2f}")
            return scale
            
        screen = self.app.primaryScreen()
        if not screen:
            return 1.0
            
        # Get physical DPI
        dpi = screen.physicalDotsPerInch()
        
        # Calculate scale factor
        scale = dpi / self.base_dpi
        
        # Clamp scale factor to reasonable range
        scale = max(0.8, min(scale, 2.5))
        
        print(f"[AdaptiveUI] Screen DPI: {dpi}, Scale Factor: {scale:.2f}")
        return scale
    
    def get_scaled_size(self, base_width, base_height=None):
        """Get scaled size based on DPI"""
        if base_height is None:
            base_height = base_width
            
        scaled_width = int(base_width * self.scale_factor)
        scaled_height = int(base_height * self.scale_factor)
        
        return QSize(scaled_width, scaled_height)
    
    def get_scaled_value(self, base_value):
        """Get scaled integer value"""
        return int(base_value * self.scale_factor)
    
    def get_scaled_font_size(self, base_size=None):
        """Get scaled font size in pt"""
        if base_size is None:
            base_size = self.base_font_size
            
        # Font scaling should be more conservative
        font_scale = min(self.scale_factor, 1.5)
        return max(8, int(base_size * font_scale))
    
    def get_responsive_width(self, screen_percentage=0.8):
        """Get responsive width based on screen size"""
        if not PYQT_AVAILABLE or not self.app:
            # Fallback: estimate screen width
            try:
                import tkinter as tk
                root = tk.Tk()
                width = root.winfo_screenwidth()
                root.destroy()
                return int(width * screen_percentage)
            except:
                return int(1920 * screen_percentage)  # Assume 1920x1080
            
        screen = self.app.primaryScreen()
        if not screen:
            return int(1200 * screen_percentage)
            
        screen_geometry = screen.availableGeometry()
        return int(screen_geometry.width() * screen_percentage)
    
    def get_responsive_height(self, screen_percentage=0.8):
        """Get responsive height based on screen size"""
        if not PYQT_AVAILABLE or not self.app:
            # Fallback: estimate screen height
            try:
                import tkinter as tk
                root = tk.Tk()
                height = root.winfo_screenheight()
                root.destroy()
                return int(height * screen_percentage)
            except:
                return int(1080 * screen_percentage)  # Assume 1920x1080
            
        screen = self.app.primaryScreen()
        if not screen:
            return int(800 * screen_percentage)
            
        screen_geometry = screen.availableGeometry()
        return int(screen_geometry.height() * screen_percentage)
    
    def get_minimum_window_size(self):
        """Get minimum window size that works on all screens"""
        screen = self.app.primaryScreen() if self.app else None
        if not screen:
            return QSize(1000, 600)
            
        screen_geometry = screen.availableGeometry()
        
        # Minimum should be 70% of screen size, but not less than 800x600
        min_width = max(800, int(screen_geometry.width() * 0.7))
        min_height = max(600, int(screen_geometry.height() * 0.7))
        
        return QSize(min_width, min_height)
    
    def apply_adaptive_sizing(self, widget):
        """Apply adaptive sizing to a widget and its children"""
        # This will be implemented to recursively adjust widget sizes
        pass

# Global instance
_adaptive_ui = None

def get_adaptive_ui():
    """Get global AdaptiveUI instance"""
    global _adaptive_ui
    if _adaptive_ui is None:
        _adaptive_ui = AdaptiveUI()
    return _adaptive_ui

def get_scaled_size(width, height=None):
    """Convenience function to get scaled size"""
    return get_adaptive_ui().get_scaled_size(width, height)

def get_scaled_value(value):
    """Convenience function to get scaled value"""
    return get_adaptive_ui().get_scaled_value(value)

def get_scaled_font_size(base_size=None):
    """Convenience function to get scaled font size"""
    return get_adaptive_ui().get_scaled_font_size(base_size)