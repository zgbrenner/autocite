from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import fitz
import pymupdf4llm

PDF = Path('reference/The_Bluebook_Uncovered_22e.pdf')
OUT = Path('reference/generated')
ASSETS = OUT / 'assets'
CHAPTERS = OUT / 'chapters'

if OUT.exists():
    shutil.rmtree(OUT)
ASSETS.mkdir(parents=True)
CHAPTERS.mkdir(parents=True)

# Preserve the single substantive embedded figure (decorative icons are omitted).
doc = fitz.open(PDF)
figure_xref = 513
img = doc.extract_image(figure_xref)
fig_path = ASSETS / f'figure_8_1.{img["ext"]}'
fig_path.write_bytes(img['image'])

pymupdf4llm.use_layout(False)
chunks = pymupdf4llm.to_markdown(
    str(PDF),
    page_chunks=True,
    ignore_graphics=True,
    ignore_images=True,
    force_text=True,
    margins=(0, 60, 0, 55),
    show_progress=True,
    page_separators=False,
)

sections = [
    ('00_front_matter.md', 'Front Matter', 1, 22),
    ('01_chapter_01_legal_citations.md', 'Chapter 1: Legal Citations', 23, 34),
    ('02_chapter_02_cases_full_citation.md', 'Chapter 2: Cases - Full Citation', 35, 68),
    ('03_chapter_03_cases_short_citation.md', 'Chapter 3: Cases - Short Citation', 69, 82),
    ('04_chapter_04_statutes.md', 'Chapter 4: Statutes', 83, 102),
    ('05_chapter_05_other_primary_authority.md', 'Chapter 5: Other Primary Authority', 103, 114),
    ('06_chapter_06_court_and_litigation_documents.md', 'Chapter 6: Court & Litigation Documents', 115, 128),
    ('07_chapter_07_secondary_authority.md', 'Chapter 7: Secondary Authority', 129, 142),
    ('08_chapter_08_cases_prior_and_subsequent_history.md', 'Chapter 8: Cases - Prior & Subsequent History', 143, 158),
    ('09_chapter_09_cases_parallel_citation.md', 'Chapter 9: Cases - Parallel Citation', 159, 172),
    ('10_chapter_10_parentheticals.md', 'Chapter 10: Parentheticals', 173, 196),
    ('11_chapter_11_nonprint_sources.md', 'Chapter 11: Nonprint Sources', 197, 210),
    ('12_chapter_12_quotations.md', 'Chapter 12: Quotations', 211, 232),
    ('13_chapter_13_string_citations.md', 'Chapter 13: String Citations', 233, 240),
    ('14_chapter_14_introductory_signals.md', 'Chapter 14: Introductory Signals', 241, 254),
    ('15_chapter_15_pinpoint_information.md', 'Chapter 15: Pinpoint Information', 255, 278),
    ('16_chapter_16_capitalization.md', 'Chapter 16: Capitalization', 279, 286),
    ('17_chapter_17_comprehensive_exercise.md', 'Chapter 17: Comprehensive Exercise', 287, 316),
    ('18_appendix_scholarly_writing.md', 'Appendix: Differences in Rules for Scholarly Writing', 317, 324),
    ('19_index.md', 'Index', 325, 331),
]


def clean_page(text: str, page_num: int) -> str:
    text = text.replace('<mark>', '').replace('</mark>', '')
    text = text.replace('%0x28', '%28').replace('%0x29', '%29')
    text = text.replace('\u00ad', '')
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = text.strip()

    chapter_titles = {
        25: 'Chapter 1: Legal Citations',
        37: 'Chapter 2: Cases - Full Citation',
        69: 'Chapter 3: Cases - Short Citation',
        83: 'Chapter 4: Statutes',
        103: 'Chapter 5: Other Primary Authority',
        115: 'Chapter 6: Court & Litigation Documents',
        129: 'Chapter 7: Secondary Authority',
        145: 'Chapter 8: Cases - Prior & Subsequent History',
        159: 'Chapter 9: Cases - Parallel Citation',
        173: 'Chapter 10: Parentheticals',
        197: 'Chapter 11: Nonprint Sources',
        213: 'Chapter 12: Quotations',
        233: 'Chapter 13: String Citations',
        241: 'Chapter 14: Introductory Signals',
        255: 'Chapter 15: Pinpoint Information',
        279: 'Chapter 16: Capitalization',
        289: 'Chapter 17: Comprehensive Exercise',
        317: 'Appendix: Differences in Rules for Scholarly Writing',
        325: 'Index',
    }
    part_titles = {
        23: 'Part I: Introduction',
        35: 'Part II: Basic Citation Information',
        143: 'Part III: Additional Citation Information',
        211: 'Part IV: Other Bluebook Topics',
        287: 'Part V: Bluebook Rules in Context',
    }

    if page_num == 1:
        text = re.sub(
            r'^# \*\*The Bluebook\*\* \*\*Uncovered\*\*\s*\n### \*\*A Practical Guide to\*\* \*\*Mastering Legal Citation\*\*',
            '# The Bluebook Uncovered\n\n## A Practical Guide to Mastering Legal Citation',
            text,
            flags=re.M,
        )

    if page_num in part_titles:
        lines = text.splitlines()
        body_start = 0
        while body_start < len(lines) and (not lines[body_start].strip() or lines[body_start].lstrip().startswith('#')):
            body_start += 1
        text = '# ' + part_titles[page_num]
        if body_start < len(lines):
            text += '\n\n' + '\n'.join(lines[body_start:]).strip()

    if page_num in chapter_titles:
        lines = text.splitlines()
        idx = 0
        removed = 0
        while idx < len(lines) and removed < 2:
            if lines[idx].lstrip().startswith('#'):
                removed += 1
            idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        text = '# ' + chapter_titles[page_num]
        if idx < len(lines):
            text += '\n\n' + '\n'.join(lines[idx:]).strip()

    if page_num == 146:
        fig_md = (
            '![Figure 8.1: Direct vs. Indirect History and Prior vs. Subsequent History]'
            '(../assets/figure_8_1.png)'
        )
        title_pat = r'(\*\*Figure 8\.1:[^\n]+\*\*)'
        if re.search(title_pat, text):
            text = re.sub(title_pat, r'\1\n\n' + fig_md, text, count=1)
        else:
            text = fig_md + '\n\n' + text

    return f'<!-- Source PDF page {page_num} -->\n\n{text}\n'


