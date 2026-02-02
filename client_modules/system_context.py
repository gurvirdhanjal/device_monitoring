import psutil
import time
import platform

class WindowMonitor:
    """
    Safe Window Title Monitor.
    Only captures foreground window.
    Strictly opt-in, truncated, and crash-safe.
    """
    def get_active_window(self, enabled=False):
        """
        Get the active window title and app name.
        
        Args:
            enabled (bool): Gating flag. If False, returns None immediately.
            
        Returns:
            dict: { 'title': str, 'app_name': str } OR None
        """
        if not enabled:
            return None
            
        # Only support Windows for now
        if platform.system() != 'Windows':
            return None
            
        try:
            import win32gui
            import win32process
            
            window = win32gui.GetForegroundWindow()
            if not window:
                return None
                
            # Get Title
            title = win32gui.GetWindowText(window)
            
            # Get PID and Process Name
            _, pid = win32process.GetWindowThreadProcessId(window)
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"
                
            # Clean and Truncate
            if not title or not title.strip():
                return None # Don't report empty titles
                
            title = title.strip()
            if len(title) > 256:
                title = title[:253] + "..."
                
            return {
                "title": title,
                "app_name": app_name
            }
            
        except ImportError:
            # win32gui not installed or available
            return None
        except Exception:
            # Fail silently to prevent service crash
            return None
