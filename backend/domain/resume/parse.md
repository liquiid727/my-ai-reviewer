# Resume Parser

## Scope

The parser layer converts uploaded resume files into the common
`ParsedResumeText` structure consumed by extraction and classification.
Supported extensions are:

- `.pdf`
- `.doc`
- `.docx`
- `.html` / `.htm`
- `.md`
- `.txt`

The implementation lives under `backend/infrastructure/parsers/` and is
routed by `backend/infrastructure/parsers/__init__.py`.

## Common Output

`ParsedResumeText` contains:

- `raw_text`: the normalized text used by downstream LLM extraction;
- `page_count`: the page count when the source format provides it;
- `blocks`: structured paragraph, heading, or generic blocks. PDF blocks also
  carry their source page number.

`ResumeParser` is the abstract interface. Each parser exposes a version string
so the processing pipeline can record which parser produced the result.

## Format Implementations

| Format | Implementation | Behavior |
| --- | --- | --- |
| PDF | `PdfResumeParser` + PyMuPDF | Extracts text page by page and assigns page numbers to blocks. |
| DOCX | `DocxResumeParser` + `python-docx` | Extracts paragraphs and table rows; uses Word heading styles when available. |
| DOC | `DocResumeParser` | Uses LibreOffice `soffice` conversion when available, then falls back to readable text recovery from the binary stream. |
| HTML | `HtmlResumeParser` + stdlib `html.parser` | Removes script, style, head, and metadata content while preserving visible text and headings. |
| Markdown | `MarkdownResumeParser` | Preserves source text, normalizes line endings, and maps Markdown headings to blocks. |
| TXT | `TextResumeParser` | Reads plain text through the shared encoding fallback described below. |

The project intentionally uses the standard library for HTML and Markdown
handling. This avoids introducing parser dependencies that are not needed for
the current extraction contract.

## TXT / Markdown Encoding Fallback

`TextResumeParser` and `MarkdownResumeParser` both call
`read_text_with_fallback` from `backend/infrastructure/parsers/base.py`:

1. Read as `utf-8-sig`, which handles ordinary UTF-8 and strips a UTF-8 BOM.
2. If UTF-8 decoding fails, use `charset-normalizer.from_path` and retry with
   the best detected encoding. This covers common GBK, GB18030, and Big5 files
   when the content provides enough signal.
3. If detection is unavailable or the detected encoding cannot decode the file,
   read as UTF-8 with `errors="replace"` and emit a warning. The parser keeps
   the document processable instead of failing the whole resume pipeline.

`charset-normalizer` is a required backend dependency because this behavior is
part of the default TXT / Markdown parser contract, not an optional feature.

## Factory and Upload Integration

`get_parser` normalizes the extension to lowercase and returns the parser
registered in `_PARSER_MAP`. Unknown extensions raise `ValueError` before
processing starts. The resume upload API uses the same supported-extension set,
so parser routing and upload validation stay aligned.

## Versioning and Limitations

Parser versions are part of the stored resume processing metadata. Re-parsing
can snapshot the previous result before running the current parser version.

- HTML and non-PDF office formats do not expose reliable page numbers.
- DOC best-effort recovery preserves readable text but not original layout.
- Automatic legacy-encoding detection is heuristic; replacement decoding is
  the final availability fallback and should be surfaced through the warning
  log for operational diagnosis.
