# TextQuicker - 文字快捷输入工具

快捷键呼出、文字片段管理、分类管理、自动粘贴、窗口记忆。

## 功能

- 全局快捷键（默认 `Ctrl+Alt+Space`）呼出窗口
- 文字片段管理：新建/编辑/删除/搜索
- 分类管理：新建/重命名/删除
- 选中后自动复制到剪贴板并粘贴（可配置）
- 系统托盘图标
- 窗口位置记忆

## 使用

1. 运行 TextQuicker.exe
2. 按 `Ctrl+Alt+Space` 呼出窗口
3. 双击片段自动复制并粘贴到当前窗口

## 打包

```bash
python build_textquicker.py
```

## 依赖

- keyboard
- pyperclip
- pywin32
- pystray + Pillow（可选，用于托盘图标）
