"""
build_docx.py — собирает курсовую работу в DOCX по приложенному образцу.

Запуск:
    cd docs && python3 build_docx.py
Результат:
    docs/coursework.docx
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.shared import Cm, Pt, Mm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = Path(__file__).parent
CONTENT_DIR = HERE / "content"
IMG_DIR = HERE / "img"
OUT_PATH = HERE / "coursework.docx"
TEMPLATE_PATH = HERE / "template.docx"  # титульник + оглавление от пользователя

# Множитель межстрочного интервала в основном тексте.
# Методичка: 18 пт точно для шрифта 14 пт; 18/14 ≈ 1.29.
BODY_LINE_SPACING = Pt(18)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def set_default_font(doc: Document, name: str = "Times New Roman", size: int = 14) -> None:
    style = doc.styles["Normal"]
    style.font.name = name
    style.font.size = Pt(size)


def configure_page(doc: Document) -> None:
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Mm(30)
        section.right_margin = Mm(10)
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)


def enable_page_numbers(doc: Document) -> None:
    """Номера страниц: внизу страницы по центру, TNR 12."""
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        fldChar1 = OxmlElement("w:fldChar")
        fldChar1.set(qn("w:fldCharType"), "begin")
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = "PAGE"
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "end")
        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)


def p_title(doc: Document, text: str, *, bold: bool = False, line_spacing: float = 1.0,
            space_after: int = 0) -> None:
    """Заголовок: 14pt Times New Roman, по центру, межстрочный 1.0."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    run.bold = bold


def p_body(doc: Document, text: str, *, indent: float = 1.25, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
           line_spacing=None) -> None:
    """Абзац основного текста: TNR 14 pt, межстр. 18 pt точно, отступ 1,25 см, по ширине."""
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = line_spacing if line_spacing is not None else BODY_LINE_SPACING
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY if line_spacing is None else WD_LINE_SPACING.MULTIPLE
    p.paragraph_format.first_line_indent = Cm(indent) if indent else None
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    text = normalize_punct(text)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)


def normalize_punct(text: str) -> str:
    """Приведение пунктуации к методичке: «» вместо "", тире вместо дефиса между словами."""
    # Замена прямых кавычек на «ёлочки» (упрощённо: парные)
    out_chars = []
    open_quote = True
    for ch in text:
        if ch == '"':
            out_chars.append("«" if open_quote else "»")
            open_quote = not open_quote
        else:
            out_chars.append(ch)
    s = "".join(out_chars)
    # Замена двойного дефиса на тире и одиночного «слово - слово» на «слово – слово».
    s = s.replace(" -- ", " – ")
    return s


def add_md_table(doc: Document, lines: list) -> None:
    """Преобразует markdown-таблицу (список строк) в Word-таблицу."""
    rows = []
    for ln in lines:
        if re.match(r"\s*\|[-\s|]+\|\s*$", ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.style = "Table Grid"
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            cell = table.cell(ri, ci)
            text = row[ci] if ci < len(row) else ""
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
            if ri == 0:
                run.bold = True


def p_subheading(doc: Document, text: str) -> None:
    """Подзаголовок (1.1 / 1.2 / ...): TNR 14 pt, обычный, с отступом 1,25 см, по левому краю."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = BODY_LINE_SPACING
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)
    run.bold = True


def p_numbered_item(doc: Document, num: int, text: str) -> None:
    """Элемент нумерованного списка: '1. Текст.' Отступ 1,25 см."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = BODY_LINE_SPACING
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    text = normalize_punct(text)
    run = p.add_run(f"{num}. {text}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)


def p_figure(doc: Document, img_path: Path, caption: str) -> None:
    """Вставка рисунка и подписи по методичке.

    Расстояние между текстом и рисунком — одна пустая строка.
    Подрисуночная подпись — TNR 12 pt, полужирный, по центру, без точки в конце.
    После подписи — ещё одна пустая строка.
    """
    # Пустая строка перед рисунком.
    _spacer(doc)
    # Сам рисунок.
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run()
    run.add_picture(str(img_path), width=Cm(14.5))
    # Подрисуночная подпись.
    pc = doc.add_paragraph()
    pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pc.paragraph_format.line_spacing = 1.0
    pc.paragraph_format.first_line_indent = Cm(0)
    pc.paragraph_format.space_after = Pt(0)
    pc.paragraph_format.keep_with_next = True
    rc = pc.add_run(normalize_punct(caption).rstrip("."))
    rc.font.name = "Times New Roman"
    rc.font.size = Pt(12)
    rc.bold = True
    # Пустая строка после подписи.
    _spacer(doc)


def _spacer(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)


def p_right(doc: Document, text: str, *, indent: float = 8.5) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.first_line_indent = None
    p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)


def page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


# -----------------------------------------------------------------------------
# Чтение фрагментов текста
# -----------------------------------------------------------------------------
def read_block(name: str) -> list:
    """Читает текстовый файл и возвращает список абзацев (по пустым строкам)."""
    text = (CONTENT_DIR / name).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text.strip())
    return [b.strip() for b in blocks if b.strip()]


