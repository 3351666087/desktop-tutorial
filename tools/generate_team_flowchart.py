from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SmartClassroom_Team_Flowchart_ZH.png"

W, H = 2200, 1300


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for item in candidates:
        if item.exists():
            return ImageFont.truetype(str(item), size)
    return ImageFont.load_default()


F_TITLE = font(46, True)
F_H1 = font(30, True)
F_H2 = font(23, True)
F_BODY = font(19)
F_SMALL = font(16)
F_TINY = font(13)


COLORS = {
    "bg": "#061016",
    "grid": "#123448",
    "panel": "#0E2737",
    "panel2": "#102D40",
    "ink": "#F4FBFF",
    "muted": "#A9C4D6",
    "cyan": "#6FEAFF",
    "mint": "#54F2B0",
    "amber": "#FFCA6A",
    "red": "#FF5F7E",
    "purple": "#B884FF",
    "green": "#6CF28C",
}


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, ft: ImageFont.FreeTypeFont) -> None:
    draw.text(xy, value, fill=fill, font=ft)


def multiline(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, ft: ImageFont.FreeTypeFont, width: int, line_gap: int = 8) -> None:
    x, y = xy
    # Chinese text wraps poorly by spaces; use a conservative character width estimate.
    max_chars = max(8, width // max(8, int(ft.size * 0.62)))
    lines: list[str] = []
    for para in value.split("\n"):
        if any("\u4e00" <= ch <= "\u9fff" for ch in para):
            lines.extend([para[i : i + max_chars] for i in range(0, len(para), max_chars)])
        else:
            lines.extend(wrap(para, max_chars))
    for line in lines:
        draw.text((x, y), line, fill=fill, font=ft)
        y += ft.size + line_gap


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str, width: int = 2, radius: int = 28) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def node(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, body: str, color: str) -> None:
    rounded(draw, (x, y, x + w, y + h), COLORS["panel"], color, 3)
    rounded(draw, (x + 24, y + 22, x + 180, y + 58), "#123448", color, 2, 14)
    text(draw, (x + 42, y + 27), title, color, F_SMALL)
    multiline(draw, (x + 28, y + 82), body, COLORS["ink"], F_BODY, w - 56, 7)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, label: str = "") -> None:
    draw.line([start, end], fill=color, width=4)
    x2, y2 = end
    x1, y1 = start
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 >= x1 else -1
        tri = [(x2, y2), (x2 - 16 * direction, y2 - 9), (x2 - 16 * direction, y2 + 9)]
    else:
        direction = 1 if y2 >= y1 else -1
        tri = [(x2, y2), (x2 - 9, y2 - 16 * direction), (x2 + 9, y2 - 16 * direction)]
    draw.polygon(tri, fill=color)
    if label:
        lx = (x1 + x2) // 2 - 78
        ly = (y1 + y2) // 2 - 24
        rounded(draw, (lx, ly, lx + 156, ly + 30), "#081925", color, 1, 10)
        draw.text((lx + 14, ly + 6), label, fill=color, font=F_TINY)


