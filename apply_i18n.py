#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apollo Save Tool (PS2) — 中文化脚本 / Chinese localization script
===================================================================

在原版 apollo-ps2 仓库根目录运行本脚本即可把界面与功能选项翻译为简体中文，
并把主菜单/关于页等使用位图字体的文字切换到 TTF 渲染（FONT.OTF）以正确显示
中文、日文与繁体中文。

用法 / Usage:
    cd apollo-ps2          # 你的 fork 根目录（含 source/ 与 include/）
    python3 apply_i18n.py

    # 若要把确认/取消按键对调为 ⭕ 确定 / ✕ 返回：
    python3 apply_i18n.py --swap-buttons

说明 / Notes:
    * 本脚本只修改 source/*.c 中的用户可见字符串，不改变逻辑。
    * 渲染中文依赖 DATA/FONT.OTF（含 CJK 字形的 TrueType/OpenType 字体）。
      请把仓库附带的 FONT.OTF 放到 APOLLO/DATA/ 目录下（与 APOLLO.ELF 同级）。
    * 项目本身已经内置 TTF 渲染与字体回退（face[0] -> face[1]=FONT.OTF），
      所以只要提供含中文字形的 FONT.OTF 即可显示中文，无需改动字体加载代码。
"""

import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO, "source")

# 需要把 DrawStringMono（位图字体，无法显示中文）替换为 DrawString（TTF）的文件。
# 注意：
#  - 用负向后顾确保不会误改 DrawFormatStringMono（十六进制编辑器专用，纯 ASCII）。
#  - draw.c 特殊处理：其「加载中」画面运行在独立线程，FreeType 非线程安全，
#    那一行的 DrawStringMono 必须保留（见 apply_file 内的还原逻辑），否则进记忆卡会卡死。
MONO_TO_TTF_FILES = ["draw.c", "menu_about.c"]

# 翻译表： (英文原文, 中文译文)
# 采用『完整引号字符串字面量』精确匹配，因此不受顺序影响，也不会误伤代码标识符。
# 源码中的 \n 写作 \\n，\x10 等转义写作 \\x10（均为文件中的字面字符）。
TRANSLATIONS = [
    # ---------- main.c : 主菜单标题 (save_list.title) ----------
    ("MemCard Saves", "记忆卡存档"),
    ("External Saves", "外部存档"),
    ("Virtual MemCard", "虚拟记忆卡"),
    ("Saves Database", "存档数据库"),
    ("User Tools", "用户工具"),

    # ---------- main.c : 帮助栏 ----------
    ("\\x10 Select    \\x13 Back    \\x12 Details    \\x11 Refresh",
     "\\x10 选择    \\x13 返回    \\x12 详情    \\x11 刷新"),
    ("\\x10 Value Up  \\x11 Value Down   \\x13 Exit",
     "\\x10 上移  \\x11 下移   \\x13 退出"),
    ("\\x10 Select    \\x13 Back    \\x11 Refresh",
     "\\x10 选择    \\x13 返回    \\x11 刷新"),
    ("\\x10 Select    \\x12 View Code    \\x13 Back",
     "\\x10 选择    \\x12 查看代码    \\x13 返回"),
    ("\\x10 Select    \\x13 Back",
     "\\x10 选择    \\x13 返回"),
    ("\\x13 Back",
     "\\x13 返回"),

    # ---------- main.c : 记忆卡选择 / 提示 ----------
    ("Select Memory Card", "选择记忆卡"),
    ("Memory Card 1", "记忆卡 1"),
    ("Memory Card 2", "记忆卡 2"),
    # 注意：加载画面运行在独立线程，FreeType 非线程安全，必须保持位图字体（只能显示拉丁字符），
    # 因此「Loading saves...」故意不翻译，避免中文在该画面显示为方块或触发多线程崩溃。
    ("No save-games found", "未找到存档"),
    ("Exit the app?", "退出程序？"),
    ("Patch view", "补丁查看"),
    ("Save changes to %s?", "保存对 %s 的修改？"),
    ("Unable to load\\n%s", "无法加载\\n%s"),
    ("No data found in folder:\\n%s", "文件夹中未找到数据：\\n%s"),
    ("Successfully installed local application data", "本地应用数据安装成功"),

    # ---------- menu_options.c : 设置页标题 ----------
    ("Settings", "设置"),

    # ---------- menu_about.c : 关于页 ----------
    ("PlayStation 2 version", "PS2 A9VG汉化版"),
    ("In memory of", "纪念"),
    ("About", "关于"),
    ("Developer", "开发者"),
    ("... in memory of Leon & Luna - may your days be filled with eternal joy ...",
     "... 纪念 Leon & Luna — 愿你们的日子充满永恒的欢乐 ..."),

    # ---------- menu_cheats.c ----------
    ("Options", "选项"),
    ("Details", "详情"),
    ("Target File: %s", "目标文件：%s"),
    ("on", "开"),
    ("%ld Saves", "%ld 个存档"),
    ("%ld Games", "%ld 个游戏"),
    ("Tools", "工具"),

    # ---------- dialog.c : 对话框按钮 ----------
    ("\\x10 OK   \\x13 Cancel", "\\x10 确定   \\x13 取消"),
    ("\\x10 OK", "\\x10 确定"),
    ("\\x10 Yes   \\x13 No", "\\x10 是   \\x13 否"),

    # ---------- draw.c : 主菜单底部 jar 标签 ----------
    ("Ext Saves", "外部存档"),
    ("Saves DB", "存档数据库"),
    ("Saves", "存档"),

    # ---------- settings.c : 设置项 ----------
    ("\\nBackground Music", "\\n背景音乐"),
    ("Menu Animations", "菜单动画"),
    ("Sort Saves", "存档排序"),
    ("External Saves Source", "外部存档来源"),
    ("Clear Local Cache", "清除本地缓存"),
    ("Enable Debug Log", "启用调试日志"),
    ("Disabled", "关闭"),
    ("by Name", "按名称"),
    ("by Title ID", "按标题 ID"),
    ("by Type", "按类型"),
    ("Local cache folder cleaned:\\n", "本地缓存已清理：\\n"),
    ("Debug Logging Enabled!\\n\\n", "调试日志已启用！\\n\\n"),
    ("New version available! Download update?", "发现新版本！是否下载更新？"),
    ("Update downloaded to ms0:/APOLLO/apollo-psp.zip", "更新已下载至 ms0:/APOLLO/apollo-psp.zip"),
    ("Download error!", "下载失败！"),

    # ---------- saves.c : 操作命令显示名 ----------
    (" File Backup ", " 文件备份 "),
    (" Save Game Backup ", " 存档备份 "),
    (" Save Transfer ", " 存档传输 "),
    (" Virtual Memory Card ", " 虚拟记忆卡 "),
    (" Copy save files", " 复制存档文件"),
    (" Export save files to Zip", " 导出存档为 Zip"),
    (" Export single save files", " 导出单个存档文件"),
    (" Import single save files", " 导入单个存档文件"),
    (" Hex Edit save game files", " 十六进制编辑存档文件"),
    (" Export save to .MCS format", " 导出存档为 .MCS 格式"),
    (" Export save to .PSX format", " 导出存档为 .PSX 格式"),
    (" Export save to .PSV format", " 导出存档为 .PSV 格式"),
    (" Export save to .PSU format", " 导出存档为 .PSU 格式"),
    (" Export save to .CBS format", " 导出存档为 .CBS 格式"),
    (" Save linked to MemCard ID", " 存档绑定到记忆卡 ID"),
    (" View Save Details", " 查看存档详情"),
    (" Delete Save Game", " 删除存档"),
    (" Cheats ", " 金手指 "),
    (" Apply Changes", " 应用修改"),
    (" View Raw Patch File", " 查看原始补丁文件"),
    (" Import to Memory Card", " 导入到记忆卡"),
    (" Export save game to .MCS format", " 导出存档为 .MCS 格式"),
    (" Export save game to .PSV format", " 导出存档为 .PSV 格式"),
    (" Export save game to .PSX format", " 导出存档为 .PSX 格式"),
    (" Copy save game to Memory Card", " 复制存档到记忆卡"),
    (" Extract Archives (Zip)", " 解压压缩包 (Zip)"),
    (" Local Web Server (full system access)", " 本地网页服务器（完全系统访问）"),
    (" Bulk Save Management", " 批量存档管理"),
    (" Copy selected Saves to Memory Card", " 复制所选存档到记忆卡"),
    (" Copy all Saves to Memory Card", " 复制所有存档到记忆卡"),
    (" Copy selected Saves to Backup Storage", " 复制所选存档到备份存储"),
    (" Copy all Saves to Backup Storage", " 复制所有存档到备份存储"),
    (".PSU Export selected Saves to Backup Storage", ".PSU 导出所选存档到备份存储"),
    (".PSU Export All Saves to Backup Storage", ".PSU 导出所有存档到备份存储"),
    (" Memory Card Management", " 记忆卡管理"),
    (" Export selected Saves to Storage (.PSV)", " 导出所选存档到存储 (.PSV)"),
    (" Export all Saves to Storage (.PSV)", " 导出所有存档到存储 (.PSV)"),
    (" Export Memory Card to .VM1 format", " 导出记忆卡为 .VM1 格式"),
    (" Export Memory Card to .VMP format", " 导出记忆卡为 .VMP 格式"),
    (" Import Saves to Virtual Card", " 导入存档到虚拟卡"),

    # ---------- saves.c : 详情页字段标签 ----------
    ("----- Packed PS%d Save -----", "----- 打包的 PS%d 存档 -----"),
    ("----- Virtual Memory Card -----", "----- 虚拟记忆卡 -----"),
    ("----- PS1 Save -----", "----- PS1 存档 -----"),
    ("----- PS2 Save -----", "----- PS2 存档 -----"),
    ("----- Save -----", "----- 存档 -----"),
    ("File: %s\\n", "文件：%s\\n"),
    ("Title ID: %s\\n", "标题 ID：%s\\n"),
    ("Folder: %s\\n", "文件夹：%s\\n"),
    ("Game: %s\\n", "游戏：%s\\n"),
    ("Icon: %s\\n", "图标：%s\\n"),
    ("Title: %s\\n", "标题：%s\\n"),
    ("Dir Name: %s\\n", "目录名：%s\\n"),
]


# 当启用 --swap-buttons 时，需要把译文里的 \x10（X/确认）与 \x13（O/取消）对调的字符串。
# 注意：十六进制编辑器的帮助栏（"Value Up ... Exit"）不在这里，因为该界面 X/O 功能不是确认/取消。
BUTTON_SWAP_KEYS = {
    "\\x10 Select    \\x13 Back    \\x12 Details    \\x11 Refresh",
    "\\x10 Select    \\x13 Back    \\x11 Refresh",
    "\\x10 Select    \\x12 View Code    \\x13 Back",
    "\\x10 Select    \\x13 Back",
    "\\x13 Back",
    "\\x10 OK   \\x13 Cancel",
    "\\x10 OK",
    "\\x10 Yes   \\x13 No",
}


def swap_button_codes(s):
    """把字符串里的 \x10 与 \x13 对调，用于"⭕ 确定 / ✕ 取消"模式。"""
    # 用占位符避免二次对调
    s = s.replace("\\x10", "\x00BTN_X\x00")
    s = s.replace("\\x13", "\\x10")
    s = s.replace("\x00BTN_X\x00", "\\x13")
    return s


def make_literal_pattern(en):
    """构造只匹配『完整引号字符串字面量』的正则。

    例如 en="Saves" 只匹配源码里的 "Saves"（含单/双引号），
    不会误伤 DrawStringMono、PlayStation 等代码标识符，也不受替换顺序影响。
    """
    esc = re.escape(en)
    # 组1/组3 为引号，组2 为被翻译内容；替换时原样保留引号，仅替换内部文本。
    return re.compile(r'(["\'])(' + esc + r')(\1)')


def apply_file(path, swap_buttons=False):
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()

    original = data
    count = 0

    # 1) 字符串翻译：仅替换『完整引号字符串字面量』，避免误伤代码与长串
    for en, zh in TRANSLATIONS:
        # 若启用按钮对调，把帮助栏/对话框里的 \x10 与 \x13 对调
        if swap_buttons and en in BUTTON_SWAP_KEYS:
            zh = swap_button_codes(zh)

        pat = make_literal_pattern(en)

        # 用函数做替换，避免 zh 里的 \x10 / \1 等被当作反向引用解析
        def repl(m, zh=zh):
            return m.group(1) + zh + m.group(3)

        new_data, n = pat.subn(repl, data)
        if n:
            data = new_data
            count += n

    # 2) 把位图字体 DrawStringMono 切换为 TTF 的 DrawString（仅指定文件）
    if os.path.basename(path) in MONO_TO_TTF_FILES:
        # 负向后顾：DrawFormatStringMono（十六进制编辑器，纯 ASCII）不含子串
        # "DrawStringMono"，因此不会被误改；这里再保险地排除字母前缀。
        new_data, n = re.subn(r'(?<![A-Za-z])DrawStringMono\(', 'DrawString(', data)

        # draw.c 的「加载中」画面运行在独立 SDL 线程（loading_screen_thread）里，
        # 而 FreeType 不是线程安全的。原版在那里用位图字体 DrawStringMono，
        # 若改成 DrawString（FreeType）会让主线程与加载线程同时访问 FreeType，
        # 在 PS2 上直接卡死/崩溃。所以必须把这唯一一行还原为位图字体。
        if os.path.basename(path) == "draw.c":
            new_data = new_data.replace(
                'DrawString(0, SCREEN_HEIGHT - 120, (char*) user_data);',
                'DrawStringMono(0, SCREEN_HEIGHT - 120, (char*) user_data);'
            )

        if n:
            data = new_data
            count += n

    if data != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return count
    return 0


def _swap_cross_circle_in_function(data, func_name, mode='swap'):
    """在指定函数体内对调（或单向替换）PAD_CROSS 与 PAD_CIRCLE 两个 token。

    mode='swap'      : X↔O 对调（用于同时存在"确认/取消"两个分支的菜单）
    mode='circle_to_cross' : 仅把 O 改成 X（用于只有"返回"操作的界面，保持 X=取消统一）
    """
    # 函数可能是 static int foo() 或 int foo() 或 static void foo() 等
    pattern = re.compile(rf'(?:static\s+)?(?:void|int)\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{', re.DOTALL)
    m = pattern.search(data)
    if not m:
        return data

    start = m.end() - 1          # 函数体开括号 '{' 的位置
    depth = 1
    i = start + 1
    while i < len(data) and depth > 0:
        if data[i] == '{':
            depth += 1
        elif data[i] == '}':
            depth -= 1
        i += 1
    end = i                      # 函数体闭括号之后一位

    body = data[start:end]
    if mode == 'swap':
        body = body.replace('PAD_CROSS', 'PAD_CROSS_TEMP')
        body = body.replace('PAD_CIRCLE', 'PAD_CROSS')
        body = body.replace('PAD_CROSS_TEMP', 'PAD_CIRCLE')
    elif mode == 'circle_to_cross':
        body = body.replace('PAD_CIRCLE', 'PAD_CROSS')

    return data[:start] + body + data[end:]


def swap_menu_buttons(path):
    """把 menu_main.c 里菜单导航的确认/取消按键对调：⭕ 确定，✕ 返回/取消。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()

    funcs = {
        'doMainMenu': 'swap',
        'doSaveMenu': 'swap',
        'doOptionsMenu': 'swap',
        'doPatchMenu': 'swap',
        'doCodeOptionsMenu': 'swap',
        # 只有"返回"的界面，把 O 返回改成 X 返回，保持 X=取消统一
        'doAboutMenu': 'circle_to_cross',
        'doSaveDetailsMenu': 'circle_to_cross',
        'doPatchViewMenu': 'circle_to_cross',
        # doHexEditor 不动：X/Square 是数值加减，Circle 是保存并退出，不属于确认/取消
    }

    original = data
    for func_name, mode in funcs.items():
        data = _swap_cross_circle_in_function(data, func_name, mode)

    if data != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return True
    return False


def swap_dialog_buttons(path):
    """把 dialog.c 里对话框的 OK/Cancel/Yes/No 按键对调：⭕ 确定，✕ 取消。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()

    funcs = {
        'show_dialog': 'swap',
        'show_multi_dialog': 'swap',
    }

    original = data
    for func_name, mode in funcs.items():
        data = _swap_cross_circle_in_function(data, func_name, mode)

    if data != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Apollo Save Tool (PS2) 中文化脚本")
    parser.add_argument(
        "--swap-buttons", action="store_true",
        help="对调确认/取消按键：⭕ (Circle) 确定，✕ (Cross) 返回/取消（默认：X 确定，O 返回）"
    )
    args = parser.parse_args()

    if not os.path.isdir(SRC_DIR):
        print("错误：未找到 source/ 目录。请在 apollo-ps2 仓库根目录运行本脚本。")
        print("Error: source/ not found. Run this script at the repo root.")
        sys.exit(1)

    total = 0
    changed_files = 0
    for name in sorted(os.listdir(SRC_DIR)):
        if not name.endswith(".c"):
            continue
        path = os.path.join(SRC_DIR, name)
        try:
            n = apply_file(path, swap_buttons=args.swap_buttons)
        except UnicodeDecodeError as e:
            print(f"跳过 {name}（编码错误，请确认文件为 UTF-8）：{e}")
            continue
        if n:
            print(f"已修改 {name}（{n} 处）")
            changed_files += 1
            total += n

    if args.swap_buttons:
        menu_path = os.path.join(SRC_DIR, "menu_main.c")
        if os.path.exists(menu_path):
            if swap_menu_buttons(menu_path):
                print("已对调 menu_main.c 的确认/取消按键映射")
                changed_files += 1

        dialog_path = os.path.join(SRC_DIR, "dialog.c")
        if os.path.exists(dialog_path):
            if swap_dialog_buttons(dialog_path):
                print("已对调 dialog.c 的对话框按键映射")
                changed_files += 1

    print(f"\n完成：共修改 {changed_files} 个文件，{total} 处字符串。")
    print("Done: modified", changed_files, "files,", total, "strings.")

    font_path = os.path.join(REPO, "DATA", "FONT.OTF")
    if os.path.exists(font_path):
        size = os.path.getsize(font_path)
        print(f"检测到 FONT.OTF（{size/1024:.0f} KB）。请把它放到 APOLLO/DATA/ 目录下。")
    else:
        print("提示：编译前请把一份含 CJK 字形的 FONT.OTF 放到 APOLLO/DATA/ 目录，")
        print("      否则中文/日文/繁体中文将无法正常显示。")


if __name__ == "__main__":
    main()
