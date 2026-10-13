#!/usr/bin/env python3
"""
Convert sample markdown documents to PDF for Playground upload.
Requires: pip install markdown weasyprint
"""

import os
import sys
from pathlib import Path

def convert_md_to_pdf(md_path: Path, pdf_path: Path):
    """Convert markdown file to PDF."""
    try:
        import markdown
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "markdown", "weasyprint"], check=True)
        import markdown
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

    # Read markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )

    # Add styling
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Calibri, Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                color: #333;
            }}
            h1, h2, h3, h4 {{ color: #1a3c5e; margin-top: 1.5em; }}
            h1 {{ border-bottom: 2px solid #1a3c5e; padding-bottom: 10px; }}
            h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #1a3c5e; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
            pre {{ background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            pre code {{ background: none; padding: 0; color: inherit; }}
            blockquote {{ border-left: 4px solid #1a3c5e; padding-left: 15px; color: #666; margin: 1em 0; }}
            .header-info {{ background: #f0f4f8; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 1em 0; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Generate PDF
    font_config = FontConfiguration()
    HTML(string=styled_html).write_pdf(
        pdf_path,
        font_config=font_config,
        stylesheets=[CSS(string='@page { margin: 2cm; }')]
    )
    print(f"✅ Created: {pdf_path}")

def main():
    docs_dir = Path(__file__).parent / "sample_documents"
    md_files = list(docs_dir.glob("*.md"))

    if not md_files:
        print("No markdown files found in sample_documents/")
        return

    print(f"Converting {len(md_files)} markdown files to PDF...\n")

    for md_file in md_files:
        pdf_file = md_file.with_suffix('.pdf')
        try:
            convert_md_to_pdf(md_file, pdf_file)
        except Exception as e:
            print(f"❌ Failed to convert {md_file.name}: {e}")

    print(f"\n✅ Done! PDFs ready in {docs_dir}")
    print("Upload these PDFs to Azure AI Foundry Playground → Knowledge → Add files")

if __name__ == "__main__":
    main()