def main() -> None:
    img = Image.new("RGB", (W, H), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 90):
        draw.line([(x, 0), (x, H)], fill="#FFFFFF08", width=1)
    for y in range(0, H, 90):
        draw.line([(0, y), (W, y)], fill="#FFFFFF08", width=1)

    draw.ellipse((1260, -180, 1900, 460), fill="#122A4420", outline=None)
    draw.ellipse((-220, 820, 420, 1460), fill="#3A215420", outline=None)

    text(draw, (70, 48), "Smart Classroom 项目总流程图", COLORS["ink"], F_TITLE)
    text(draw, (74, 108), "给组员现场组装、讲解和演示使用：先讲本地安全与边缘控制，再讲网络、Dashboard 和 AI。", COLORS["muted"], F_BODY)

    node(draw, 90, 205, 340, 320, "输入层", "PIR 人体感应\nTEMT6000 光照\nLM35 温度\nGas 气体\nFlame 火焰 DO/AO\nD4 紧急测试按钮", COLORS["cyan"])
    node(draw, 520, 175, 390, 380, "UNO 边缘控制", "readSensors()\nupdateButton()\nupdateControlLogic()\napplyActuators()\nSafety Alarm 最高优先级\n每 1 秒输出 SC2 遥测", COLORS["amber"])
    node(draw, 1010, 205, 360, 320, "执行层", "D5 教室灯 LED\nD6 继电器控制风扇电源\nD9 风扇 PWM\nD3 Tach RPM\nD7 蜂鸣器\nD10/D11/D12 红黄绿灯", COLORS["red"])

    node(draw, 520, 700, 390, 330, "ESP32 网关", "Serial2 接收 UNO\nWi-Fi + MQTT 重连\n发布 JSON / 关键 topics\n接收网页命令\n通过 UART 回传 UNO\nACK 确认命令落地", COLORS["mint"])
    node(draw, 1010, 700, 360, 330, "Web Dashboard", "实时卡片与图表\n自动/手动模式\n阈值永久保存\n一键场景/预设策略\n移动端支持\n日志默认隐藏可展开", COLORS["purple"])
    node(draw, 1480, 700, 520, 330, "AI + 数据层", "收集用户偏好数据\nQwen 将自然语言转成结构化多步骤任务\n支持时间轴：如 3 分钟后切手动\n完成后自动清除任务\n语音输入可接 faster-whisper", COLORS["green"])

    rounded(draw, (1480, 185, 2020, 565), COLORS["panel2"], COLORS["cyan"], 3, 28)
    text(draw, (1510, 220), "讲解优先级", COLORS["cyan"], F_H1)
    priorities = [
        ("P1", "安全报警层", "Gas / Flame / Button -> 红灯、蜂鸣器、风扇高转"),
        ("P2", "边缘架构", "UNO 本地决策，ESP32 只是网关"),
        ("P3", "节能舒适", "PIR + 光照 + 温度 -> 灯和风扇"),
        ("P4", "IoT 网络", "UART -> MQTT -> Dashboard -> ACK"),
        ("P5", "运维界面", "图表、手动模式、预设策略、移动端"),
        ("P6", "智能功能", "语音、Qwen、多步骤时间轴、数据偏好"),
    ]
    y = 280
    for tag, title, body in priorities:
        rounded(draw, (1512, y, 1570, y + 34), "#081925", COLORS["amber"], 1, 12)
        text(draw, (1528, y + 5), tag, COLORS["amber"], F_SMALL)
        text(draw, (1590, y + 3), title, COLORS["ink"], F_SMALL)
        multiline(draw, (1718, y + 3), body, COLORS["muted"], F_TINY, 270, 2)
        y += 47

    arrow(draw, (430, 365), (520, 365), COLORS["cyan"], "sensor")
    arrow(draw, (910, 365), (1010, 365), COLORS["amber"], "control")
    arrow(draw, (715, 555), (715, 700), COLORS["mint"], "SC2 UART")
    arrow(draw, (910, 865), (1010, 865), COLORS["mint"], "MQTT")
    arrow(draw, (1370, 865), (1480, 865), COLORS["purple"], "AI ops")
    arrow(draw, (1010, 960), (910, 960), COLORS["purple"], "command")
    arrow(draw, (520, 960), (430, 525), COLORS["amber"], "local first")

    rounded(draw, (90, 1125, 2020, 1220), "#0E2737", COLORS["cyan"], 2, 26)
    text(draw, (122, 1153), "现场介绍建议", COLORS["cyan"], F_H2)
    multiline(
        draw,
        (300, 1147),
        "先按按钮演示 Safety Alarm，立刻证明系统不是普通 Dashboard；再解释 UNO/ESP32 分工；最后展示网页、图表、预设策略和 Qwen 语音时间轴。",
        COLORS["ink"],
        F_BODY,
        1600,
        6,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, quality=96)
    print(OUT)


if __name__ == "__main__":
    main()
