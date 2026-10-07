from pathlib import Path
import sys

import pypdfium2 as pdfium


def main():
    pdf_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf = pdfium.PdfDocument(str(pdf_path))
    for index, page in enumerate(pdf, start=1):
        bitmap = page.render(scale=2.0).to_pil()
        out = out_dir / f"page-{index}.png"
        bitmap.save(out)
        print(out)


if __name__ == "__main__":
    main()
