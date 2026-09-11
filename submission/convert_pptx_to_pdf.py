"""
convert_pptx_to_pdf.py — uses the real, installed PowerPoint (via COM
automation) to export Relay_Pitch_Deck.pptx to a PDF with identical
content/layout, so Unstop's separate PDF and PPT uploads aren't two
independently-built decks that can drift out of sync.

Run: python convert_pptx_to_pdf.py
"""

import os
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
PPTX_PATH = os.path.join(HERE, "Relay_Pitch_Deck.pptx")
PDF_PATH = os.path.join(HERE, "Relay_Pitch_Deck.pdf")

ppSaveAsPDF = 32


def main():
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    presentation = powerpoint.Presentations.Open(PPTX_PATH, WithWindow=False)
    try:
        presentation.SaveAs(PDF_PATH, ppSaveAsPDF)
        print(f"wrote {PDF_PATH}")
    finally:
        presentation.Close()
        powerpoint.Quit()


if __name__ == "__main__":
    main()
