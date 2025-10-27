"""
Utility classes for test scenario execution
"""
import re
import math
from typing import Dict, Any, Optional, List


class EvalContext:
    """Context for variable storage and expression evaluation"""
    
    def __init__(self):
        self.vars = {}
        self.flags = {}
        
    def set_var(self, name: str, value: Any, device=None):
        """Set variable value"""
        # Handle DSL expressions like "[doshell cmd]" or "{var_name}"
        if isinstance(value, str):
            if value.startswith('[') and value.endswith(']'):
                # DSL command expression
                resolved_value = self._resolve_dsl_command(value, device)
                self.vars[name] = resolved_value
            elif value.startswith('{') and value.endswith('}'):
                # Variable reference
                var_name = value[1:-1]
                self.vars[name] = self.vars.get(var_name, 0)
            elif value.startswith('"') and value.endswith('"'):
                # String literal
                self.vars[name] = value[1:-1]
            else:
                # Direct value or expression
                self.vars[name] = self._evaluate_expression(value)
        else:
            self.vars[name] = value
    
    def get_var(self, name: str, default=None):
        """Get variable value"""
        return self.vars.get(name, default)
    
    def resolve(self, expression: str, device=None) -> Any:
        """Resolve DSL expression"""
        if expression.startswith('[') and expression.endswith(']'):
            return self._resolve_dsl_command(expression, device)
        elif expression.startswith('{') and expression.endswith('}'):
            var_name = expression[1:-1]
            return self.vars.get(var_name, 0)
        else:
            return self._evaluate_expression(expression)
    
    def _resolve_dsl_command(self, command: str, device=None) -> Any:
        """Resolve DSL command like [doshell cmd] or [split str delim]"""
        command = command[1:-1]  # Remove [ ]
        
        if command.startswith('doshell '):
            # Execute shell command
            shell_cmd = command[8:]  # Remove 'doshell '
            if device:
                return device.shell(shell_cmd)
            return ""
        elif command.startswith('split '):
            # Split string: [split {var} delimiter]
            parts = command.split(' ', 2)
            if len(parts) >= 3:
                string_expr = parts[1]
                delimiter_expr = parts[2]
                
                string_val = self.resolve(string_expr, device)
                delimiter_val = self.resolve(delimiter_expr, device)
                
                return string_val.split(delimiter_val)
            return []
        elif command.startswith('get '):
            # Get list element: [get {list_var} index]
            parts = command.split(' ', 2)
            if len(parts) >= 3:
                list_expr = parts[1]
                index_expr = parts[2]
                
                list_val = self.resolve(list_expr, device)
                index_val = int(self.resolve(index_expr, device))
                
                if isinstance(list_val, list) and 0 <= index_val < len(list_val):
                    return list_val[index_val]
            return ""
        else:
            # Unknown command
            return command
    
    def _evaluate_expression(self, expr: str) -> Any:
        """Evaluate mathematical expression"""
        if isinstance(expr, str):
            # Replace variable references
            for var_name, var_value in self.vars.items():
                if var_name in expr:
                    expr = expr.replace(f"{{{var_name}}}", str(var_value))
            
            # Try to evaluate as math expression
            try:
                # Simple math operations
                if any(op in expr for op in ['+', '-', '*', '/', '(', ')']):
                    return eval(expr)
                else:
                    # Try to convert to number
                    if '.' in expr:
                        return float(expr)
                    else:
                        return int(expr)
            except:
                return expr
        return expr
    
    def _func(self, func_name: str, *args) -> Any:
        """Execute built-in function"""
        if func_name == "brightness_create":
            # Calculate brightness value based on target lux and model
            target_lux = int(args[0]) if args else 500
            model_factor = int(args[1]) if len(args) > 1 else 6
            
            # Simple brightness calculation (mock)
            brightness = min(255, max(0, int(target_lux / model_factor)))
            return brightness
        
        return 0


class UIAutomationHelper:
    """Helper class for UI automation operations"""
    
    def __init__(self, device):
        self.device = device
        
    def type_text(self, text: str):
        """Type text with proper escaping"""
        self.device.type_text(text)
        self.device.sleep(300)
    
    def click_text(self, pattern: str) -> bool:
        """Click UI element by text pattern"""
        return self.device.click({"textMatches": pattern})
    
    def click_resource_id(self, res_id: str) -> bool:
        """Click UI element by resource ID"""
        return self.device.click({"resourceId": res_id})
    
    def press_key(self, key: str):
        """Press hardware key"""
        self.device.press(key)
    
    def handle_common_dialogs(self) -> bool:
        """Handle common dialog boxes"""
        handled = False
        
        # Common dialog patterns
        dialog_patterns = [
            "(?i)Continue",
            "(?i)Not now", 
            "(?i)Close",
            "(?i)OK",
            "(?i)Cancel",
            "(?i)Agree",
            "(?i)Turn on location"
        ]
        
        for pattern in dialog_patterns:
            if self.click_text(pattern):
                self.device.sleep(1000)
                handled = True
                break
                
        return handled
    
    def wait_and_click(self, selector: Dict[str, Any], timeout: int = 5000) -> bool:
        """Wait for element and click"""
        # Mock implementation - in real scenario would use uiautomator2
        self.device.sleep(min(timeout, 2000))
        return self.device.click(selector)


class CoordinateCalculator:
    """Calculate screen coordinates for UI automation"""
    
    def __init__(self, device):
        self.device = device
        self.screen_x, self.screen_y = device.get_screen_size()
        
    def get_coordinates(self) -> Dict[str, float]:
        """Get calculated coordinates"""
        return {
            "screen_x": self.screen_x,
            "screen_y": self.screen_y,
            "center_x": self.screen_x * 0.5,
            "center_y": self.screen_y * 0.5,
            "right_x": self.screen_x * 0.75,
            "left_x": self.screen_x * 0.25,
            "y_upper": self.screen_y / 5,
            "y_lower": self.screen_y - self.screen_y / 5,
            "home_x": self.screen_x * 0.5,
            "home_y": self.screen_y - 70,  # Home button area
            "back_x": self.screen_x * 0.1,
            "back_y": self.screen_y - 70,  # Back button area
        }
    
    def get_swipe_coordinates(self, direction: str) -> tuple:
        """Get swipe coordinates for different directions"""
        center_x, center_y = self.screen_x // 2, self.screen_y // 2
        
        if direction == "up":
            return (center_x, center_y + 200, center_x, center_y - 200)
        elif direction == "down":
            return (center_x, center_y - 200, center_x, center_y + 200)
        elif direction == "left":
            return (center_x + 200, center_y, center_x - 200, center_y)
        elif direction == "right":
            return (center_x - 200, center_y, center_x + 200, center_y)
        else:
            return (center_x, center_y, center_x, center_y)