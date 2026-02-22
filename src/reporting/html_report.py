"""Generate HTML report artifacts."""
from __future__ import annotations

import pandas as pd


def table_to_html(df: pd.DataFrame, title: str) -> str:
    return f"<h3>{title}</h3>" + df.to_html(index=False, border=0)


def build_report_html(sections: list[tuple[str, str]]) -> str:
    body = "\n".join([f"<section><h2>{title}</h2><div>{content}</div></section>" for title, content in sections])
    return f"""
    <html>
    <head>
      <style>
        body {{font-family: Arial, sans-serif; margin: 24px;}}
        h1, h2 {{color: #1E3A8A;}}
        table {{border-collapse: collapse; width: 100%;}}
        th, td {{border: 1px solid #ddd; padding: 8px; text-align: right;}}
        th {{background: #f3f4f6;}}
      </style>
    </head>
    <body>
      <h1>Cross-Asset Market Monitor Report</h1>
      {body}
    </body>
    </html>
    """
