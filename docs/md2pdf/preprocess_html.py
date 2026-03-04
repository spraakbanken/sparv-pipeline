"""Preprocess html (created by Zensical) to serve as input for Pandoc.

Remove headers, footers, styles, scripts, and other unwanted elements.
Convert admonitions to a more suitable format.

This script is used by the `md2pdf.sh` script to prepare HTML files for conversion to PDF.
"""

import argparse
from pathlib import Path

from bs4 import BeautifulSoup


def preprocess_html(input_file: str, output_file: str, hide_docstring: bool) -> None:
    """Preprocess the HTML file to remove headers, footers, styles, and scripts."""
    content = Path(input_file).read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Get main tag and attach it to new html tag
    html_tag = soup.new_tag("html")
    main_tag = soup.find("main")
    main_tag.name = "body"
    html_tag.append(main_tag)

    if hide_docstring:
        # Remove p tag within div with class="doc doc-contents first"
        for div in html_tag.find_all("div", class_="doc doc-contents first"):
            first_p = div.find("p")
            if first_p:
                first_p.decompose()

    # Remove some unwanted tags
    for tag in html_tag.find_all(["style", "script", "input", "label", "nav", "head", "header", "footer", "button"]):
        tag.decompose()

    # Remove tags containing "headerlink" class
    for tag in html_tag.find_all(class_="headerlink"):
        tag.decompose()

    # Remove tags containing and attribute that starts with "md-sidebar"
    for tag in html_tag.find_all(attrs=lambda attr: attr and attr.startswith("md-sidebar")):
        tag.decompose()

    # Remove all <span> tags but keep their content
    for tag in html_tag.find_all("span"):
        tag.unwrap()

    # Remove all <a> tags but keep their content
    for a_tag in html_tag.find_all("a"):
        a_tag.unwrap()

    # Convert admonitions created by Zensical
    for div in html_tag.find_all("div", class_=lambda c: c and "admonition" in c):
        class_name = "note"  # Default class name if no p tag is found
        p_tag = div.find("p", class_="admonition-title")
        if p_tag:
            class_name = p_tag.get_text(strip=True).lower()
            # Remove the p tag
            p_tag.decompose()
        div["class"] = [class_name]

    # Remove all classes and some other attributes
    for tag in html_tag.find_all(True):
        for attr in ("class", "data-md-component", "title", "id"):
            # Do not remove admonition titles
            if tag.has_attr(attr):
                if attr == "class" and tag.get("class") in [
                    ["note"],
                    ["info"],
                    ["tip"],
                    ["warning"],
                    ["attention"],
                    ["important"],
                ]:
                    continue
                del tag[attr]

    # Convert admonitions (created by mkdocstrings plugin)
    for details in html_tag.find_all("details"):
        summary = details.find("summary")
        # Get the text from the summary and format it
        summary_text = summary.get_text(strip=True).lower()
        if summary_text:
            # Create a new div with the admonition title
            new_div = soup.new_tag("div", **{"class": summary_text})
            for p in details.find_all("p"):
                new_div.append(p)
            details.replace_with(new_div)
        else:
            details.unwrap()

    # Remove div tags that don't have any attributes and keep their content
    for div in html_tag.find_all("div"):
        if not div.attrs:
            # If the div has no attributes, unwrap it to keep its content
            div.unwrap()
        elif "class" in div.attrs and div["class"] == ["doc"]:
            # If the div has class "doc", unwrap it to keep its content
            div.unwrap()

    content = str(html_tag)

    Path(output_file).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preprocess HTML files to remove headers, footers, styles, and scripts."
    )
    parser.add_argument("input_file", type=str, help="Path to the input HTML file.")
    parser.add_argument("output_file", type=str, help="Path to the output HTML file.")
    parser.add_argument(
        "--hide-docstring", action="store_true", help="Whether to remove the module docstrings."
    )

    args = parser.parse_args()

    preprocess_html(args.input_file, args.output_file, args.hide_docstring)