# -----------------------------------------------------------------------------
# Шаблон титульного листа (берётся из ____602.docx)
# -----------------------------------------------------------------------------
def build_title_page(doc: Document) -> None:
    p_title(doc, "МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ")
    p_title(doc, "БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ")
    p_title(doc, "Кафедра телекоммуникаций и информационных технологий")
    p_title(doc, "")
    p_title(doc, "")
    p_title(doc, "")

    p_title(doc, "РАЗРАБОТКА ПРОГРАММНО-АППАРАТНОГО КОМПЛЕКСА", bold=True)
    p_title(doc, "КРИПТОГРАФИЧЕСКИХ ПРЕОБРАЗОВАНИЙ ИНФОРМАЦИИ", bold=True)
    p_title(doc, "ПО СТАНДАРТАМ СТБ С USB-ИНТЕРФЕЙСОМ", bold=True)
    p_title(doc, "")
    p_title(doc, "Курсовая работа")
    p_title(doc, "")

    p_right(doc, "Дятчика Владимира Александровича")
    p_right(doc, "студента 3 курса 602 группы")
    p_right(doc, "специальность «Кибербезопасность»")
    p_right(doc, "")
    p_right(doc, "Научный руководитель:")
    p_right(doc, "Старший преподаватель")
    p_right(doc, "Шалатонин Иван Алексеевич")

    for _ in range(4):
        p_title(doc, "")
    p_title(doc, "Минск, 2026")
    page_break(doc)


