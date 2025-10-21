#!/usr/bin/env python3
"""
Test script for adaptive UI sizing
Run this to test the UI on different screen configurations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize
from main import MainWindow
from services.adaptive_ui import get_adaptive_ui

def test_adaptive_ui():
    """Test adaptive UI with different screen configurations"""
    app = QApplication(sys.argv)
    
    # Get adaptive UI info
    adaptive_ui = get_adaptive_ui()
    
    print("=== Adaptive UI Test ===")
    print(f"Scale Factor: {adaptive_ui.scale_factor:.2f}")
    print(f"Base Font Size: {adaptive_ui.get_scaled_font_size()}pt")
    print(f"Responsive Width: {adaptive_ui.get_responsive_width()}")
    print(f"Responsive Height: {adaptive_ui.get_responsive_height()}")
    print(f"Minimum Window Size: {adaptive_ui.get_minimum_window_size().width()}x{adaptive_ui.get_minimum_window_size().height()}")
    
    # Test different font sizes
    print("\n=== Font Size Tests ===")
    for base_size in [8, 9, 10, 11, 12, 14, 16]:
        scaled = adaptive_ui.get_scaled_font_size(base_size)
        print(f"Base {base_size}pt -> Scaled {scaled}pt")
    
    # Test different widget sizes
    print("\n=== Widget Size Tests ===")
    test_sizes = [(100, 30), (200, 40), (300, 50), (400, 60)]
    for width, height in test_sizes:
        scaled = adaptive_ui.get_scaled_size(width, height)
        print(f"Base {width}x{height} -> Scaled {scaled.width()}x{scaled.height()}")
    
    # Create and show main window
    print("\n=== Creating Main Window ===")
    window = MainWindow()
    window.show()
    
    # Print actual window size
    actual_size = window.size()
    print(f"Actual window size: {actual_size.width()}x{actual_size.height()}")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_adaptive_ui())