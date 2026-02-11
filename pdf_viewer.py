"""
Utility functions for opening PDFs at specific pages.
Supports Windows (SumatraPDF, Adobe), macOS (Preview), and Linux (evince, okular).
"""

import sys
import os
import subprocess
import platform


def get_app_dir():
    """Get the directory where the app is running from."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def open_pdf_at_page(pdf_path: str, page_num: int):
    """Open PDF at specific page using bundled or system PDF viewer."""
    system = platform.system()
    pdf_path = os.path.abspath(pdf_path)
    
    if system == "Windows":
        app_dir = get_app_dir()
        bundled_sumatra_paths = [
            os.path.join(app_dir, "_internal", "SumatraPDF", "SumatraPDF.exe"),
            os.path.join(app_dir, "_internal", "SumatraPDF.exe"),
            os.path.join(app_dir, "SumatraPDF", "SumatraPDF.exe"),
            os.path.join(app_dir, "SumatraPDF.exe"),
        ]
        
        for sumatra in bundled_sumatra_paths:
            if os.path.exists(sumatra):
                subprocess.Popen([sumatra, "-page", str(page_num), pdf_path])
                return True
        
        sumatra_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
        ]
        
        for sumatra in sumatra_paths:
            if os.path.exists(sumatra):
                subprocess.Popen([sumatra, "-page", str(page_num), pdf_path])
                return True
        
        adobe_paths = [
            r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        ]
        
        for adobe in adobe_paths:
            if os.path.exists(adobe):
                subprocess.Popen([adobe, "/A", f"page={page_num}", pdf_path])
                return True
        
        os.startfile(pdf_path)
        return False
        
    elif system == "Darwin":
        script = f'''
        tell application "Preview"
            open POSIX file "{pdf_path}"
            activate
        end tell
        delay 0.5
        tell application "System Events"
            keystroke "g" using {{option down, command down}}
            delay 0.2
            keystroke "{page_num}"
            keystroke return
        end tell
        '''
        subprocess.Popen(["osascript", "-e", script])
        return True
        
    else:
        viewers = [
            (["evince", "-p", str(page_num), pdf_path], "evince"),
            (["okular", "-p", str(page_num), pdf_path], "okular"),
            (["xdg-open", pdf_path], "xdg-open"),
        ]
        
        for cmd, name in viewers:
            try:
                subprocess.Popen(cmd)
                return name != "xdg-open"
            except FileNotFoundError:
                continue
        
        return False