# -----------------------------------------------------------------------------
# Оглавление
# -----------------------------------------------------------------------------
TOC = [
    ("ВВЕДЕНИЕ", None),
    ("ГЛАВА 1 ТЕОРЕТИЧЕСКИЕ ОСНОВЫ КРИПТОГРАФИЧЕСКОЙ ЗАЩИТЫ ИНФОРМАЦИИ ПО СТАНДАРТАМ СТБ", None),
    ("1.1 Основные понятия и цели криптографической защиты информации", "sub"),
    ("1.2 Национальные стандарты криптографических преобразований СТБ", "sub"),
    ("1.3 Алгоритмы шифрования и дешифрования информации", "sub"),
    ("1.4 Электронная цифровая подпись и принципы её применения", "sub"),
    ("1.5 Управление и защита криптографических ключей", "sub"),
    ("ГЛАВА 2 АРХИТЕКТУРА ПРОГРАММНО-АППАРАТНОГО КОМПЛЕКСА КРИПТОГРАФИЧЕСКИХ ПРЕОБРАЗОВАНИЙ", None),
    ("2.1 Выбор и характеристика микроконтроллерной платформы", "sub"),
    ("2.2 Общая структура программно-аппаратного комплекса", "sub"),
    ("2.3 Организация обмена данными по USB-интерфейсу", "sub"),
    ("2.4 Протокол взаимодействия между персональным компьютером и устройством", "sub"),
    ("2.5 Требования к безопасности программно-аппаратного комплекса", "sub"),
    ("ГЛАВА 3 ОБЗОР ПРАКТИЧЕСКИХ РЕШЕНИЙ АППАРАТНО-ПРОГРАММНЫХ СРЕДСТВ КРИПТОГРАФИЧЕСКОЙ ЗАЩИТЫ", None),
    ("3.1 Аппаратные криптографические устройства с USB-интерфейсом", "sub"),
    ("3.2 Обзор средств криптографической защиты информации по стандартам СТБ", "sub"),
    ("3.3 Анализ архитектурных и функциональных решений", "sub"),
    ("3.4 Сравнительный анализ существующих программно-аппаратных комплексов", "sub"),
    ("ГЛАВА 4 ПРАКТИЧЕСКАЯ РЕАЛИЗАЦИЯ ПРОГРАММНО-АППАРАТНОГО КОМПЛЕКСА", None),
    ("4.1 Реализация взаимодействия персонального компьютера с микроконтроллером", "sub"),
    ("4.2 Реализация криптографических операций на стороне устройства", "sub"),
    ("4.3 Генерация и хранение криптографических ключей", "sub"),
    ("4.4 Реализация программного обеспечения на стороне персонального компьютера", "sub"),
    ("4.5 Тестирование и анализ результатов работы комплекса", "sub"),
    ("ГЛАВА 5 ОЦЕНКА ЭФФЕКТИВНОСТИ И БЕЗОПАСНОСТИ РАЗРАБОТАННОГО КОМПЛЕКСА", None),
    ("5.1 Производительность криптографических операций", "sub"),
    ("5.2 Стойкость к известным атакам и оценка криптографических примитивов", "sub"),
    ("5.3 Защищённость хранилища ключей и протокола обмена", "sub"),
    ("5.4 Эксплуатационные характеристики и рекомендации по применению", "sub"),
    ("ЗАКЛЮЧЕНИЕ", None),
    ("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", None),
]


def build_toc(doc: Document) -> None:
    p_title(doc, "ОГЛАВЛЕНИЕ", line_spacing=1.0, bold=True)
    for title, kind in TOC:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(0)
        if kind == "sub":
            p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(title)
        run.font.name = "Times New Roman"
        run.font.size = Pt(13)
    page_break(doc)


# -----------------------------------------------------------------------------
# Универсальный набор главы из файла
# -----------------------------------------------------------------------------
def render_block(doc: Document, fname: str) -> None:
    """Читает файл с контентом; выводит:
    - markdown-таблицы как Word-таблицы;
    - блоки NLIST_START / NLIST_END как нумерованные списки;
    - строки IMG[path|caption] как рисунки с подписью;
    - остальное как абзацы основного текста.
    """
    blocks = read_block(fname)
    in_list = False
    list_items: list = []
    list_counter = 0
    for para in blocks:
        # Маркер начала списка может стоять отдельным блоком или внутри абзаца.
        if para.strip() == "NLIST_START":
            in_list = True
            list_items = []
            continue
        if para.strip() == "NLIST_END":
            for item in list_items:
                list_counter += 1
                p_numbered_item(doc, list_counter, item)
            in_list = False
            list_counter = 0
            list_items = []
            continue
        if in_list:
            for line in para.splitlines():
                line = line.strip()
                if line and line not in ("NLIST_START", "NLIST_END"):
                    list_items.append(line)
            continue
        # Рисунок: IMG[/abs/path|caption]
        if para.startswith("IMG[") and para.endswith("]"):
            body = para[4:-1]
            if "|" in body:
                img_path_str, caption = body.split("|", 1)
                img_path = Path(img_path_str.strip())
                if not img_path.is_absolute():
                    img_path = (HERE / img_path).resolve()
                p_figure(doc, img_path, caption.strip())
            continue
        lines = para.splitlines()
        # таблица: все строки начинаются с «|»
        if all(l.lstrip().startswith("|") for l in lines) and len(lines) >= 2:
            add_md_table(doc, lines)
        else:
            p_body(doc, para)


