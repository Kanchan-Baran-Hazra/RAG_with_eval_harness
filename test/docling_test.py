from docling.document_converter import DocumentConverter

# 1. Initialize the converter
converter = DocumentConverter()

# 2. Convert a local file or URL
source = r"docs\sample_document.pdf"  # Also supports .docx, .pptx, .html, .png, .jpg, or URLs
result = converter.convert(source)

# 3. Export extracted content to Markdown (preserves headings, lists, and tables)
markdown_text = result.document.export_to_markdown()
print(markdown_text)

# Optional: Export to plain text or structured dictionary/JSON
plain_text = result.document.export_to_text()
json_data = result.document.export_to_dict()