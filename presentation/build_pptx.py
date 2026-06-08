#!/usr/bin/env python3
"""Génère presentation.pptx — thème clair, en français, sans emojis.

Usage : python3 build_pptx.py
Dépendance : python-pptx  (pip install python-pptx)
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Palette (thème clair, cohérent avec l'interface web) ────────────────────
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
INK        = RGBColor(0x0F, 0x17, 0x2A)  # slate-900
BODY       = RGBColor(0x33, 0x41, 0x55)  # slate-700
MUTED      = RGBColor(0x94, 0xA3, 0xB8)  # slate-400
ACCENT     = RGBColor(0x4F, 0x46, 0xE5)  # indigo-600
ACCENT_DK  = RGBColor(0x43, 0x38, 0xCA)  # indigo-700
CARD       = RGBColor(0xF8, 0xFA, 0xFC)  # slate-50
CARD_LINE  = RGBColor(0xE2, 0xE8, 0xF0)  # slate-200
CHIP_BG    = RGBColor(0xEE, 0xF2, 0xFF)  # indigo-50
GREEN      = RGBColor(0x05, 0x96, 0x69)  # emerald-600

FONT       = "Arial"
MONO       = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]

TOTAL = 11  # mis à jour à la fin


# ── Helpers ─────────────────────────────────────────────────────────────────
def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid(); bg.fill.fore_color.rgb = WHITE
    bg.line.fill.background(); bg.shadow.inherit = False
    return s


def _set(run, size, color, bold=False, font=FONT, italic=False):
    run.font.size = Pt(size); run.font.color.rgb = color
    run.font.bold = bold; run.font.italic = italic; run.font.name = font


def textbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    return tf


def header(s, title_parts, num):
    """title_parts: list of (text, color) tuples."""
    tf = textbox(s, 0.7, 0.45, 10.5, 0.8)
    p = tf.paragraphs[0]
    for txt, col in title_parts:
        r = p.add_run(); r.text = txt; _set(r, 28, col, bold=True)
    # numéro de slide
    tn = textbox(s, 11.4, 0.55, 1.3, 0.5)
    pn = tn.paragraphs[0]; pn.alignment = PP_ALIGN.RIGHT
    r = pn.add_run(); r.text = f"{num} / {TOTAL}"; _set(r, 12, MUTED, font=MONO)
    # filet accent
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.32),
                              Inches(11.93), Pt(2.5))
    rule.fill.solid(); rule.fill.fore_color.rgb = ACCENT
    rule.line.fill.background(); rule.shadow.inherit = False


def rrect(s, x, y, w, h, fill=CARD, line=CARD_LINE, line_w=1.0, accent_bar=None):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    if accent_bar:
        bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                 Inches(0.07), Inches(h))
        bar.adjustments[0] = 0.5
        bar.fill.solid(); bar.fill.fore_color.rgb = accent_bar
        bar.line.fill.background(); bar.shadow.inherit = False
    return sh


def card(s, x, y, w, h, title, lines, accent=ACCENT):
    rrect(s, x, y, w, h, accent_bar=accent)
    tf = textbox(s, x + 0.28, y + 0.2, w - 0.45, h - 0.35)
    p = tf.paragraphs[0]; p.space_after = Pt(6)
    r = p.add_run(); r.text = title; _set(r, 15, INK, bold=True)
    for ln in lines:
        para = tf.add_paragraph(); para.space_after = Pt(3)
        r = para.add_run(); r.text = ln; _set(r, 12, BODY)


def bullets(s, x, y, w, h, heading, items, color=ACCENT):
    tf = textbox(s, x, y, w, h)
    p = tf.paragraphs[0]; p.space_after = Pt(8)
    r = p.add_run(); r.text = heading; _set(r, 16, ACCENT_DK, bold=True)
    for it in items:
        para = tf.add_paragraph(); para.space_after = Pt(7)
        rb = para.add_run(); rb.text = "•  "; _set(rb, 13, color, bold=True)
        rt = para.add_run(); rt.text = it; _set(rt, 13, BODY)


def chips(s, x, y, labels, gap=0.12):
    cx = x
    for lab in labels:
        w = 0.13 * len(lab) + 0.4
        c = rrect(s, cx, y, w, 0.34, fill=CHIP_BG, line=None)
        tf = c.text_frame; tf.word_wrap = False
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = lab; _set(r, 11, ACCENT_DK, bold=True)
        cx += w + gap


def mono_card(s, x, y, w, h, lines, size=11):
    rrect(s, x, y, w, h, fill=CARD, accent_bar=ACCENT)
    tf = textbox(s, x + 0.3, y + 0.22, w - 0.5, h - 0.4)
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(2)
        r = p.add_run(); r.text = ln; _set(r, size, BODY, font=MONO)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Couverture
# ════════════════════════════════════════════════════════════════════════════
s = slide()
# bandeau accent haut
top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.18))
top.fill.solid(); top.fill.fore_color.rgb = ACCENT
top.line.fill.background(); top.shadow.inherit = False

tf = textbox(s, 1.2, 1.5, 11, 0.6)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Université Euromed de Fès  ·  EIDIA"
_set(r, 14, MUTED, bold=True)

tf = textbox(s, 1.2, 2.5, 11, 1.6)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Compréhension "; _set(r, 46, INK, bold=True)
r = p.add_run(); r.text = "Audio"; _set(r, 46, ACCENT, bold=True)
p2 = tf.add_paragraph(); p2.space_before = Pt(6)
r = p2.add_run(); r.text = "Audio Understanding par Intelligence Artificielle"
_set(r, 18, BODY)

chip = rrect(s, 1.2, 4.4, 4.1, 0.5, fill=WHITE, line=ACCENT, line_w=1.25)
tfc = chip.text_frame; tfc.vertical_anchor = MSO_ANCHOR.MIDDLE
pc = tfc.paragraphs[0]; pc.alignment = PP_ALIGN.CENTER
r = pc.add_run(); r.text = "Qwen2-Audio-7B-Instruct"; _set(r, 15, ACCENT_DK, bold=True, font=MONO)

tf = textbox(s, 1.2, 5.5, 11, 1.4)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Projet de Fin du Module — Architectures Modernes de Réseaux de Neurones"
_set(r, 13, MUTED, italic=True)
p = tf.add_paragraph(); p.space_before = Pt(10)
r = p.add_run(); r.text = "Tassnim & Zineb"; _set(r, 15, INK, bold=True)
p = tf.add_paragraph(); p.space_before = Pt(2)
r = p.add_run(); r.text = "Encadrant : Pr. Smail Tigani   ·   Année : 2025 / 2026"
_set(r, 13, BODY)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Plan
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Plan de la présentation", ACCENT_DK)], 2)
plan = [
    "Contexte & objectifs",
    "Le modèle Qwen2-Audio",
    "API opérationnelle (FastAPI)",
    "Interface web",
    "Pipeline technique d'inférence",
    "Déploiement sur Google Colab",
    "Difficultés & solutions",
    "Pistes d'amélioration",
]
x0, y0, w, h, gx, gy = 0.7, 1.7, 5.9, 0.95, 0.13, 0.22
for i, txt in enumerate(plan):
    col, row = i % 2, i // 2
    x = x0 + col * (w + gx); y = y0 + row * (h + gy)
    rrect(s, x, y, w, h, accent_bar=ACCENT)
    tf = textbox(s, x + 0.35, y, w - 0.5, h, anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    rn = p.add_run(); rn.text = f"{i+1}.  "; _set(rn, 16, ACCENT, bold=True)
    rt = p.add_run(); rt.text = txt; _set(rt, 15, INK, bold=True)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Contexte & objectifs
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Contexte & objectifs", ACCENT_DK)], 3)
bullets(s, 0.7, 1.7, 5.9, 5,
        "Pourquoi la compréhension audio ?",
        ["Les interfaces vocales sont omniprésentes",
         "Au-delà de la transcription : comprendre le sens",
         "Analyse de réunions, podcasts, cours enregistrés",
         "Accessibilité pour les personnes malentendantes",
         "Marchés en forte croissance (assistants, centres d'appels, éducation)"])
ty = 1.7
tf = textbox(s, 6.95, ty, 5.7, 0.5)
p = tf.paragraphs[0]; r = p.add_run(); r.text = "Objectifs du projet"
_set(r, 16, ACCENT_DK, bold=True)
card(s, 6.95, ty + 0.55, 5.65, 1.35, "API opérationnelle",
     ["Points de terminaison POST fonctionnels avec le modèle"], accent=GREEN)
card(s, 6.95, ty + 2.05, 5.65, 1.35, "Mise en application",
     ["Plateforme web complète d'Audio Understanding"], accent=GREEN)
card(s, 6.95, ty + 3.55, 5.65, 1.35, "Rapport & présentation",
     ["Documentation académique du travail réalisé"], accent=GREEN)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Le modèle
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Le modèle : ", ACCENT_DK), ("Qwen2-Audio-7B-Instruct", ACCENT)], 4)
tf = textbox(s, 0.7, 1.6, 5.9, 0.4)
p = tf.paragraphs[0]; r = p.add_run(); r.text = "Architecture"
_set(r, 16, ACCENT_DK, bold=True)
mono_card(s, 0.7, 2.1, 5.9, 4.6, [
    "Audio  (16 kHz, WAV / MP3 / …)",
    "        |",
    "        v",
    "  Encodeur audio",
    "  Whisper Large V2",
    "  -> embeddings audio",
    "        |",
    "        v   <-- prompt texte",
    "  Fusion multimodale",
    "  (concaténation des tokens)",
    "        |",
    "        v",
    "  Décodeur Qwen2-7B",
    "  (7 milliards de paramètres)",
    "  génération autorégressive",
    "        |",
    "        v",
    "  Réponse textuelle",
], size=12)
bullets(s, 6.95, 1.6, 5.7, 4,
        "Pourquoi ce modèle ?",
        ["Open source (Apache 2.0) — aucune API payante",
         "Multilingue : français, anglais, arabe…",
         "Traitement natif de la forme d'onde audio",
         "Questions-réponses libres sur le contenu",
         "Analyse émotionnelle et tonale"])
chips(s, 6.95, 5.7, ["7 Md paramètres", "Encodeur Whisper", "Instruction-tuned", "HuggingFace"])

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — API FastAPI
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("API opérationnelle — ", ACCENT_DK), ("FastAPI", ACCENT)], 5)
rows = [
    ("POST", "/api/v1/audio/transcribe", "Audio → transcription complète", ACCENT),
    ("POST", "/api/v1/audio/understand", "Audio + question → réponse en langage naturel", ACCENT),
    ("POST", "/api/v1/audio/analyze", "Audio → transcription + résumé + sentiment", ACCENT),
    ("GET", "/api/v1/health", "État du serveur et du modèle chargé", GREEN),
]
ry = 1.7
for meth, path, desc, col in rows:
    rrect(s, 0.7, ry, 11.93, 0.78, accent_bar=col)
    mt = rrect(s, 1.0, ry + 0.2, 0.95, 0.38, fill=col, line=None)
    tfm = mt.text_frame; tfm.vertical_anchor = MSO_ANCHOR.MIDDLE
    pm = tfm.paragraphs[0]; pm.alignment = PP_ALIGN.CENTER
    r = pm.add_run(); r.text = meth; _set(r, 11, WHITE, bold=True, font=MONO)
    tfp = textbox(s, 2.15, ry, 4.3, 0.78, anchor=MSO_ANCHOR.MIDDLE)
    r = tfp.paragraphs[0].add_run(); r.text = path; _set(r, 13, ACCENT_DK, bold=True, font=MONO)
    tfd = textbox(s, 6.6, ry, 5.8, 0.78, anchor=MSO_ANCHOR.MIDDLE)
    r = tfd.paragraphs[0].add_run(); r.text = desc; _set(r, 12, BODY)
    ry += 0.92
# exemple + réponse
ey = ry + 0.1
tf = textbox(s, 0.7, ey, 5, 0.35)
r = tf.paragraphs[0].add_run(); r.text = "Exemple — /understand"; _set(r, 13, ACCENT_DK, bold=True)
mono_card(s, 0.7, ey + 0.4, 5.9, 1.2, [
    "curl -X POST .../audio/understand \\",
    '  -F "audio=@reunion.wav" \\',
    '  -F "question=Quelle langue ?"',
], size=10)
tf = textbox(s, 6.95, ey, 5, 0.35)
r = tf.paragraphs[0].add_run(); r.text = "Réponse JSON"; _set(r, 13, ACCENT_DK, bold=True)
mono_card(s, 6.95, ey + 0.4, 5.7, 1.2, [
    "{",
    '  "answer": "L\'audio est en français…",',
    '  "filename": "reunion.wav"',
    "}",
], size=10)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Interface web
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Interface web — ", ACCENT_DK), ("3 fonctionnalités", ACCENT)], 6)
cw, cx0, cy = 3.82, 0.7, 1.8
card(s, cx0, cy, cw, 3.0, "Transcrire",
     ["Import de fichier audio", "Enregistrement micro", "Transcription complète", "Copie en un clic"])
card(s, cx0 + (cw + 0.23), cy, cw, 3.0, "Comprendre",
     ["Audio + question libre", "Réponse contextuelle", "Tout en langage naturel", "Questions-réponses ouvertes"])
card(s, cx0 + 2 * (cw + 0.23), cy, cw, 3.0, "Analyser",
     ["Transcription intégrale", "Résumé automatique", "Détection du sentiment", "Rapport complet"])
rrect(s, 0.7, 5.1, 11.93, 1.5, accent_bar=ACCENT)
tf = textbox(s, 1.0, 5.3, 11.4, 1.1)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Technologies front-end"; _set(r, 14, INK, bold=True)
p = tf.add_paragraph(); p.space_before = Pt(4)
r = p.add_run(); r.text = ("Application monopage (SPA) en HTML5 / CSS3 / JavaScript vanilla — "
                           "API MediaRecorder, Fetch, glisser-déposer. Interface claire et épurée, "
                           "servie directement par le backend.")
_set(r, 12, BODY)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Pipeline d'inférence
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Pipeline technique d'inférence", ACCENT_DK)], 7)
steps = [
    ("1. Réception", "Requête HTTP POST (multipart/form-data) — validation : format, taille ≤ 50 Mo, contenu non vide"),
    ("2. Décodage audio", "soundfile → WAV/FLAC/OGG ; librosa + ffmpeg → MP3/M4A/WebM-Opus"),
    ("3. Rééchantillonnage", "Conversion en 16 000 Hz, mono, float32 (fréquence attendue par l'encodeur)"),
    ("4. Chat template", "Construction de la conversation Qwen2-Audio (tokens audio + tokens texte)"),
    ("5. AutoProcessor", "Texte → tokens ; audio → caractéristiques (input_features) → tenseurs PyTorch"),
    ("6. Inférence", "model.generate() → décodage des tokens → réponse textuelle"),
    ("7. Sérialisation", "Réponse JSON → HTTP 200"),
]
sy = 1.65
for title, desc in steps:
    rrect(s, 0.7, sy, 11.93, 0.68, accent_bar=ACCENT)
    tf = textbox(s, 1.0, sy, 2.6, 0.68, anchor=MSO_ANCHOR.MIDDLE)
    r = tf.paragraphs[0].add_run(); r.text = title; _set(r, 13, ACCENT_DK, bold=True)
    tf = textbox(s, 3.7, sy, 8.7, 0.68, anchor=MSO_ANCHOR.MIDDLE)
    r = tf.paragraphs[0].add_run(); r.text = desc; _set(r, 12, BODY)
    sy += 0.78

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Déploiement Google Colab
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Déploiement sur ", ACCENT_DK), ("Google Colab", ACCENT)], 8)
bullets(s, 0.7, 1.7, 6.0, 5,
        "Mise en service",
        ["GPU NVIDIA A100 — modèle en float16 complet (~16 Go)",
         "Clonage du dépôt GitHub dans l'environnement Colab",
         "Serveur uvicorn lancé sur le port 8000",
         "Tunnel public cloudflared → URL trycloudflare.com",
         "UI et API servies sur la même origine : une seule URL"])
tf = textbox(s, 7.0, 1.7, 5.6, 0.4)
r = tf.paragraphs[0].add_run(); r.text = "Flux de déploiement"; _set(r, 16, ACCENT_DK, bold=True)
mono_card(s, 7.0, 2.2, 5.6, 2.2, [
    "GPU Colab A100",
    "      |",
    "  uvicorn : 8000",
    "      |",
    "  cloudflared (tunnel)",
    "      |",
    "  URL publique -> navigateur",
], size=12)
card(s, 7.0, 4.7, 5.6, 1.9, "Quantification optionnelle",
     ["4 ou 8 bits via bitsandbytes (LOAD_IN_4BIT / 8BIT)",
      "Permet d'exécuter le modèle sur des GPU plus modestes (ex. Colab T4 ~15 Go)"],
     accent=GREEN)

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Difficultés & solutions
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Difficultés & solutions", ACCENT_DK)], 9)
diffs = [
    ("Formats audio hétérogènes",
     "Les navigateurs enregistrent en WebM/Opus, non géré par soundfile. "
     "Solution : double décodeur — soundfile, puis librosa + ffmpeg en secours."),
    ("Audio non transmis au modèle",
     "Le modèle répondait « je ne peux pas accéder à l'audio », sans erreur. Cause : l'argument "
     "du processeur a été renommé selon la version de transformers (audios → audio) et "
     "était ignoré silencieusement. Solution : essayer les deux noms, vérifier la présence de "
     "input_features (échec explicite sinon) et aligner le type (float16)."),
    ("Ressources mémoire (~16 Go VRAM)",
     "Le modèle 7B en float16 exige un GPU conséquent. Solution : GPU Colab A100 + "
     "option de quantification 4/8 bits pour les cartes plus petites."),
]
dy = 1.7
for title, desc in diffs:
    h = 1.55
    rrect(s, 0.7, dy, 11.93, h, accent_bar=ACCENT)
    tf = textbox(s, 1.0, dy + 0.18, 11.4, h - 0.3)
    p = tf.paragraphs[0]; p.space_after = Pt(4)
    r = p.add_run(); r.text = title; _set(r, 14, INK, bold=True)
    p = tf.add_paragraph()
    r = p.add_run(); r.text = desc; _set(r, 12, BODY)
    dy += h + 0.12

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Pistes d'amélioration
# ════════════════════════════════════════════════════════════════════════════
s = slide()
header(s, [("Pistes d'amélioration", ACCENT_DK)], 10)
items = [
    ("Streaming des réponses", "Server-Sent Events : afficher les tokens au fur et à mesure."),
    ("Conversation multi-tours", "Conserver l'historique des échanges sur un même audio."),
    ("Détection de langue", "Identifier la langue du locuteur et adapter la réponse."),
    ("Traitement des audios longs", "Découpage (chunking) pour réunions et conférences."),
    ("Quantification avancée", "GPTQ / AWQ au-delà du 4/8 bits déjà pris en charge."),
    ("Évaluation formelle (WER)", "Mesurer le Word Error Rate sur un corpus francophone."),
]
x0, y0, w, h, gx, gy = 0.7, 1.75, 5.9, 1.45, 0.13, 0.2
for i, (t, d) in enumerate(items):
    col, row = i % 2, i // 2
    x = x0 + col * (w + gx); y = y0 + row * (h + gy)
    card(s, x, y, w, h, t, [d])

# ════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Conclusion
# ════════════════════════════════════════════════════════════════════════════
s = slide()
band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.18))
band.fill.solid(); band.fill.fore_color.rgb = ACCENT
band.line.fill.background(); band.shadow.inherit = False

tf = textbox(s, 1.2, 1.3, 11, 1.0)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Merci de votre attention"; _set(r, 34, INK, bold=True)

concl = [
    "3 endpoints POST opérationnels — /transcribe · /understand · /analyze",
    "Interface web claire : import, enregistrement micro et 3 onglets",
    "Déployé sur GPU Colab A100 — modèle open source, aucune API payante",
]
cy = 2.7
for txt in concl:
    rrect(s, 1.2, cy, 10.9, 0.95, accent_bar=GREEN)
    tf = textbox(s, 1.55, cy, 10.4, 0.95, anchor=MSO_ANCHOR.MIDDLE)
    r = tf.paragraphs[0].add_run(); r.text = txt; _set(r, 14, BODY)
    cy += 1.1

tf = textbox(s, 1.2, 6.3, 11, 0.8)
p = tf.paragraphs[0]
r = p.add_run(); r.text = "Tassnim & Zineb"; _set(r, 15, INK, bold=True)
p = tf.add_paragraph(); p.space_before = Pt(2)
r = p.add_run(); r.text = "Pr. Smail Tigani · Université Euromed de Fès · EIDIA · 2025/2026"
_set(r, 12, MUTED)

# ── Sauvegarde ──────────────────────────────────────────────────────────────
import os
out = os.path.join(os.path.dirname(__file__), "presentation.pptx")
prs.save(out)
print("Saved:", out, f"({len(prs.slides._sldIdLst)} slides)")
