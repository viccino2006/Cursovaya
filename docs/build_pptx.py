"""build_pptx.py — собирает презентацию к защите курсовой.

Запуск:
    cd docs && python3 build_pptx.py
Результат:
    docs/presentation.pptx
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Cm, Pt, Emu
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

HERE = Path(__file__).parent
IMG_DIR = HERE / "img"
OUT = HERE / "presentation.pptx"

# Cвет акцента — академический тёмно-синий.
ACCENT = RGBColor(0x1F, 0x3A, 0x68)
LIGHT = RGBColor(0xF5, 0xF7, 0xFA)
TEXT = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x55, 0x55, 0x55)

# Размер слайда 16:9 (33.87 × 19.05 см — стандарт PowerPoint).
SLIDE_W = Cm(33.87)
SLIDE_H = Cm(19.05)


def new_pres() -> Presentation:
    p = Presentation()
    p.slide_width = SLIDE_W
    p.slide_height = SLIDE_H
    return p


def blank(p: Presentation):
    layout = p.slide_layouts[6]  # blank
    return p.slides.add_slide(layout)


def add_bar(slide):
    """Цветная полоса слева — общий декоративный элемент."""
    from pptx.shapes.autoshape import Shape
    from pptx.enum.shapes import MSO_SHAPE
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), Cm(0), Cm(0.5), SLIDE_H)
    bar.line.fill.background()
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT


def add_textbox(slide, *, left, top, width, height, text, size=18, bold=False,
                color=TEXT, align=PP_ALIGN.LEFT, font="Calibri"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Cm(0)
    tf.margin_right = Cm(0)
    tf.margin_top = Cm(0)
    tf.margin_bottom = Cm(0)
    lines = text.split("\n") if isinstance(text, str) else text
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def add_title(slide, title, *, top=Cm(0.8), size=30):
    add_textbox(slide, left=Cm(1.5), top=top, width=Cm(30.5), height=Cm(1.6),
                text=title, size=size, bold=True, color=ACCENT)
    # тонкая разделительная линия
    from pptx.enum.shapes import MSO_SHAPE
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(1.5), top + Cm(1.5),
                                   Cm(8), Cm(0.08))
    line.line.fill.background()
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT


def add_footer(slide, page_no, total):
    add_textbox(slide, left=Cm(1.5), top=Cm(18.0), width=Cm(20), height=Cm(0.7),
                text="Программно-аппаратный комплекс по СТБ с USB-интерфейсом",
                size=10, color=MUTED)
    add_textbox(slide, left=Cm(30), top=Cm(18.0), width=Cm(2.5), height=Cm(0.7),
                text=f"{page_no} / {total}", size=10, color=MUTED, align=PP_ALIGN.RIGHT)


# -----------------------------------------------------------------------------
# Слайды
# -----------------------------------------------------------------------------

def slide_title(p, page_no, total):
    s = blank(p)
    # Полностью закрашенный фон.
    from pptx.enum.shapes import MSO_SHAPE
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.line.fill.background()
    bg.fill.solid()
    bg.fill.fore_color.rgb = ACCENT

    add_textbox(s, left=Cm(2), top=Cm(2), width=Cm(30), height=Cm(2),
                text="Белорусский государственный университет",
                size=18, color=LIGHT)
    add_textbox(s, left=Cm(2), top=Cm(2.8), width=Cm(30), height=Cm(2),
                text="Факультет радиофизики и компьютерных технологий",
                size=14, color=LIGHT)
    add_textbox(s, left=Cm(2), top=Cm(3.6), width=Cm(30), height=Cm(2),
                text="Кафедра телекоммуникаций и информационных технологий",
                size=14, color=LIGHT)

    add_textbox(s, left=Cm(2), top=Cm(6.5), width=Cm(30), height=Cm(2),
                text="Курсовая работа",
                size=20, color=LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(s, left=Cm(2), top=Cm(7.7), width=Cm(30), height=Cm(4.5),
                text=("Разработка программно-аппаратного комплекса\n"
                      "криптографических преобразований информации\n"
                      "по стандартам СТБ с USB-интерфейсом"),
                size=32, bold=True, color=LIGHT, align=PP_ALIGN.CENTER)

    add_textbox(s, left=Cm(2), top=Cm(14.5), width=Cm(30), height=Cm(0.8),
                text="Выполнил: Дятчик Владимир Александрович, студент 3 курса 602 группы",
                size=14, color=LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(s, left=Cm(2), top=Cm(15.3), width=Cm(30), height=Cm(0.8),
                text="Научный руководитель: ассистент Рундыгин Сергей Денисович",
                size=14, color=LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(s, left=Cm(2), top=Cm(17.5), width=Cm(30), height=Cm(1),
                text="Минск, 2026", size=14, color=LIGHT, align=PP_ALIGN.CENTER)


def slide_goal(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Цель и задачи работы")

    add_textbox(s, left=Cm(1.5), top=Cm(3), width=Cm(30), height=Cm(1.5),
                text="Цель",
                size=22, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(1.5), top=Cm(4.2), width=Cm(30), height=Cm(2),
                text=("Разработка программно-аппаратного комплекса, выполняющего "
                      "криптографические преобразования информации по белорусским "
                      "стандартам СТБ 34.101.31 и СТБ 34.101.45 на отдельном USB-устройстве."),
                size=18, color=TEXT)

    add_textbox(s, left=Cm(1.5), top=Cm(7.5), width=Cm(30), height=Cm(1.5),
                text="Задачи",
                size=22, bold=True, color=ACCENT)
    tasks = [
        "1. Изучить теоретические основы и национальные криптографические стандарты СТБ.",
        "2. Обосновать выбор микроконтроллерной платформы и архитектуры комплекса.",
        "3. Провести обзор существующих аппаратно-программных средств защиты по СТБ.",
        "4. Разработать прошивку устройства на основе криптобиблиотеки bee2.",
        "5. Реализовать хост-приложение для управления комплексом по USB CDC.",
        "6. Провести натурные испытания и оценить производительность и стойкость.",
    ]
    add_textbox(s, left=Cm(1.5), top=Cm(8.7), width=Cm(30), height=Cm(8),
                text="\n".join(tasks),
                size=17, color=TEXT)

    add_footer(s, page_no, total)


def slide_relevance(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Актуальность")
    bullets = [
        "•  Государственные и финансовые системы РБ обязаны защищать данные по СТБ.",
        "•  Использование иностранных решений ограничено законодательством (Указ № 196).",
        "•  Программные хранилища ключей уязвимы при компрометации хост-системы.",
        "•  Сертифицированные токены (АвестКлюч, Rutoken) дороги и закрыты.",
        "•  Нет открытых учебных образцов на отладочных платах STM32.",
    ]
    add_textbox(s, left=Cm(1.5), top=Cm(3.2), width=Cm(30), height=Cm(10),
                text="\n\n".join(bullets), size=20, color=TEXT)
    add_textbox(s, left=Cm(1.5), top=Cm(13.5), width=Cm(30), height=Cm(3),
                text=("⇒ Открытый, недорогой и расширяемый макет\n"
                      "USB-токена, реализующего отечественные стандарты СТБ."),
                size=22, bold=True, color=ACCENT)
    add_footer(s, page_no, total)


def slide_stb(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Используемые стандарты СТБ")
    # Таблица «стандарт → суть → применение в комплексе».
    rows = [
        ("Стандарт", "Описание", "Роль в комплексе"),
        ("СТБ 34.101.31-2020", "Шифр belt (блок 128 бит, ключ до 256 бит)\nи хеш-функция belt-hash", "Шифрование файлов в режиме CBC,\nвычисление хешей"),
        ("СТБ 34.101.45-2020", "Электронная цифровая подпись bign\nна эллиптических кривых", "Формирование и проверка подписи,\nалгоритм bign-sign2"),
        ("СТБ 34.101.47-2017", "Алгоритмы генерации\nпсевдослучайных чисел", "Генератор brng для выработки\nключевой пары"),
        ("СТБ 34.101.66-2014", "Протокол выработки общего\nключа bake", "Перспективное направление\nдля защиты канала"),
    ]
    table = s.shapes.add_table(len(rows), 3, Cm(1.5), Cm(3.5), Cm(30.5), Cm(11)).table
    table.columns[0].width = Cm(6.5)
    table.columns[1].width = Cm(13)
    table.columns[2].width = Cm(11)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            tf = cell.text_frame
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = val
            run.font.size = Pt(15)
            run.font.name = "Calibri"
            if ri == 0:
                run.font.bold = True
                run.font.color.rgb = LIGHT
                cell.fill.solid()
                cell.fill.fore_color.rgb = ACCENT
            else:
                run.font.color.rgb = TEXT
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT if ri % 2 else RGBColor(0xFF, 0xFF, 0xFF)
    add_footer(s, page_no, total)


def slide_architecture(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Общая архитектура комплекса")
    from pptx.enum.shapes import MSO_SHAPE
    # Блок «ПК».
    pc = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(2), Cm(5), Cm(11), Cm(8))
    pc.fill.solid(); pc.fill.fore_color.rgb = LIGHT
    pc.line.color.rgb = ACCENT
    add_textbox(s, left=Cm(2.5), top=Cm(5.2), width=Cm(10), height=Cm(1),
                text="Персональный компьютер", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(2.5), top=Cm(6.5), width=Cm(10), height=Cm(7),
                text=("•  Tkinter GUI\n"
                      "•  stm32_protocol.py (PySerial)\n"
                      "•  belt_hash.py — эталон\n"
                      "•  belt.py — программный шифр\n"
                      "•  чтение/запись файлов\n"
                      "•  хранение публичных ключей"),
                size=15, color=TEXT)

    # Стрелка / USB CDC.
    add_textbox(s, left=Cm(13.5), top=Cm(8.2), width=Cm(7), height=Cm(1.5),
                text="USB CDC ACM\n«запрос – ответ», 8 команд",
                size=14, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    arrow = s.shapes.add_shape(MSO_SHAPE.LEFT_RIGHT_ARROW, Cm(13.5), Cm(9.5),
                               Cm(7), Cm(0.8))
    arrow.fill.solid(); arrow.fill.fore_color.rgb = ACCENT
    arrow.line.fill.background()

    # Блок устройства.
    dev = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(21), Cm(5), Cm(11), Cm(8))
    dev.fill.solid(); dev.fill.fore_color.rgb = LIGHT
    dev.line.color.rgb = ACCENT
    add_textbox(s, left=Cm(21.5), top=Cm(5.2), width=Cm(10), height=Cm(1),
                text="STM32F103C8T6", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(21.5), top=Cm(6.5), width=Cm(10), height=Cm(7),
                text=("•  bee2 (belt, belt-hash, bign)\n"
                      "•  usb_protocol — диспетчер\n"
                      "•  key_storage — Flash 0x0801FC00\n"
                      "•  rng_stm32 — сбор энтропии\n"
                      "•  HAL + USB Device CDC"),
                size=15, color=TEXT)

    add_textbox(s, left=Cm(1.5), top=Cm(14), width=Cm(30), height=Cm(3),
                text=("Принцип минимизации доверенной зоны: закрытый ключ "
                      "никогда не покидает микроконтроллер."),
                size=18, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    add_footer(s, page_no, total)


def slide_platform(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Аппаратная платформа: STM32F103C8T6")
    left_col = ("•  Ядро ARM Cortex-M3, 72 МГц\n"
                "•  128 КБ Flash, 20 КБ ОЗУ\n"
                "•  Аппаратный USB Full-Speed (12 Мбит/с)\n"
                "•  96-битный уникальный ID\n"
                "•  12-разрядный АЦП — источник шума\n"
                "•  Цена платы STM32 Smart V2.0 < 10 у.е.")
    add_textbox(s, left=Cm(1.5), top=Cm(3.5), width=Cm(15), height=Cm(10),
                text=left_col, size=18, color=TEXT)

    add_textbox(s, left=Cm(17), top=Cm(3.5), width=Cm(15), height=Cm(1),
                text="Почему именно этот МК", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(17), top=Cm(4.7), width=Cm(15), height=Cm(10),
                text=("•  Достаточно памяти для bee2 (≈38 КБ)\n"
                      "•  Полный цикл bign-sign укладывается\n"
                      "    в 42 мс — приемлемо для пользователя\n"
                      "•  Аппаратный USB снимает необходимость\n"
                      "    в драйверах USB-UART\n"
                      "•  Опция Read-out Protection защищает\n"
                      "    Flash от несанкционированного чтения"),
                size=17, color=TEXT)
    add_footer(s, page_no, total)


def slide_usb(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Протокол обмена по USB CDC")
    add_textbox(s, left=Cm(1.5), top=Cm(3), width=Cm(30), height=Cm(1.5),
                text="Формат пакета: CMD (1 байт) | LEN (2 байта) | DATA (LEN байт)",
                size=18, bold=True, color=ACCENT)

    rows = [
        ("Команда", "Описание"),
        ("CMD_PING",          "Проверка связи, возвращает «BIGN1»"),
        ("CMD_GEN_KEYPAIR",   "Генерация новой пары ключей bign-128"),
        ("CMD_GET_PUBKEY",    "Чтение открытого ключа (64 байта)"),
        ("CMD_SIGN",          "Подпись 32-байтового хеша → 48 байт подписи"),
        ("CMD_VERIFY",        "Проверка подписи по pubkey"),
        ("CMD_HASH",          "belt-hash произвольных данных → 32 байта"),
        ("CMD_ENCRYPT",       "belt-CBC: IV+ключ+открытый текст → шифртекст"),
        ("CMD_DECRYPT",       "belt-CBC обратно: шифртекст → открытый текст"),
    ]
    table = s.shapes.add_table(len(rows), 2, Cm(1.5), Cm(5), Cm(30.5), Cm(11.5)).table
    table.columns[0].width = Cm(9)
    table.columns[1].width = Cm(21.5)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            tf = cell.text_frame
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = val
            run.font.size = Pt(15)
            run.font.name = "Consolas" if ci == 0 and ri > 0 else "Calibri"
            if ri == 0:
                run.font.bold = True
                run.font.color.rgb = LIGHT
                cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT
            else:
                run.font.color.rgb = TEXT
                cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT if ri % 2 else RGBColor(0xFF, 0xFF, 0xFF)
    add_footer(s, page_no, total)


def slide_firmware(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Прошивка устройства")
    add_textbox(s, left=Cm(1.5), top=Cm(3.2), width=Cm(15), height=Cm(1),
                text="Слои прошивки", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(1.5), top=Cm(4.3), width=Cm(15), height=Cm(10),
                text=("1. STM32 HAL (CubeMX)\n"
                      "2. USB Device + USB CDC ACM\n"
                      "3. usb_protocol — кадрирование и\n"
                      "   диспетчер 8 команд\n"
                      "4. crypto_stb — обёртка над bee2\n"
                      "5. key_storage — Flash + CRC-32\n"
                      "6. rng_stm32 — UID + DWT + АЦП → belt-hash"),
                size=17, color=TEXT)

    add_textbox(s, left=Cm(17), top=Cm(3.2), width=Cm(15), height=Cm(1),
                text="Хранение ключевой пары", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(17), top=Cm(4.3), width=Cm(15), height=Cm(10),
                text=("•  Последняя страница Flash:\n"
                      "    0x0801FC00, 1 КБ\n"
                      "•  32 Б d || 64 Б Q || 4 Б CRC-32\n"
                      "•  Защита целостности по CRC\n"
                      "•  При повреждении → ERR_NO_KEY\n"
                      "•  Закрытый ключ d из чипа\n"
                      "    не выводится наружу"),
                size=17, color=TEXT)
    add_footer(s, page_no, total)


def slide_host(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Хост-приложение (Python 3 + Tkinter)")
    add_textbox(s, left=Cm(1.5), top=Cm(3.2), width=Cm(30), height=Cm(1),
                text="Три рабочих вкладки + журнал операций",
                size=18, bold=True, color=ACCENT)
    cols = [
        ("Ключи",
         "•  Чтение публичного ключа\n"
         "•  Генерация новой пары\n"
         "•  Сохранение pubkey в файл"),
        ("Подпись / проверка",
         "•  belt-hash на ПК и устройстве\n"
         "•  bign-sign2 → файл .sig\n"
         "•  bign-verify, негативные тесты"),
        ("Шифрование",
         "•  belt-CBC + PKCS#7\n"
         "•  Случайный ключ и IV\n"
         "•  Round-trip без потерь"),
    ]
    for i, (h, body) in enumerate(cols):
        x = Cm(1.5 + i * 10.5)
        from pptx.enum.shapes import MSO_SHAPE
        card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Cm(5), Cm(10), Cm(9))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT
        card.line.color.rgb = ACCENT
        add_textbox(s, left=x + Cm(0.4), top=Cm(5.2), width=Cm(9), height=Cm(1),
                    text=h, size=18, bold=True, color=ACCENT)
        add_textbox(s, left=x + Cm(0.4), top=Cm(6.4), width=Cm(9), height=Cm(7),
                    text=body, size=15, color=TEXT)

    add_textbox(s, left=Cm(1.5), top=Cm(14.6), width=Cm(30), height=Cm(2.5),
                text=("Модули: stm32_protocol.py (PySerial), belt.py, belt_hash.py "
                      "(эталонные реализации для контроля устройства)."),
                size=15, color=MUTED)
    add_footer(s, page_no, total)


def slide_demo_keys(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Демонстрация: генерация ключевой пары")
    pic = s.shapes.add_picture(str(IMG_DIR / "01_keys_tab.png"),
                                Cm(1.5), Cm(3.3), height=Cm(13))
    add_textbox(s, left=Cm(20.5), top=Cm(3.5), width=Cm(12), height=Cm(13),
                text=("•  Сбор энтропии: UID + ADC + DWT\n\n"
                      "•  belt-hash → затравка генератора\n\n"
                      "•  d ← brng, Q = d·G\n\n"
                      "•  Запись в Flash 0x0801FC00\n\n"
                      "•  Возврат публичного ключа\n   (64 байта)\n\n"
                      "•  Время операции: 110 мс"),
                size=17, color=TEXT)
    add_footer(s, page_no, total)


def slide_demo_sign(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Демонстрация: ЭЦП по СТБ 34.101.45")
    pic = s.shapes.add_picture(str(IMG_DIR / "02_sign_tab.png"),
                                Cm(1.5), Cm(3.3), height=Cm(13))
    add_textbox(s, left=Cm(20.5), top=Cm(3.5), width=Cm(12), height=Cm(13),
                text=("•  belt-hash файла Open Text.txt\n   на ПК и на устройстве совпали:\n   e2f43da9…0133eb45b\n\n"
                      "•  bign-sign2 (детерминированный\n   k = belt-pbkdf(d || H))\n\n"
                      "•  Получена подпись 48 байт:\n   76199588…861b8946\n\n"
                      "•  Время формирования: 42 мс"),
                size=15, color=TEXT)
    add_footer(s, page_no, total)


def slide_demo_encrypt(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Демонстрация: шифрование belt-CBC + PKCS#7")
    pic = s.shapes.add_picture(str(IMG_DIR / "03_encrypt_tab.png"),
                                Cm(1.5), Cm(3.3), height=Cm(13))
    add_textbox(s, left=Cm(20.5), top=Cm(3.5), width=Cm(12), height=Cm(13),
                text=("•  Исходный файл: 43 байта (UTF-8)\n\n"
                      "•  Случайный ключ 32 Б, IV 16 Б\n\n"
                      "•  После PKCS#7 → 48 байт\n   передаются на устройство\n\n"
                      "•  belt-CBC шифрует → 48 байт\n\n"
                      "•  Расшифрование + снятие PKCS#7\n   → ровно 43 байта оригинала"),
                size=16, color=TEXT)
    add_footer(s, page_no, total)


def slide_demo_roundtrip(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Подтверждение корректности: round-trip")
    pic = s.shapes.add_picture(str(IMG_DIR / "05_roundtrip.png"),
                                Cm(1.5), Cm(3.3), width=Cm(31))
    add_textbox(s, left=Cm(1.5), top=Cm(15.7), width=Cm(30.5), height=Cm(2),
                text=("Слева — оригинал, в центре — шифртекст (нечитаемые байты), "
                      "справа — расшифрованный файл. SHA-256 совпадает с оригиналом."),
                size=15, color=TEXT, align=PP_ALIGN.CENTER)
    add_footer(s, page_no, total)


def slide_performance(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Производительность и ресурсы")

    rows = [
        ("Операция", "Размер данных", "Время / скорость"),
        ("CMD_PING", "—", "0,5 мс"),
        ("belt-hash, 1 КБ", "1024 байта", "1,3 мс  /  770 КБ/с"),
        ("belt-CBC шифрование", "1 КБ", "0,9 мс  /  1,1 МБ/с"),
        ("bign-sign2 (подпись)", "хеш 32 байта", "42 мс"),
        ("bign-verify (проверка)", "32 + 48 + 64 байта", "78 мс"),
        ("CMD_GEN_KEYPAIR", "—", "110 мс"),
    ]
    table = s.shapes.add_table(len(rows), 3, Cm(1.5), Cm(3.3), Cm(20), Cm(10)).table
    table.columns[0].width = Cm(8)
    table.columns[1].width = Cm(5)
    table.columns[2].width = Cm(7)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            tf = cell.text_frame
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = val
            run.font.size = Pt(14)
            run.font.name = "Calibri"
            if ri == 0:
                run.font.bold = True
                run.font.color.rgb = LIGHT
                cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT
            else:
                run.font.color.rgb = TEXT
                cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT if ri % 2 else RGBColor(0xFF, 0xFF, 0xFF)

    add_textbox(s, left=Cm(22), top=Cm(3.3), width=Cm(10), height=Cm(1),
                text="Использование ресурсов", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(22), top=Cm(4.5), width=Cm(10), height=Cm(9),
                text=("Flash: 83 / 128 КБ (≈ 65 %)\n"
                      "•  bee2 ≈ 38 КБ\n"
                      "•  USB-стек ≈ 14 КБ\n"
                      "•  HAL ≈ 12 КБ\n"
                      "•  прикладной слой ≈ 16 КБ\n\n"
                      "ОЗУ: 18,5 / 20 КБ (≈ 93 %)\n"
                      "•  bss ≈ 13 КБ\n"
                      "•  куча bee2 ≈ 4 КБ\n"
                      "•  стек ≈ 1,5 КБ"),
                size=15, color=TEXT)
    add_footer(s, page_no, total)


def slide_comparison(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Сравнение с существующими решениями")
    rows = [
        ("Решение", "Алгоритмы", "Открытость", "Цена"),
        ("АвестКлюч 6", "СТБ 34.101.31/45/66", "закрытое", "коммерч."),
        ("Rutoken ЭЦП 2.0", "СТБ 34.101.31/45", "закрытое", "коммерч."),
        ("JaCarta GOST", "СТБ 34.101.45", "закрытое", "коммерч."),
        ("Bee2 (BSU)", "СТБ 34.101.31/45/47/66", "открытое (Apache 2.0)", "free"),
        ("Разработанный комплекс", "СТБ 34.101.31, 34.101.45", "открытое (MIT)", "< 10 у.е."),
    ]
    table = s.shapes.add_table(len(rows), 4, Cm(1.5), Cm(3.3), Cm(30.5), Cm(9)).table
    table.columns[0].width = Cm(8)
    table.columns[1].width = Cm(11.5)
    table.columns[2].width = Cm(7)
    table.columns[3].width = Cm(4)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            tf = cell.text_frame
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = val
            run.font.size = Pt(15)
            run.font.name = "Calibri"
            if ri == 0:
                run.font.bold = True
                run.font.color.rgb = LIGHT
                cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT
            elif ri == len(rows) - 1:
                run.font.bold = True
                run.font.color.rgb = ACCENT
                cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT
            else:
                run.font.color.rgb = TEXT
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    add_textbox(s, left=Cm(1.5), top=Cm(13.5), width=Cm(30.5), height=Cm(3),
                text=("Разработанный комплекс занимает промежуточную нишу:\n"
                      "аппаратная защита ключа, как у промышленных токенов,\n"
                      "при полностью открытом коде и доступном оборудовании."),
                size=17, color=TEXT, align=PP_ALIGN.CENTER)
    add_footer(s, page_no, total)


def slide_security(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Оценка стойкости и защищённости")
    add_textbox(s, left=Cm(1.5), top=Cm(3.2), width=Cm(15), height=Cm(1),
                text="Криптографическая стойкость", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(1.5), top=Cm(4.4), width=Cm(15), height=Cm(11),
                text=("•  belt: 128 бит, лучшая атака ≥ 2¹¹⁰\n\n"
                      "•  bign на bign-curve256v1:\n   ρ-Полларда ≈ 2¹²⁸ операций\n\n"
                      "•  Детерминированный bign-sign2\n   снимает риск повтора k (как в ECDSA)\n\n"
                      "•  belt-hash в bee2 — постоянное время,\n   нечувствительно к тайминг-атакам"),
                size=16, color=TEXT)

    add_textbox(s, left=Cm(17), top=Cm(3.2), width=Cm(15), height=Cm(1),
                text="Защищённость комплекса", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(17), top=Cm(4.4), width=Cm(15), height=Cm(11),
                text=("•  Закрытый ключ не покидает Flash\n\n"
                      "•  CRC-32 защищает ключевую пару\n   от повреждения\n\n"
                      "•  Read-out Protection блокирует\n   чтение Flash через JTAG/SWD\n\n"
                      "•  Негативный тест: изменение 1 байта\n   → BAD SIGNATURE\n\n"
                      "•  Итоговый уровень стойкости: 128 бит"),
                size=16, color=TEXT)
    add_footer(s, page_no, total)


def slide_conclusion(p, page_no, total):
    s = blank(p)
    add_bar(s)
    add_title(s, "Заключение")
    add_textbox(s, left=Cm(1.5), top=Cm(3), width=Cm(30), height=Cm(1.5),
                text="Все поставленные задачи выполнены:",
                size=20, bold=True, color=ACCENT)
    items = [
        "•  Изучены национальные стандарты СТБ 34.101.31, 34.101.45, 34.101.47, 34.101.66.",
        "•  Спроектирована архитектура комплекса «ПК + STM32» с USB CDC-обменом.",
        "•  Выполнен обзор аппаратно-программных средств защиты по СТБ в Беларуси.",
        "•  Реализована прошивка STM32F103C8T6 на bee2 (~83 КБ Flash, 18,5 КБ ОЗУ).",
        "•  Создано хост-приложение Tkinter с тремя рабочими вкладками.",
        "•  Натурно подтверждены: belt-hash, bign-sign / verify, belt-CBC + PKCS#7.",
    ]
    add_textbox(s, left=Cm(1.5), top=Cm(4.6), width=Cm(30), height=Cm(9),
                text="\n\n".join(items), size=17, color=TEXT)

    add_textbox(s, left=Cm(1.5), top=Cm(13.7), width=Cm(30), height=Cm(1),
                text="Перспективы развития:", size=18, bold=True, color=ACCENT)
    add_textbox(s, left=Cm(1.5), top=Cm(14.9), width=Cm(30), height=Cm(2.5),
                text=("•  реализация PKCS#11-провайдера для интеграции в стандартные приложения;\n"
                      "•  использование bake (СТБ 34.101.66) для защищённой передачи сеансовых ключей;\n"
                      "•  переход на STM32 с аппаратным TRNG и большим объёмом ОЗУ."),
                size=15, color=TEXT)
    add_footer(s, page_no, total)


def slide_thanks(p, page_no, total):
    s = blank(p)
    from pptx.enum.shapes import MSO_SHAPE
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.line.fill.background()
    bg.fill.solid(); bg.fill.fore_color.rgb = ACCENT
    add_textbox(s, left=Cm(2), top=Cm(6), width=Cm(30), height=Cm(3),
                text="Спасибо за внимание!", size=48, bold=True,
                color=LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(s, left=Cm(2), top=Cm(10), width=Cm(30), height=Cm(2),
                text="Готов ответить на вопросы.",
                size=22, color=LIGHT, align=PP_ALIGN.CENTER)
    add_textbox(s, left=Cm(2), top=Cm(15), width=Cm(30), height=Cm(2),
                text="github.com/viccino2006/Cursovaya",
                size=16, color=LIGHT, align=PP_ALIGN.CENTER)


def main() -> None:
    builders = [
        slide_title,
        slide_goal,
        slide_relevance,
        slide_stb,
        slide_architecture,
        slide_platform,
        slide_usb,
        slide_firmware,
        slide_host,
        slide_demo_keys,
        slide_demo_sign,
        slide_demo_encrypt,
        slide_demo_roundtrip,
        slide_performance,
        slide_comparison,
        slide_security,
        slide_conclusion,
        slide_thanks,
    ]
    pres = new_pres()
    total = len(builders)
    for i, fn in enumerate(builders, 1):
        fn(pres, i, total)
    pres.save(str(OUT))
    print(f"Saved {OUT}  slides: {total}")


if __name__ == "__main__":
    main()
