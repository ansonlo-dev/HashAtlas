"""Preserve slide 2's click-to-play video when a headless PDF exporter omits media."""
from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name, String

presentation = Path(__file__).resolve().parents[1]
deck = presentation / "HashAtlas.pdf"
with pikepdf.open(deck, allow_overwriting_input=True) as pdf:
    page = pdf.pages[1]
    annotations = page.obj.get("/Annots", Array())
    if not any(a.get("/Subtype") == Name.Screen for a in annotations):
        media = pdf.make_stream((presentation / "video/hashatlas_intro.mp4").read_bytes())
        media.Type = Name.EmbeddedFile
        file = Dictionary(Type=Name.Filespec, F=String("hashatlas_intro.mp4"), EF=Dictionary(F=media))
        clip = Dictionary(Type=Name.MediaClip, S=Name.MCD, D=file, CT=String("video/mp4"),
                          P=Dictionary(TF=String("TEMPACCESS")))
        rendition = Dictionary(Type=Name.Rendition, S=Name.MR, C=clip)
        # The slide uses inches from the top left. PDF annotations use points from the bottom left.
        left, top, width, height = 1.47, 0.9, 10.4, 5.85
        page_height = float(page.MediaBox[3])
        rect = [left * 72, page_height - (top + height) * 72, (left + width) * 72, page_height - top * 72]
        screen = pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Screen, Rect=rect, P=page.obj))
        screen.A = Dictionary(Type=Name.Action, S=Name.Rendition, AN=screen, R=rendition, OP=0)
        annotations.append(screen)
        page.obj.Annots = annotations
        pdf.save(deck)