def build_section(doc: Document, *, header_lines: list, subsections: list) -> None:
    """
    header_lines  — список строк заголовка главы (центрируются 1.5 межстр.).
    subsections   — список (title, filename) подразделов.
    """
    for line in header_lines:
        p_title(doc, line, line_spacing=1.5, bold=True)

    for title, fname in subsections:
        p_subheading(doc, title)
        render_block(doc, fname)


def build_intro(doc: Document) -> None:
    p_title(doc, "ВВЕДЕНИЕ", line_spacing=1.5, bold=True)
    render_block(doc, "intro.txt")
    page_break(doc)


def build_chapter1(doc: Document) -> None:
    build_section(
        doc,
        header_lines=[
            "ГЛАВА 1",
            "ТЕОРЕТИЧЕСКИЕ ОСНОВЫ КРИПТОГРАФИЧЕСКОЙ ЗАЩИТЫ",
            "ИНФОРМАЦИИ ПО СТАНДАРТАМ СТБ",
        ],
        subsections=[
            ("1.1 Основные понятия и цели криптографической защиты информации", "ch1_1.txt"),
            ("1.2 Национальные стандарты криптографических преобразований СТБ", "ch1_2.txt"),
            ("1.3 Алгоритмы шифрования и дешифрования информации", "ch1_3.txt"),
            ("1.4 Электронная цифровая подпись и принципы её применения", "ch1_4.txt"),
            ("1.5 Управление и защита криптографических ключей", "ch1_5.txt"),
        ],
    )
    page_break(doc)


def build_chapter2(doc: Document) -> None:
    build_section(
        doc,
        header_lines=[
            "ГЛАВА 2",
            "АРХИТЕКТУРА ПРОГРАММНО-АППАРАТНОГО КОМПЛЕКСА",
            "КРИПТОГРАФИЧЕСКИХ ПРЕОБРАЗОВАНИЙ",
        ],
        subsections=[
            ("2.1 Выбор и характеристика микроконтроллерной платформы", "ch2_1.txt"),
            ("2.2 Общая структура программно-аппаратного комплекса", "ch2_2.txt"),
            ("2.3 Организация обмена данными по USB-интерфейсу", "ch2_3.txt"),
            ("2.4 Протокол взаимодействия между персональным компьютером и устройством", "ch2_4.txt"),
            ("2.5 Требования к безопасности программно-аппаратного комплекса", "ch2_5.txt"),
        ],
    )
    page_break(doc)


def build_chapter3(doc: Document) -> None:
    build_section(
        doc,
        header_lines=[
            "ГЛАВА 3",
            "ОБЗОР ПРАКТИЧЕСКИХ РЕШЕНИЙ АППАРАТНО-ПРОГРАММНЫХ",
            "СРЕДСТВ КРИПТОГРАФИЧЕСКОЙ ЗАЩИТЫ",
        ],
        subsections=[
            ("3.1 Аппаратные криптографические устройства с USB-интерфейсом", "ch3_1.txt"),
            ("3.2 Обзор средств криптографической защиты информации по стандартам СТБ", "ch3_2.txt"),
            ("3.3 Анализ архитектурных и функциональных решений", "ch3_3.txt"),
            ("3.4 Сравнительный анализ существующих программно-аппаратных комплексов", "ch3_4.txt"),
        ],
    )
    page_break(doc)


