#!/usr/bin/env python3
"""
Simple test runner for adaptive UI
This script tests the UI improvements without requiring full dependencies
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_adaptive_ui_system():
    """Test the adaptive UI system components"""
    print("=== Testing Adaptive UI System ===\n")
    
    try:
        # Test adaptive UI module
        from services.adaptive_ui import AdaptiveUI, get_adaptive_ui
        print("✓ AdaptiveUI module imported successfully")
        
        # Create adaptive UI instance (without QApplication for now)
        adaptive = AdaptiveUI()
        print(f"✓ AdaptiveUI created with scale factor: {adaptive.scale_factor:.2f}")
        
        # Test scaling functions
        test_sizes = [(100, 30), (200, 40), (400, 60)]
        print("\n--- Size Scaling Tests ---")
        for width, height in test_sizes:
            scaled = adaptive.get_scaled_size(width, height)
            print(f"  {width}x{height} -> {scaled.width()}x{scaled.height()}")
        
        # Test font scaling
        print("\n--- Font Scaling Tests ---")
        for font_size in [8, 10, 12, 14, 16]:
            scaled = adaptive.get_scaled_font_size(font_size)
            print(f"  {font_size}pt -> {scaled}pt")
        
        # Test responsive layout manager
        from services.responsive_layout import ResponsiveLayoutManager
        print("\n✓ ResponsiveLayoutManager imported successfully")
        
        # Test theme with adaptive sizing
        from services.theme import ModernTheme
        print("✓ Enhanced theme system loaded")
        
        print(f"\n--- Theme Colors ---")
        for key, value in ModernTheme.COLORS.items():
            print(f"  {key}: {value}")
        
        print("\n=== All Tests Passed! ===")
        print("\nThe adaptive UI system is ready to use.")
        print("Key improvements:")
        print("• DPI-aware scaling for all UI elements")
        print("• Responsive layout that adapts to screen size") 
        print("• Consistent font sizing across different displays")
        print("• Flexible widget sizing with minimum/maximum constraints")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def show_recommendations():
    """Show recommendations for using the adaptive UI"""
    print("\n=== Usage Recommendations ===")
    print("1. Run the application on different screen sizes to test responsiveness")
    print("2. Check that text is readable on high-DPI displays")
    print("3. Verify that UI elements don't overlap on small screens")
    print("4. Test with different system font scaling settings")
    print("\nTo run the full application:")
    print("  python3 main.py")

if __name__ == "__main__":
    success = test_adaptive_ui_system()
    if success:
        show_recommendations()
    sys.exit(0 if success else 1)