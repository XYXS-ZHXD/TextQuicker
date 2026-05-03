"""
TextQuicker - 文字快捷输入工具
功能：快捷键呼出、文字片段管理、分类管理、图标、窗口记忆、双击输入
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
import time
import ctypes

# ── 依赖检测 ────────────────────────────────
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ── 路径 ────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(APP_DIR, "textquicker_data.json")
CONFIG_FILE = os.path.join(APP_DIR, "textquicker_config.json")

# ── 默认值 ──────────────────────────────────
DEFAULT_CONFIG = {
    "hotkey": "ctrl+alt+space",
    "auto_paste": True,
    "window_geometry": "640x520",
    "window_maximized": False,
}

DEFAULT_SNIPPETS = [
    {"id": 1, "category": "问候语", "title": "你好", "content": "你好！有什么可以帮助你的吗？"},
    {"id": 2, "category": "问候语", "title": "感谢", "content": "非常感谢您的支持！"},
    {"id": 3, "category": "工作用语", "title": "收到", "content": "收到，我会尽快处理的，请放心。"},
    {"id": 4, "category": "工作用语", "title": "稍等", "content": "请稍等，我马上为您处理。"},
    {"id": 5, "category": "示例", "title": "个人介绍", "content": "您好，我是TextQuicker用户，很高兴认识您！"},
]

# ── 图标设置 ────────────────────────────────
def set_window_icon(widget):
    """给 tk.Tk / tk.Toplevel 设置图标"""
    try:
        img = tk.PhotoImage(width=32, height=32)
        for x in range(32):
            for y in range(32):
                dist = ((x-16)**2 + (y-16)**2) ** 0.5
                if dist < 14:
                    img.put('#2196F3', (x, y))
        widget._icon_img = img
        widget.iconphoto(True, img)
    except Exception as e:
        print(f"[TextQuicker] Icon error: {e}")

# ── 数据存储（原子写入）──────────────────────
def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[TextQuicker] 读取 {path} 失败: {e}")
    return default.copy()

def save_json(path, data):
    """原子写入：先写 .tmp 再 rename，防止崩溃丢数据"""
    try:
        tmp_path = path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)  # 原子操作
    except Exception as e:
        print(f"[TextQuicker] 写入 {path} 失败: {e}")

def load_config():
    return load_json(CONFIG_FILE, DEFAULT_CONFIG.copy())

def save_config(c):
    save_json(CONFIG_FILE, c)

def load_snippets():
    return load_json(DATA_FILE, DEFAULT_SNIPPETS.copy())

def save_snippets(s):
    save_json(DATA_FILE, s)

def next_id(snippets):
    return max((s.get('id', 0) for s in snippets), default=0) + 1

# ── 剪贴板 & 粘贴 ─────────────────────────────
def copy_to_clipboard(text, root=None):
    """复制文本到剪贴板。优先 pyperclip，fallback 到 tkinter（复用 root 窗口避免泄漏）"""
    if HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"[TextQuicker] pyperclip 复制失败: {e}")
    try:
        if root is not None:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        else:
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(text)
            r.update()
            r.destroy()
        return True
    except Exception as e:
        print(f"[TextQuicker] tkinter 复制失败: {e}")
    return False

def simulate_paste():
    time.sleep(0.15)
    if HAS_KEYBOARD:
        try:
            keyboard.send('ctrl+v')
            return
        except Exception as e:
            print(f"[TextQuicker] keyboard 粘贴失败: {e}")
    try:
        VK_CONTROL, VK_V, KEYUP = 0x11, 0x56, 0x0002
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    except Exception as e:
        print(f"[TextQuicker] ctypes 粘贴失败: {e}")

# ────────────────────────────────────────────────
#  对话框：新建/编辑分类
# ────────────────────────────────────────────────
class CategoryDialog(tk.Toplevel):
    def __init__(self, parent, title="新建分类", old_name=""):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.geometry("330x130")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg='#f5f5f5')
        set_window_icon(self)

        tk.Label(self, text="分类名称：", bg='#f5f5f5', font=('Microsoft YaHei', 11)).pack(pady=(18, 4))
        self.var = tk.StringVar(value=old_name)
        self.entry = tk.Entry(self, textvariable=self.var, width=26, font=('Microsoft YaHei', 11), relief='solid', bd=1)
        self.entry.pack()
        self.entry.select_range(0, 'end')
        self.entry.focus_set()
        self.entry.bind('<Return>', lambda e: self._ok())
        self.entry.bind('<Escape>', lambda e: self.destroy())

        frm = tk.Frame(self, bg='#f5f5f5')
        frm.pack(pady=12)
        tk.Button(frm, text="  确 定  ", bg='#4CAF50', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10, 'bold'), cursor='hand2', command=self._ok).pack(side='left', padx=8, ipadx=4)
        tk.Button(frm, text="  取 消  ", bg='#9E9E9E', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2', command=self.destroy).pack(side='left', padx=4, ipadx=4)
        self._center()

    def _ok(self):
        v = self.var.get().strip()
        if not v:
            messagebox.showwarning("提示", "名称不能为空", parent=self)
            return
        self.result = v
        self.destroy()

    def _center(self):
        self.update_idletasks()
        self.geometry("+{}+{}".format(
            self.master.winfo_rootx() + self.master.winfo_width()//2 - 165,
            self.master.winfo_rooty() + self.master.winfo_height()//2 - 65
        ))

# ────────────────────────────────────────────────
#  对话框：新建/编辑文字片段
# ────────────────────────────────────────────────
class SnippetDialog(tk.Toplevel):
    def __init__(self, parent, categories, snippet=None):
        super().__init__(parent)
        self.result = None
        self.is_edit = snippet is not None
        self.snippet = snippet or {}
        self.categories = list(categories)
        self.unsaved = False

        self.title("编辑文字片段" if self.is_edit else "新建文字片段")
        self.geometry("540x480")
        self.minsize(400, 350)
        self.transient(parent)
        self.grab_set()
        self.configure(bg='#f5f5f5')
        set_window_icon(self)
        self._build_ui()
        self._center()
        self.wait_window()

    def _build_ui(self):
        # 【关键】先打包底部按钮，固定在窗口底部，始终可见
        btn_bg = tk.Frame(self, bg='#e0e0e0', height=50)
        btn_bg.pack(fill='x', side='bottom')
        btn_bg.pack_propagate(False)

        btn_frm = tk.Frame(btn_bg, bg='#e0e0e0')
        btn_frm.pack(expand=True)
        tk.Button(btn_frm, text="  ✔  保 存  ", bg='#4CAF50', fg='white', relief='flat',
                  font=('Microsoft YaHei', 11, 'bold'), cursor='hand2',
                  activebackground='#388E3C', command=self._save).pack(side='left', padx=10, ipadx=6, ipady=3)
        tk.Button(btn_frm, text="  取 消  ", bg='#9E9E9E', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  activebackground='#616161', command=self.destroy).pack(side='left', padx=4, ipadx=6, ipady=3)

        # 内容区（可以扩展）
        frm3 = tk.Frame(self, bg='#f5f5f5')
        frm3.pack(fill='both', expand=True, padx=14, pady=(4, 2))
        tk.Label(frm3, text="内容：", bg='#f5f5f5', width=8, anchor='ne').pack(side='left', anchor='n', pady=2)
        txt_frame = tk.Frame(frm3, relief='solid', bd=1)
        txt_frame.pack(side='left', fill='both', expand=True)
        self.content_text = tk.Text(txt_frame, wrap='word', font=('Microsoft YaHei', 11), bd=0)
        self.content_text.pack(side='left', fill='both', expand=True)
        self.content_text.insert('1.0', self.snippet.get('content', ''))
        sb = ttk.Scrollbar(txt_frame, command=self.content_text.yview)
        sb.pack(side='right', fill='y')
        self.content_text.config(yscrollcommand=sb.set)

        # 标题行
        frm2 = tk.Frame(self, bg='#f5f5f5')
        frm2.pack(fill='x', padx=14, pady=4, before=frm3)
        tk.Label(frm2, text="标题：", bg='#f5f5f5', width=8, anchor='e').pack(side='left')
        self.title_var = tk.StringVar(value=self.snippet.get('title', ''))
        tk.Entry(frm2, textvariable=self.title_var, width=36,
                 font=('Microsoft YaHei', 11), relief='solid', bd=1).pack(side='left', fill='x', expand=True)

        # 分类行
        frm1 = tk.Frame(self, bg='#f5f5f5')
        frm1.pack(fill='x', padx=14, pady=(10, 2), before=frm2)
        tk.Label(frm1, text="分类：", bg='#f5f5f5', width=8, anchor='e').pack(side='left')
        self.cat_var = tk.StringVar(value=self.snippet.get('category', ''))
        self.cat_cb = ttk.Combobox(frm1, textvariable=self.cat_var, values=self.categories, width=24, state='normal')
        self.cat_cb.pack(side='left', padx=(0, 6))
        tk.Button(frm1, text="＋ 新建", bg='#2196F3', fg='white', relief='flat',
                  font=('Microsoft YaHei', 9), cursor='hand2', command=self._new_cat).pack(side='left', padx=2)
        tk.Button(frm1, text="✏ 改名", bg='#FF9800', fg='white', relief='flat',
                  font=('Microsoft YaHei', 9), cursor='hand2', command=self._rename_cat).pack(side='left', padx=2)
        tk.Button(frm1, text="🗑 删除", bg='#f44336', fg='white', relief='flat',
                  font=('Microsoft YaHei', 9), cursor='hand2', command=self._del_cat).pack(side='left', padx=2)

        # 键盘快捷键
        self.bind('<Return>', lambda e: self._save())
        self.bind('<Escape>', lambda e: self.destroy())
        self.title_var.trace_add('write', lambda *a: self._mark_unsaved())
        self.content_text.bind('<KeyRelease>', lambda e: self._mark_unsaved())

    def _mark_unsaved(self):
        self.unsaved = True

    def _new_cat(self):
        dlg = CategoryDialog(self, "新建分类")
        if dlg.result:
            name = dlg.result
            if name in self.categories:
                messagebox.showwarning("提示", "分类「{}」已存在".format(name), parent=self)
                return
            self.categories.append(name)
            self.categories.sort()
            self.cat_cb['values'] = self.categories
            self.cat_var.set(name)

    def _rename_cat(self):
        old = self.cat_var.get().strip()
        if not old:
            messagebox.showinfo("提示", "请先输入或选择一个分类名", parent=self)
            return
        dlg = CategoryDialog(self, "重命名分类", old)
        if dlg.result and dlg.result != old:
            new_name = dlg.result
            if new_name in self.categories:
                messagebox.showwarning("提示", "分类「{}」已存在".format(new_name), parent=self)
                return
            idx = self.categories.index(old)
            self.categories[idx] = new_name
            self.categories.sort()
            self.cat_cb['values'] = self.categories
            self.cat_var.set(new_name)

    def _del_cat(self):
        cat = self.cat_var.get().strip()
        if not cat:
            messagebox.showinfo("提示", "请先输入或选择一个分类名", parent=self)
            return
        if messagebox.askyesno("确认", "确定删除分类「{}」吗？\n（该分类下的文字片段不会被删除）".format(cat), parent=self):
            self.categories.remove(cat)
            self.cat_cb['values'] = self.categories
            self.cat_var.set('')

    def _save(self):
        cat = self.cat_var.get().strip()
        title = self.title_var.get().strip()
        content = self.content_text.get('1.0', 'end-1c').strip()
        if not title:
            messagebox.showwarning("提示", "请填写标题", parent=self)
            return
        if not content:
            messagebox.showwarning("提示", "请填写内容", parent=self)
            return
        self.result = {
            'id': self.snippet.get('id', -1),
            'category': cat or '未分类',
            'title': title,
            'content': content,
        }
        self.unsaved = False
        self.destroy()

    def destroy(self):
        if self.unsaved:
            if not messagebox.askyesno("提示", "内容尚未保存，确定要关闭吗？", parent=self):
                return
        super().destroy()

    def _center(self):
        self.update_idletasks()
        self.geometry("+{}+{}".format(
            self.master.winfo_rootx() + self.master.winfo_width()//2 - 270,
            self.master.winfo_rooty() + self.master.winfo_height()//2 - 240
        ))

# ────────────────────────────────────────────────
#  对话框：录制快捷键
# ────────────────────────────────────────────────
class HotkeyDialog(tk.Toplevel):
    _TK_TO_KB = {
        'space': 'space', 'return': 'enter', 'escape': 'esc', 'tab': 'tab',
        'backspace': 'backspace', 'delete': 'delete',
        'prior': 'page up', 'next': 'page down', 'home': 'home', 'end': 'end',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
        'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4', 'f5': 'f5', 'f6': 'f6',
        'f7': 'f7', 'f8': 'f8', 'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
        'insert': 'insert',
    }
    _MOD_MAP = {
        'control_l': 'ctrl', 'control_r': 'ctrl', 'control': 'ctrl',
        'shift_l': 'shift', 'shift_r': 'shift', 'shift': 'shift',
        'alt_l': 'alt', 'alt_r': 'alt', 'alt': 'alt',
        'meta_l': 'alt', 'meta_r': 'alt',
    }

    def __init__(self, parent, current_hotkey):
        super().__init__(parent)
        self.result = None
        self.current = current_hotkey
        self._mods = set()
        self._recorded = ''
        self._recording = False

        self.title("录制全局快捷键")
        self.geometry("440x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg='#f5f5f5')
        set_window_icon(self)
        self._build_ui()
        self._center()
        # 窗口显示后立即开始录制，不额外延迟
        self.after(10, self._start_recording)
        self.wait_window()

    def _build_ui(self):
        tk.Label(self, text="录制全局快捷键", font=('Microsoft YaHei', 14, 'bold'),
                 bg='#f5f5f5').pack(pady=(18, 2))
        tk.Label(self, text="点击下方输入框，然后直接按下快捷键组合\n（需包含 Ctrl / Alt / Shift 中至少一个）",
                 bg='#f5f5f5', fg='#555', font=('Microsoft YaHei', 9)).pack()

        self.display_var = tk.StringVar(value=self.current.upper())
        self.rec_entry = tk.Entry(self, textvariable=self.display_var,
                                  font=('Consolas', 14, 'bold'),
                                  justify='center', state='readonly',
                                  readonlybackground='#e3f2fd',
                                  relief='solid', bd=2)
        self.rec_entry.pack(pady=14, ipady=6, ipadx=4, fill='x', padx=60)

        self.hint_var = tk.StringVar(value="▶ 正在监听按键，请按下快捷键…")
        self.hint_lbl = tk.Label(self, textvariable=self.hint_var,
                                  bg='#f5f5f5', fg='#1976D2',
                                  font=('Microsoft YaHei', 9))
        self.hint_lbl.pack()

        frm = tk.Frame(self, bg='#f5f5f5')
        frm.pack(pady=18)
        tk.Button(frm, text="  ✔  确 定  ", bg='#2196F3', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10, 'bold'), cursor='hand2',
                  command=self._ok).pack(side='left', padx=8, ipadx=6, ipady=2)
        tk.Button(frm, text="  重 录  ", bg='#FF9800', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  command=self._start_recording).pack(side='left', padx=4, ipadx=4, ipady=2)
        tk.Button(frm, text="  取 消  ", bg='#9E9E9E', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  command=self.destroy).pack(side='left', padx=4, ipadx=4, ipady=2)

        self.bind('<KeyPress>', self._on_press)
        self.bind('<KeyRelease>', self._on_release)
        self.rec_entry.bind('<Button-1>', lambda e: self._start_recording())

    def _start_recording(self):
        self._mods = set()
        self._recorded = ''
        self._recording = True
        self.hint_var.set("▶ 正在监听按键，请按下快捷键…")
        self.hint_lbl.config(fg='#1976D2')
        self.display_var.set("…")
        self.focus_force()

    def _on_press(self, e):
        if not self._recording:
            return
        ks = e.keysym.lower()
        mod = self._MOD_MAP.get(ks)
        if mod:
            self._mods.add(mod)
            parts = sorted(self._mods)
            self.display_var.set('+'.join(p.upper() for p in parts) + '+…')
            return 'break'
        if ks in self._TK_TO_KB:
            key = self._TK_TO_KB[ks]
        elif len(ks) == 1:
            key = ks
        else:
            key = ks
        if not self._mods:
            self.hint_var.set("⚠ 请同时按下 Ctrl / Alt / Shift 中的至少一个修饰键")
            self.hint_lbl.config(fg='#f44336')
            return 'break'
        parts = sorted(self._mods)
        parts.append(key)
        combo = '+'.join(parts)
        self._recorded = combo
        self.display_var.set(combo.upper())
        self._recording = False
        self.hint_var.set("✔ 已录制：{}  （点确定保存）".format(combo.upper()))
        self.hint_lbl.config(fg='#4CAF50')
        return 'break'

    def _on_release(self, e):
        mod = self._MOD_MAP.get(e.keysym.lower())
        if mod:
            self._mods.discard(mod)

    def _ok(self):
        v = (self._recorded or self.display_var.get()).strip()
        if not v or v == '…' or '+' not in v:
            messagebox.showwarning("提示", "请先录制一个有效快捷键", parent=self)
            return
        self.result = v.lower()
        self.destroy()

    def _center(self):
        self.update_idletasks()
        self.geometry("+{}+{}".format(
            self.master.winfo_rootx() + self.master.winfo_width()//2 - 220,
            self.master.winfo_rooty() + self.master.winfo_height()//2 - 140
        ))

# ────────────────────────────────────────────────
#  主程序
# ────────────────────────────────────────────────
class TextQuickerApp:
    def __init__(self):
        self.config = load_config()
        self.snippets = load_snippets()
        self._hotkey_registered = False
        self._prev_hwnd = None
        self._geom_timer = None  # P0: 防抖计时器

        self.root = tk.Tk()
        self.root.title("TextQuicker 文字快捷输入")
        self.root.minsize(500, 400)
        self.root.configure(bg='#ffffff')
        set_window_icon(self.root)

        # 恢复窗口大小和位置
        geom = self.config.get('window_geometry', '640x520')
        try:
            self.root.geometry(geom)
        except Exception:
            self.root.geometry('640x520')

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind('<Escape>', lambda e: self.root.withdraw())
        # P0: 窗口大小变化时保存（带防抖）
        self.root.bind('<Configure>', self._on_configure)

        self._build_ui()
        self._refresh_list()
        self._register_hotkey()
        self._setup_tray()
        self.root.after(100, self._minimize_to_tray)

    def _on_configure(self, event):
        # P0 fix: 只处理主窗口事件，500ms 防抖
        if event.widget == self.root:
            if self._geom_timer:
                self.root.after_cancel(self._geom_timer)
            self._geom_timer = self.root.after(500, self._save_geometry)

    def _save_geometry(self):
        try:
            if self.root.state() == 'normal':
                self.config['window_geometry'] = self.root.geometry()
                save_config(self.config)
        except Exception as e:
            print(f"[TextQuicker] 保存窗口位置失败: {e}")

    # ── UI ─────────────────────────────────────
    def _build_ui(self):
        # 顶部工具栏
        tb = tk.Frame(self.root, bg='#2196F3', height=46)
        tb.pack(fill='x')
        tb.pack_propagate(False)
        tk.Label(tb, text="⚡ TextQuicker", fg='white', bg='#2196F3',
                 font=('Microsoft YaHei', 13, 'bold')).pack(side='left', padx=14)
        tk.Button(tb, text="＋ 新建片段", bg='#1976D2', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  activebackground='#1565C0', command=self._new_snippet).pack(side='right', padx=4, pady=8)
        tk.Button(tb, text="⚙ 设置", bg='#1976D2', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  activebackground='#1565C0', command=self._open_settings).pack(side='right', padx=4, pady=8)

        # 搜索 + 分类过滤
        filter_frm = tk.Frame(self.root, bg='#f5f5f5')
        filter_frm.pack(fill='x', padx=10, pady=(6, 2))
        tk.Label(filter_frm, text="🔍", bg='#f5f5f5', font=('', 12)).pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        tk.Entry(filter_frm, textvariable=self.search_var, font=('Microsoft YaHei', 10),
                 relief='solid', bd=1).pack(side='left', fill='x', expand=True, padx=(4, 10))
        tk.Label(filter_frm, text="分类：", bg='#f5f5f5', font=('Microsoft YaHei', 10)).pack(side='left')
        self.cat_var = tk.StringVar(value='全部')
        self.cat_cb = ttk.Combobox(filter_frm, textvariable=self.cat_var, state='readonly', width=14)
        self.cat_cb.pack(side='left', padx=2)
        self.cat_cb.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())

        # 列表
        list_frm = tk.Frame(self.root, bg='white')
        list_frm.pack(fill='both', expand=True, padx=10, pady=2)
        cols = ('cat', 'title', 'preview')
        self.tree = ttk.Treeview(list_frm, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('cat', text='分类')
        self.tree.heading('title', text='标题')
        self.tree.heading('preview', text='内容预览')
        self.tree.column('cat', width=80, minwidth=60, stretch=False)
        self.tree.column('title', width=120, minwidth=80, stretch=False)
        self.tree.column('preview', width=300, minwidth=100)
        vsb = ttk.Scrollbar(list_frm, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.tree.pack(side='left', fill='both', expand=True)
        # 双击触发输入（改回双击，避免单击无法选中编辑的问题）
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # 预览区
        prev_frm = tk.LabelFrame(self.root, text=" 内容预览 ", bg='white', font=('Microsoft YaHei', 9))
        prev_frm.pack(fill='x', padx=10, pady=2)
        self.preview_text = tk.Text(prev_frm, height=3, wrap='word', font=('Microsoft YaHei', 10),
                                     relief='flat', state='disabled', bg='#f8f8f8')
        self.preview_text.pack(fill='x', padx=4, pady=2)

        # 底部操作栏
        bot = tk.Frame(self.root, bg='#f0f0f0', pady=6)
        bot.pack(fill='x')
        self.status_var = tk.StringVar(value="快捷键: {}".format(self.config['hotkey'].upper()))
        tk.Label(bot, textvariable=self.status_var, bg='#f0f0f0', fg='#666', font=('Microsoft YaHei', 9)).pack(side='left', padx=10)
        tk.Button(bot, text="📋 复制+粘贴", bg='#4CAF50', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10, 'bold'), cursor='hand2',
                  activebackground='#388E3C', command=self._use_selected).pack(side='right', padx=6)
        tk.Button(bot, text="✏ 编辑", bg='#FF9800', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  activebackground='#E65100', command=self._edit_selected).pack(side='right', padx=2)
        tk.Button(bot, text="🗑 删除", bg='#f44336', fg='white', relief='flat',
                  font=('Microsoft YaHei', 10), cursor='hand2',
                  activebackground='#b71c1c', command=self._delete_selected).pack(side='right', padx=2)

    # ── 双击输入 ──────────────────────────────
    def _on_double_click(self, event):
        # 检查是否双击在行上
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._use_selected()

    # ── 数据 ───────────────────────────────────
    def _get_categories(self):
        cats = sorted(set(s.get('category', '未分类') for s in self.snippets))
        return ['全部'] + cats

    def _refresh_list(self):
        cats = self._get_categories()
        self.cat_cb['values'] = cats
        if self.cat_var.get() not in cats:
            self.cat_var.set('全部')
        sel_cat = self.cat_var.get()
        kw = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for s in self.snippets:
            cat = s.get('category', '未分类')
            if sel_cat != '全部' and cat != sel_cat:
                continue
            if kw and kw not in cat.lower() and kw not in s.get('title', '').lower() and kw not in s.get('content', '').lower():
                continue
            preview = s.get('content', '').replace('\n', ' ')[:60]
            if len(s.get('content', '')) > 60:
                preview += '…'
            self.tree.insert('', 'end', iid=str(s['id']), values=(cat, s.get('title', ''), preview))
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            self._update_preview(children[0])

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            self._update_preview(sel[0])

    def _update_preview(self, iid):
        try:
            s = next(s for s in self.snippets if str(s['id']) == str(iid))
            self.preview_text.config(state='normal')
            self.preview_text.delete('1.0', 'end')
            self.preview_text.insert('1.0', s.get('content', ''))
            self.preview_text.config(state='disabled')
        except StopIteration:
            pass

    # ── 片段操作 ───────────────────────────────
    def _new_snippet(self):
        cats = [c for c in self._get_categories() if c != '全部']
        dlg = SnippetDialog(self.root, categories=cats)
        if dlg.result:
            dlg.result['id'] = next_id(self.snippets)
            self.snippets.append(dlg.result)
            save_snippets(self.snippets)
            self._refresh_list()

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self.root)
            return
        s = next((s for s in self.snippets if str(s['id']) == str(sel[0])), None)
        if not s:
            return
        cats = [c for c in self._get_categories() if c != '全部']
        dlg = SnippetDialog(self.root, categories=cats, snippet=s.copy())
        if dlg.result:
            dlg.result['id'] = s['id']
            idx = next(i for i, x in enumerate(self.snippets) if x['id'] == s['id'])
            self.snippets[idx] = dlg.result
            save_snippets(self.snippets)
            self._refresh_list()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self.root)
            return
        s = next((s for s in self.snippets if str(s['id']) == str(sel[0])), None)
        if not s:
            return
        if messagebox.askyesno("确认删除", "确定删除「{}」吗？".format(s['title']), parent=self.root):
            self.snippets = [x for x in self.snippets if x['id'] != s['id']]
            save_snippets(self.snippets)
            self._refresh_list()

    def _use_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条记录", parent=self.root)
            return
        s = next((x for x in self.snippets if str(x['id']) == str(sel[0])), None)
        if not s:
            return
        self.root.withdraw()
        if HAS_WIN32:
            try:
                win32gui.SetForegroundWindow(self._prev_hwnd)
            except Exception as e:
                print(f"[TextQuicker] 恢复前台窗口失败: {e}")
        time.sleep(0.1)
        # P1: 复用 root 窗口，避免每次 new Tk()
        copy_to_clipboard(s.get('content', ''), root=self.root)
        if self.config.get('auto_paste', True):
            threading.Thread(target=simulate_paste, daemon=True).start()

    # ── 快捷键 ─────────────────────────────────
    def _register_hotkey(self):
        if not HAS_KEYBOARD:
            return
        try:
            if self._hotkey_registered:
                try:
                    keyboard.remove_hotkey(self._handler)
                except Exception:
                    keyboard.unhook_all_hotkeys()
            self._handler = keyboard.add_hotkey(self.config['hotkey'], self._toggle, suppress=True)
            self._hotkey_registered = True
            self.status_var.set("快捷键: {}  ✓".format(self.config['hotkey'].upper()))
        except Exception as e:
            self.status_var.set("快捷键注册失败: {}".format(e))
            print(f"[TextQuicker] 注册快捷键失败: {e}")

    def _toggle(self):
        self.root.after(0, self._do_toggle)

    def _do_toggle(self):
        if self.root.state() == 'withdrawn' or not self.root.winfo_viewable():
            self._show()
        else:
            self.root.withdraw()

    def _show(self):
        if HAS_WIN32:
            try:
                self._prev_hwnd = win32gui.GetForegroundWindow()
            except Exception as e:
                print(f"[TextQuicker] 获取前台窗口失败: {e}")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.search_var.set('')
        self._refresh_list()

    def _minimize_to_tray(self):
        self.root.withdraw()

    # ── 设置 ───────────────────────────────────
    def _open_settings(self):
        dlg = HotkeyDialog(self.root, self.config['hotkey'])
        if dlg.result and dlg.result != self.config['hotkey']:
            self.config['hotkey'] = dlg.result
            save_config(self.config)
            self._register_hotkey()

    # ── 托盘 ───────────────────────────────────
    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            # 画一个简单的 TQ 图标
            img = Image.new('RGBA', (64, 64), (33, 150, 243, 255))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(33, 150, 243, 255))
            d.text((12, 10), "TQ", fill='white')
            menu = pystray.Menu(
                pystray.MenuItem('显示 TextQuicker', lambda icon, item: self.root.after(0, self._show), default=True),
                pystray.MenuItem('设置快捷键', lambda icon, item: self.root.after(0, self._open_settings)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('退出', self._quit_app),
            )
            self.tray = pystray.Icon("TextQuicker", img, "TextQuicker", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except ImportError as e:
            print(f"[TextQuicker] 托盘图标不可用（需安装 pystray + Pillow）: {e}")
            self.tray = None

    # ── 生命周期 ───────────────────────────────
    def _on_close(self):
        self._save_geometry()
        if self.tray:
            self.root.withdraw()
        else:
            self._quit_app()

    def _quit_app(self, icon=None, item=None):
        self._save_geometry()
        try:
            if self.tray:
                self.tray.stop()
        except Exception as e:
            print(f"[TextQuicker] 停止托盘失败: {e}")
        if HAS_KEYBOARD and self._hotkey_registered:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception as e:
                print(f"[TextQuicker] 卸载快捷键失败: {e}")
        self.root.destroy()

    def run(self):
        self.root.mainloop()

# ── 入口 ──────────────────────────────────────
def main():
    missing = []
    if not HAS_KEYBOARD:
        missing.append("keyboard")
    if not HAS_PYPERCLIP:
        missing.append("pyperclip")
    if missing:
        r = tk.Tk()
        r.withdraw()
        messagebox.showwarning("依赖提示", "缺少库：{}\n请运行：pip install {}".format(', '.join(missing), ' '.join(missing)))
        r.destroy()
    app = TextQuickerApp()
    app.run()

if __name__ == '__main__':
    main()