def build_chapter4(doc: Document) -> None:
    build_section(
        doc,
        header_lines=[
            "ГЛАВА 4",
            "ПРАКТИЧЕСКАЯ РЕАЛИЗАЦИЯ ПРОГРАММНО-АППАРАТНОГО",
            "КОМПЛЕКСА",
        ],
        subsections=[
            ("4.1 Реализация взаимодействия персонального компьютера с микроконтроллером", "ch4_1.txt"),
            ("4.2 Реализация криптографических операций на стороне устройства", "ch4_2.txt"),
            ("4.3 Генерация и хранение криптографических ключей", "ch4_3.txt"),
            ("4.4 Реализация программного обеспечения на стороне персонального компьютера", "ch4_4.txt"),
            ("4.5 Тестирование и анализ результатов работы комплекса", "ch4_5.txt"),
        ],
    )
    page_break(doc)


def build_chapter5(doc: Document) -> None:
    build_section(
        doc,
        header_lines=[
            "ГЛАВА 5",
            "ОЦЕНКА ЭФФЕКТИВНОСТИ И БЕЗОПАСНОСТИ",
            "РАЗРАБОТАННОГО КОМПЛЕКСА",
        ],
        subsections=[
            ("5.1 Производительность криптографических операций", "ch5_1.txt"),
            ("5.2 Стойкость к известным атакам и оценка криптографических примитивов", "ch5_2.txt"),
            ("5.3 Защищённость хранилища ключей и протокола обмена", "ch5_3.txt"),
            ("5.4 Эксплуатационные характеристики и рекомендации по применению", "ch5_4.txt"),
        ],
    )
    page_break(doc)


def build_conclusion(doc: Document) -> None:
    p_title(doc, "ЗАКЛЮЧЕНИЕ", line_spacing=1.5, bold=True)
    render_block(doc, "conclusion.txt")
    page_break(doc)


def build_references(doc: Document) -> None:
    p_title(doc, "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", line_spacing=BODY_LINE_SPACING, bold=True)
    for i, para in enumerate(read_block("references.txt"), 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = BODY_LINE_SPACING
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.first_line_indent = Cm(1.25)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(f"{i}. {normalize_punct(para)}")
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)


def strip_after_toc(doc: Document) -> None:
    """Из template.docx удаляет всё после таблицы оглавления.

    Сохраняет: paragraphs 0-30 (титул + слово ОГЛАВЛЕНИЕ) + Table 0 (TOC).
    Удаляет: введение, главы, заключение, список источников (старый контент шаблона).
    Финальный <w:sectPr> остаётся на месте — новые абзацы будут вставляться перед ним.
    """
    body = doc.element.body
    children = list(body)
    # Найти первый <w:tbl> — это таблица оглавления.
    toc_idx = None
    for i, ch in enumerate(children):
        if ch.tag.endswith('}tbl'):
            toc_idx = i
            break
    if toc_idx is None:
        return
    # Удаляем всё после оглавления кроме финального <w:sectPr>.
    for ch in children[toc_idx + 1:]:
        if ch.tag.endswith('}sectPr'):
            continue
        body.remove(ch)


# -----------------------------------------------------------------------------
def main() -> None:
    if TEMPLATE_PATH.exists():
        doc = Document(str(TEMPLATE_PATH))
        strip_after_toc(doc)
        # Шаблон уже содержит правильные поля, шрифт, разделы; не перенастраиваем.
        # Включаем номера страниц по центру внизу (на случай если в шаблоне нет).
        try:
            enable_page_numbers(doc)
        except Exception:
            pass
        # После оглавления вставляем разрыв страницы перед введением.
        page_break(doc)
    else:
        doc = Document()
        configure_page(doc)
        set_default_font(doc)
        enable_page_numbers(doc)
        build_title_page(doc)
        build_toc(doc)

    build_intro(doc)
    build_chapter1(doc)
    build_chapter2(doc)
    build_chapter3(doc)
    build_chapter4(doc)
    build_chapter5(doc)
    build_conclusion(doc)
    build_references(doc)

    doc.save(OUT_PATH)
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"Сохранено: {OUT_PATH}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