pages = {}
for chunk in chunks:
    page_num = int(chunk['metadata'].get('page_number', chunk['metadata'].get('page')))
    pages[page_num] = clean_page(chunk['text'], page_num)

source_url = 'https://dionneanthon.com/bbu/Anthon%20Bluebook%20Uncovered%20%2822nd%20Edition%20of%20Bluebook%29%202025.08.06.pdf'
site_url = 'https://dionneanthon.com/bbu/bbu22.html'

readme = f'''# The Bluebook Uncovered - Markdown Conversion

This folder contains a Markdown conversion of:

**Dionne E. Anthon, _The Bluebook Uncovered: A Practical Guide to Mastering Legal Citation_ (Twenty-Second Edition of The Bluebook) (2025).**

## Files

- `The_Bluebook_Uncovered_22e.md` - the complete book in one Markdown file.
- `chapters/` - the same content divided into front matter, chapters, appendix, and index.
- `assets/figure_8_1.png` - the book's substantive diagram.

## Conversion notes

- All selectable textual content was converted without OCR.
- Heading hierarchy, emphasis, underlining, links, footnotes, lists, and monospaced citation examples were retained where the PDF structure allowed.
- PDF page markers are included as HTML comments, such as `<!-- Source PDF page 146 -->`.
- Repeated decorative callout icons were omitted, but the text inside each callout was retained.
- Complex multi-column examples and unusual typography may require minor manual cleanup.

## Source and permitted use

- Author page: {site_url}
- Source PDF: {source_url}

The author states that, except for commercial use, this version may be used in any way. This conversion should therefore be used only for noncommercial purposes unless separate permission is obtained.
'''
(OUT / 'README.md').write_text(readme, encoding='utf-8')

combined_header = f'''---
title: "The Bluebook Uncovered"
subtitle: "A Practical Guide to Mastering Legal Citation"
author: "Dionne E. Anthon"
edition: "Twenty-Second Edition of The Bluebook"
year: 2025
source: "{source_url}"
conversion: "PDF to Markdown; noncommercial use only"
---

> **Conversion note:** This Markdown edition preserves the book's textual content and its substantive diagram. Repeated decorative icons are omitted. Page markers refer to pages in the source PDF.

## Contents

'''
for filename, title, start, end in sections:
    anchor = re.sub(r'[^a-z0-9 -]', '', title.lower()).replace(' ', '-')
    combined_header += f'- [{title}](#{anchor})\n'
combined_header += '\n---\n\n'

combined_parts = [combined_header]
for filename, title, start, end in sections:
    section_text = '\n\n---\n\n'.join(pages[p] for p in range(start, end + 1) if p in pages)
    section_text = section_text.replace('(../assets/figure_8_1.png)', '(assets/figure_8_1.png)')
    if start not in (23, 35, 143, 211, 287, 25, 37, 69, 83, 103, 115, 129, 145, 159, 173, 197, 213, 233, 241, 255, 279, 289, 317, 325):
        section_text = f'# {title}\n\n' + section_text
    combined_parts.append(section_text)

combined = '\n\n---\n\n'.join(combined_parts).strip() + '\n'
(OUT / 'The_Bluebook_Uncovered_22e.md').write_text(combined, encoding='utf-8')

for filename, title, start, end in sections:
    content = '\n\n---\n\n'.join(pages[p] for p in range(start, end + 1) if p in pages)
    chapter_header = (
        f'<!-- Converted from source PDF pages {start}-{end}. -->\n\n'
        f'> Source: [{title}]({source_url}) - noncommercial use only.\n\n'
    )
    if not content.lstrip().startswith('#'):
        chapter_header += f'# {title}\n\n'
    (CHAPTERS / filename).write_text(chapter_header + content.strip() + '\n', encoding='utf-8')

assert len(pages) == 331, f'Expected 331 pages, got {len(pages)}'
assert 'Chapter 17: Comprehensive Exercise' in combined
assert 'Figure 8.1' in combined
assert fig_path.exists() and fig_path.stat().st_size > 1000

zip_path = Path('reference/generated.zip')
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(OUT.rglob('*')):
        if path.is_file():
            zf.write(path, Path(OUT.name) / path.relative_to(OUT))

print(f'Wrote: {OUT}')
print(f'Combined chars: {len(combined):,}')
print(f'Chapter files: {len(list(CHAPTERS.glob("*.md")))}')
print(f'ZIP: {zip_path} ({zip_path.stat().st_size:,} bytes)')
