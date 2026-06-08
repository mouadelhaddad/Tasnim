#!/usr/bin/env python3
"""Génère presentation.pptx — thème clair, en français, sans emojis.

Usage : python3 build_pptx.py
Dépendance : pip install python-pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Palette ──────────────────────────────────────────────────────────────────
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
INK       = RGBColor(0x0F, 0x17, 0x2A)
BODY      = RGBColor(0x33, 0x41, 0x55)
MUTED     = RGBColor(0x94, 0xA3, 0xB8)
ACCENT    = RGBColor(0x4F, 0x46, 0xE5)
ACCENT_DK = RGBColor(0x43, 0x38, 0xCA)
CARD_BG   = RGBColor(0xF8, 0xFA, 0xFC)
CARD_BD   = RGBColor(0xE2, 0xE8, 0xF0)
CHIP_BG   = RGBColor(0xEE, 0xF2, 0xFF)
GREEN     = RGBColor(0x05, 0x96, 0x69)

FONT = "Calibri"
MONO = "Consolas"

# ── Canvas ───────────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK  = prs.slide_layouts[6]
TOTAL  = 11

# ── Layout grid ──────────────────────────────────────────────────────────────
LM     = 0.55          # left margin (inches)
RM     = 0.55          # right margin
CW     = 13.333 - LM - RM   # 12.233 — total content width
RULE_Y = 1.25          # y of the accent rule under the header
CONT_Y = 1.48          # y where body content starts
BOT    = 7.32          # y of bottom boundary
GAP    = 0.14          # standard gap between adjacent elements
BAR_W  = 0.07          # accent bar width


# ── Primitive helpers ─────────────────────────────────────────────────────────

def new_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid(); bg.fill.fore_color.rgb = WHITE
    bg.line.fill.background(); bg.shadow.inherit = False
    return s


def run(para, text, size, color, bold=False, italic=False, font=FONT):
    r = para.add_run()
    r.text = text
    r.font.name  = font
    r.font.size  = Pt(size)
    r.font.color.rgb = color
    r.font.bold  = bold
    r.font.italic = italic
    return r


def textbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP,
            ml=Pt(4), mr=Pt(4), mt=Pt(4), mb=Pt(4)):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left   = ml
    tf.margin_right  = mr
    tf.margin_top    = mt
    tf.margin_bottom = mb
    return tf


def rect(s, x, y, w, h, fill, border=None, bw=Pt(0.75)):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if border:
        sh.line.color.rgb = border; sh.line.width = bw
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def rrect(s, x, y, w, h, fill=CARD_BG, border=CARD_BD, bw=Pt(0.75), radius=0.05):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = radius
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if border:
        sh.line.color.rgb = border; sh.line.width = bw
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


# ── Compound helpers ─────────────────────────────────────────────────────────

def card_bg(s, x, y, w, h, accent=ACCENT):
    """Rounded card with a solid left accent bar."""
    rrect(s, x, y, w, h)
    # bar is inset 0.04" top/bottom so it doesn't bleed past the rounded corners
    rect(s, x, y + 0.04, BAR_W, h - 0.08, fill=accent)


def card(s, x, y, w, h, title, lines, accent=ACCENT):
    """Info card: bold title + bullet lines."""
    card_bg(s, x, y, w, h, accent=accent)
    inner_x = x + BAR_W + 0.14
    inner_w = w - BAR_W - 0.22
    tf = textbox(s, inner_x, y, inner_w, h, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(4), mr=Pt(4), mt=Pt(6), mb=Pt(6))
    p = tf.paragraphs[0]; p.space_after = Pt(5)
    run(p, title, 14, INK, bold=True)
    for ln in lines:
        p2 = tf.add_paragraph(); p2.space_after = Pt(2)
        run(p2, f"· {ln}", 11, BODY)


def mono_card(s, x, y, w, h, lines, size=11):
    """Monospace code card."""
    card_bg(s, x, y, w, h)
    inner_x = x + BAR_W + 0.14
    inner_w = w - BAR_W - 0.22
    tf = textbox(s, inner_x, y, inner_w, h, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(4), mr=Pt(4), mt=Pt(8), mb=Pt(8))
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(1)
        run(p, ln, size, BODY, font=MONO)


def bullets(s, x, y, w, h, heading, items, bullet_color=ACCENT):
    """Heading + bulleted list."""
    tf = textbox(s, x, y, w, h, ml=Pt(2), mr=Pt(2), mt=Pt(2), mb=Pt(2))
    p = tf.paragraphs[0]; p.space_after = Pt(10)
    run(p, heading, 15, ACCENT_DK, bold=True)
    for it in items:
        p2 = tf.add_paragraph(); p2.space_after = Pt(7)
        run(p2, "·  ", 13, bullet_color, bold=True)
        run(p2, it,   13, BODY)


def chips(s, x, y, labels, gap=0.12):
    """Row of rounded pill chips."""
    cx = x
    for lab in labels:
        w = 0.13 * len(lab) + 0.45
        sh = rrect(s, cx, y, w, 0.34, fill=CHIP_BG, border=None)
        tf = sh.text_frame
        tf.word_wrap = False
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Pt(6)
        tf.margin_top  = tf.margin_bottom = Pt(0)
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        run(p, lab, 11, ACCENT_DK, bold=True)
        cx += w + gap


def header(s, title_parts, num):
    """Slide header: title + slide counter + accent rule."""
    tf = textbox(s, LM, 0.36, CW - 1.6, 0.78, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
    p = tf.paragraphs[0]
    for txt, col in title_parts:
        run(p, txt, 26, col, bold=True)

    tf2 = textbox(s, 13.333 - RM - 1.4, 0.36, 1.4, 0.78,
                  anchor=MSO_ANCHOR.MIDDLE,
                  ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
    p2 = tf2.paragraphs[0]; p2.alignment = PP_ALIGN.RIGHT
    run(p2, f"{num} / {TOTAL}", 11, MUTED, font=MONO)

    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                           Inches(LM), Inches(RULE_Y), Inches(CW), Pt(2.5))
    r.fill.solid(); r.fill.fore_color.rgb = ACCENT
    r.line.fill.background(); r.shadow.inherit = False


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Couverture
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()

top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.16))
top.fill.solid(); top.fill.fore_color.rgb = ACCENT
top.line.fill.background(); top.shadow.inherit = False

tf = textbox(s, 1.1, 1.3, 11, 0.46,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Université Euromed de Fès  ·  EIDIA", 13, MUTED, bold=True)

tf = textbox(s, 1.1, 2.0, 11, 1.5,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
p = tf.paragraphs[0]
run(p, "Compréhension ", 44, INK,    bold=True)
run(p, "Audio",          44, ACCENT, bold=True)
p2 = tf.add_paragraph(); p2.space_before = Pt(6)
run(p2, "Audio Understanding par Intelligence Artificielle", 17, BODY)

sh = rrect(s, 1.1, 3.9, 4.3, 0.52, fill=WHITE, border=ACCENT, bw=Pt(1.5))
tf2 = sh.text_frame
tf2.vertical_anchor = MSO_ANCHOR.MIDDLE
tf2.margin_left = tf2.margin_right = Pt(10)
tf2.margin_top  = tf2.margin_bottom = Pt(0)
pc = tf2.paragraphs[0]; pc.alignment = PP_ALIGN.CENTER
run(pc, "Qwen2-Audio-7B-Instruct", 14, ACCENT_DK, bold=True, font=MONO)

tf = textbox(s, 1.1, 5.1, 11, 1.9,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
p = tf.paragraphs[0]
run(p, "Projet de Fin du Module — Architectures Modernes de Réseaux de Neurones",
    12, MUTED, italic=True)
p2 = tf.add_paragraph(); p2.space_before = Pt(16)
run(p2, "Tassnim & Zineb", 15, INK, bold=True)
p3 = tf.add_paragraph(); p3.space_before = Pt(4)
run(p3, "Encadrant : Pr. Smail Tigani   ·   Année 2025 / 2026", 12, BODY)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Plan
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Plan de la présentation", ACCENT_DK)], 2)

PLAN_ITEMS = [
    "Contexte & objectifs",
    "Le modèle Qwen2-Audio",
    "API opérationnelle (FastAPI)",
    "Interface web",
    "Pipeline technique d'inférence",
    "Déploiement sur Google Colab",
    "Difficultés & solutions",
    "Pistes d'amélioration",
]
COL_W   = (CW - GAP) / 2
ROW_H   = 1.08
ROW_GAP = 0.17
y0 = CONT_Y + 0.06

for i, txt in enumerate(PLAN_ITEMS):
    col = i % 2
    row = i // 2
    x = LM + col * (COL_W + GAP)
    y = y0 + row * (ROW_H + ROW_GAP)
    card_bg(s, x, y, COL_W, ROW_H)
    inner_x = x + BAR_W + 0.14
    inner_w = COL_W - BAR_W - 0.22
    tf = textbox(s, inner_x, y, inner_w, ROW_H, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(6), mr=Pt(6), mt=Pt(4), mb=Pt(4))
    p = tf.paragraphs[0]
    run(p, f"{i + 1}.  ", 15, ACCENT, bold=True)
    run(p, txt,           14, INK,    bold=True)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Contexte & objectifs
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Contexte & objectifs", ACCENT_DK)], 3)

LEFT_W  = CW * 0.48
RIGHT_W = CW - LEFT_W - GAP
right_x = LM + LEFT_W + GAP

bullets(s, LM, CONT_Y, LEFT_W, BOT - CONT_Y,
        "Pourquoi la compréhension audio ?",
        ["Les interfaces vocales sont omniprésentes",
         "Au-delà de la transcription : comprendre le sens",
         "Analyse de réunions, podcasts, cours enregistrés",
         "Accessibilité pour les personnes malentendantes",
         "Marchés en forte croissance"])

tf = textbox(s, right_x, CONT_Y, RIGHT_W, 0.38,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Objectifs du projet", 15, ACCENT_DK, bold=True)

CARD_H   = 1.46
CARD_GAP = GAP
for i, (title, desc, acc) in enumerate([
    ("API opérationnelle",    "3 endpoints POST opérationnels avec le modèle Qwen2-Audio", GREEN),
    ("Mise en application",   "Plateforme web complète d'Audio Understanding",             GREEN),
    ("Rapport & présentation","Documentation académique du travail réalisé",               GREEN),
]):
    cy = CONT_Y + 0.46 + i * (CARD_H + CARD_GAP)
    card(s, right_x, cy, RIGHT_W, CARD_H, title, [desc], accent=acc)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Le modèle
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Le modèle : ", ACCENT_DK), ("Qwen2-Audio-7B-Instruct", ACCENT)], 4)

LEFT_W  = CW * 0.47
RIGHT_W = CW - LEFT_W - GAP
right_x = LM + LEFT_W + GAP

tf = textbox(s, LM, CONT_Y, LEFT_W, 0.38,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Architecture", 15, ACCENT_DK, bold=True)

mono_card(s, LM, CONT_Y + 0.42, LEFT_W, BOT - CONT_Y - 0.42, [
    "Audio  (16 kHz, WAV / MP3 / …)",
    "       |",
    "       v",
    "  Encodeur audio  (Whisper Large V2)",
    "  -> embeddings audio",
    "       |",
    "       v  <-- prompt texte",
    "  Fusion multimodale",
    "  (concaténation des tokens)",
    "       |",
    "       v",
    "  Décodeur Qwen2-7B  (7 Md params)",
    "       |",
    "       v",
    "  Réponse textuelle",
], size=11)

bullets(s, right_x, CONT_Y, RIGHT_W, 4.2,
        "Pourquoi ce modèle ?",
        ["Open source (Apache 2.0) — aucune API payante",
         "Multilingue : français, anglais, arabe…",
         "Traitement natif de la forme d'onde audio",
         "Questions-réponses libres sur le contenu",
         "Analyse émotionnelle et tonale"])

chips(s, right_x, CONT_Y + 4.32,
      ["7 Md paramètres", "Encodeur Whisper", "Instruction-tuned", "HuggingFace"])


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — API FastAPI
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("API opérationnelle — ", ACCENT_DK), ("FastAPI", ACCENT)], 5)

API_ROWS = [
    ("POST", "/api/v1/audio/transcribe", "Audio → transcription complète",                ACCENT),
    ("POST", "/api/v1/audio/understand", "Audio + question → réponse en langage naturel", ACCENT),
    ("POST", "/api/v1/audio/analyze",    "Audio → transcription + résumé + sentiment",    ACCENT),
    ("GET",  "/api/v1/health",           "État du serveur et du modèle chargé",           GREEN),
]

ROW_H   = 0.80
ROW_GAP = 0.09
BADGE_W = 0.80
PATH_X  = LM + BADGE_W + 0.30
PATH_W  = 4.50
DESC_X  = PATH_X + PATH_W + 0.18
DESC_W  = LM + CW - DESC_X

ry = CONT_Y
for meth, path, desc, col in API_ROWS:
    card_bg(s, LM, ry, CW, ROW_H, accent=col)

    badge_y = ry + (ROW_H - 0.36) / 2
    sh = rrect(s, LM + 0.16, badge_y, BADGE_W, 0.36,
               fill=col, border=None, radius=0.3)
    btf = sh.text_frame
    btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    btf.margin_left = btf.margin_right = Pt(4)
    btf.margin_top  = btf.margin_bottom = Pt(0)
    bp = btf.paragraphs[0]; bp.alignment = PP_ALIGN.CENTER
    run(bp, meth, 11, WHITE, bold=True, font=MONO)

    tf = textbox(s, PATH_X, ry, PATH_W, ROW_H, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
    run(tf.paragraphs[0], path, 12, ACCENT_DK, bold=True, font=MONO)

    tf = textbox(s, DESC_X, ry, DESC_W, ROW_H, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(0), mr=Pt(6), mt=Pt(0), mb=Pt(0))
    run(tf.paragraphs[0], desc, 12, BODY)

    ry += ROW_H + ROW_GAP

EX_Y = ry + 0.14
EX_W = (CW - GAP) / 2

tf = textbox(s, LM, EX_Y, EX_W, 0.32,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Exemple — /understand", 13, ACCENT_DK, bold=True)
mono_card(s, LM, EX_Y + 0.34, EX_W, BOT - EX_Y - 0.34, [
    "curl -X POST .../audio/understand \\",
    '  -F "audio=@reunion.wav" \\',
    '  -F "question=Quelle langue ?"',
], size=10)

right_x = LM + EX_W + GAP
tf = textbox(s, right_x, EX_Y, EX_W, 0.32,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Réponse JSON", 13, ACCENT_DK, bold=True)
mono_card(s, right_x, EX_Y + 0.34, EX_W, BOT - EX_Y - 0.34, [
    '{',
    '  "answer": "L\'audio est en français…",',
    '  "filename": "reunion.wav"',
    '}',
], size=10)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Interface web
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Interface web — ", ACCENT_DK), ("3 fonctionnalités", ACCENT)], 6)

NCOLS = 3
COL_W = (CW - (NCOLS - 1) * GAP) / NCOLS
COL_H = 3.18
FOOT_Y = CONT_Y + COL_H + GAP
FOOT_H = BOT - FOOT_Y

for i, (title, lines) in enumerate([
    ("Transcrire",  ["Import de fichier audio",   "Enregistrement microphone",
                     "Transcription complète",     "Copie en un clic"]),
    ("Comprendre",  ["Audio + question libre",     "Réponse contextuelle",
                     "Langage naturel",            "Questions-réponses ouvertes"]),
    ("Analyser",    ["Transcription intégrale",    "Résumé automatique",
                     "Détection du sentiment",     "Rapport complet"]),
]):
    x = LM + i * (COL_W + GAP)
    card(s, x, CONT_Y, COL_W, COL_H, title, lines)

card_bg(s, LM, FOOT_Y, CW, FOOT_H, accent=ACCENT)
inner_x = LM + BAR_W + 0.14
inner_w = CW - BAR_W - 0.22
tf = textbox(s, inner_x, FOOT_Y, inner_w, FOOT_H, anchor=MSO_ANCHOR.MIDDLE,
             ml=Pt(6), mr=Pt(6), mt=Pt(6), mb=Pt(6))
p = tf.paragraphs[0]; p.space_after = Pt(4)
run(p, "Technologies front-end", 14, INK, bold=True)
p2 = tf.add_paragraph()
run(p2,
    "HTML5 / CSS3 / JavaScript vanilla — MediaRecorder API, Fetch API, glisser-déposer. "
    "Interface en français servie directement par le backend FastAPI (même origine).",
    12, BODY)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Pipeline d'inférence
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Pipeline technique d'inférence", ACCENT_DK)], 7)

PIPELINE_STEPS = [
    ("1. Réception",          "Requête HTTP POST multipart/form-data — validation : format, taille ≤ 50 Mo, contenu non vide"),
    ("2. Décodage audio",     "soundfile → WAV/FLAC/OGG ; librosa + ffmpeg → MP3/M4A/WebM-Opus"),
    ("3. Rééchantillonnage",  "Conversion en 16 000 Hz, mono, float32 (fréquence attendue par l'encodeur)"),
    ("4. Chat template",      "Construction de la conversation Qwen2-Audio (tokens audio + tokens texte)"),
    ("5. AutoProcessor",      "Texte → tokens ; audio → input_features → tenseurs PyTorch"),
    ("6. Inférence GPU",      "model.generate() → décodage autorégressif des tokens → réponse textuelle"),
    ("7. Sérialisation",      "Réponse JSON → HTTP 200"),
]

N = len(PIPELINE_STEPS)
STEP_H = (BOT - CONT_Y - (N - 1) * GAP) / N
LABEL_W = 2.50
SEP_X   = LM + BAR_W + 0.14 + LABEL_W + 0.10
DESC_X  = SEP_X + 0.16
DESC_W  = LM + CW - DESC_X

sy = CONT_Y
for title, desc in PIPELINE_STEPS:
    card_bg(s, LM, sy, CW, STEP_H)

    tf = textbox(s, LM + BAR_W + 0.14, sy, LABEL_W, STEP_H,
                 anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(0), mr=Pt(4), mt=Pt(0), mb=Pt(0))
    run(tf.paragraphs[0], title, 13, ACCENT_DK, bold=True)

    sep = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                             Inches(SEP_X), Inches(sy + STEP_H * 0.15),
                             Pt(1.0), Inches(STEP_H * 0.70))
    sep.fill.solid(); sep.fill.fore_color.rgb = CARD_BD
    sep.line.fill.background(); sep.shadow.inherit = False

    tf = textbox(s, DESC_X, sy, DESC_W, STEP_H,
                 anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(6), mr=Pt(6), mt=Pt(0), mb=Pt(0))
    run(tf.paragraphs[0], desc, 12, BODY)

    sy += STEP_H + GAP


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Déploiement Google Colab
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Déploiement sur ", ACCENT_DK), ("Google Colab", ACCENT)], 8)

LEFT_W  = CW * 0.485
RIGHT_W = CW - LEFT_W - GAP
right_x = LM + LEFT_W + GAP

bullets(s, LM, CONT_Y, LEFT_W, BOT - CONT_Y,
        "Mise en service",
        ["GPU NVIDIA A100 — modèle float16 complet (~16 Go)",
         "Clonage du dépôt GitHub dans l'environnement Colab",
         "Serveur uvicorn lancé sur le port 8000",
         "Tunnel public cloudflared → URL trycloudflare.com",
         "UI et API servies sur la même origine : une seule URL"])

tf = textbox(s, right_x, CONT_Y, RIGHT_W, 0.38,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Flux de déploiement", 15, ACCENT_DK, bold=True)

DIAG_H  = 2.20
mono_card(s, right_x, CONT_Y + 0.44, RIGHT_W, DIAG_H, [
    "GPU Colab A100",
    "      |",
    "  uvicorn : 8000",
    "      |",
    "  cloudflared (tunnel)",
    "      |",
    "  URL publique → navigateur",
], size=12)

QUANT_Y = CONT_Y + 0.44 + DIAG_H + GAP
card(s, right_x, QUANT_Y, RIGHT_W, BOT - QUANT_Y,
     "Quantification optionnelle",
     ["4 ou 8 bits via bitsandbytes",
      "Variables : LOAD_IN_4BIT / LOAD_IN_8BIT",
      "Pour les GPU < 16 Go (ex. Colab T4)"],
     accent=GREEN)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Difficultés & solutions
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Difficultés & solutions", ACCENT_DK)], 9)

DIFFS = [
    ("Formats audio hétérogènes",
     "Les navigateurs enregistrent en WebM/Opus, non géré par soundfile. "
     "Solution : double décodeur — soundfile d'abord, puis librosa + ffmpeg en secours."),
    ("Audio non transmis au modèle",
     "Le modèle répondait « je ne peux pas accéder à l'audio » sans erreur visible. "
     "Cause : l'argument du processeur a été renommé selon la version de transformers "
     "(audios → audio) et était silencieusement ignoré. "
     "Solution : essayer les deux noms, vérifier input_features "
     "(erreur explicite sinon) et aligner le dtype audio en float16."),
    ("Ressources mémoire (~16 Go VRAM)",
     "Le modèle 7B en float16 exige un GPU conséquent. "
     "Solution : GPU Colab A100 + quantification 4/8 bits pour les GPU plus modestes."),
]

N = len(DIFFS)
DIFF_H = (BOT - CONT_Y - (N - 1) * GAP) / N
dy = CONT_Y
for title, desc in DIFFS:
    card_bg(s, LM, dy, CW, DIFF_H)
    inner_x = LM + BAR_W + 0.14
    inner_w = CW - BAR_W - 0.22
    tf = textbox(s, inner_x, dy, inner_w, DIFF_H,
                 anchor=MSO_ANCHOR.TOP,
                 ml=Pt(4), mr=Pt(6), mt=Pt(12), mb=Pt(8))
    p = tf.paragraphs[0]; p.space_after = Pt(6)
    run(p, title, 14, INK, bold=True)
    p2 = tf.add_paragraph()
    run(p2, desc, 12, BODY)
    dy += DIFF_H + GAP


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Pistes d'amélioration
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()
header(s, [("Pistes d'amélioration", ACCENT_DK)], 10)

IMPROVEMENTS = [
    ("Streaming des réponses",      "Server-Sent Events : afficher les tokens au fur et à mesure."),
    ("Conversation multi-tours",    "Conserver l'historique des échanges sur un même audio."),
    ("Détection de langue",         "Identifier la langue et adapter la réponse automatiquement."),
    ("Traitement des audios longs", "Découpage (chunking) pour réunions et conférences."),
    ("Quantification avancée",      "GPTQ / AWQ au-delà du 4/8 bits déjà pris en charge."),
    ("Évaluation formelle (WER)",   "Mesurer le Word Error Rate sur un corpus francophone."),
]

NCOLS  = 2
IMP_W  = (CW - GAP) / NCOLS
IMP_H  = (BOT - CONT_Y - GAP) / 3

for i, (t, d) in enumerate(IMPROVEMENTS):
    col = i % NCOLS
    row = i // NCOLS
    x = LM + col * (IMP_W + GAP)
    y = CONT_Y + row * (IMP_H + GAP)
    card(s, x, y, IMP_W, IMP_H, t, [d])


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Conclusion
# ════════════════════════════════════════════════════════════════════════════
s = new_slide()

band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.16))
band.fill.solid(); band.fill.fore_color.rgb = ACCENT
band.line.fill.background(); band.shadow.inherit = False

tf = textbox(s, 1.0, 1.0, 11.3, 0.85,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
run(tf.paragraphs[0], "Merci de votre attention", 32, INK, bold=True)

CONCL_ITEMS = [
    "3 endpoints POST opérationnels — /transcribe · /understand · /analyze",
    "Interface web claire : import fichier, enregistrement micro et 3 onglets",
    "Déployé sur GPU Colab A100 — modèle open source, aucune API payante",
]
CONCL_H = 0.90
cy = 2.05
for txt in CONCL_ITEMS:
    card_bg(s, 1.0, cy, 11.3, CONCL_H, accent=GREEN)
    inner_x = 1.0 + BAR_W + 0.14
    inner_w = 11.3 - BAR_W - 0.22
    tf = textbox(s, inner_x, cy, inner_w, CONCL_H, anchor=MSO_ANCHOR.MIDDLE,
                 ml=Pt(4), mr=Pt(4), mt=Pt(0), mb=Pt(0))
    run(tf.paragraphs[0], txt, 14, BODY)
    cy += CONCL_H + GAP

tf = textbox(s, 1.0, cy + 0.18, 11.3, 0.9,
             ml=Pt(0), mr=Pt(0), mt=Pt(0), mb=Pt(0))
p = tf.paragraphs[0]
run(p, "Tassnim & Zineb", 15, INK, bold=True)
p2 = tf.add_paragraph(); p2.space_before = Pt(4)
run(p2, "Pr. Smail Tigani · Université Euromed de Fès · EIDIA · 2025/2026", 12, MUTED)


# ── Save ─────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presentation.pptx")
prs.save(out)
print(f"Saved: {out}  ({len(prs.slides._sldIdLst)} slides)")
