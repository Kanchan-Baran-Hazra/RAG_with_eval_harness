from docling.document_converter import DocumentConverter

# 1. Initialize the converter
converter = DocumentConverter()

# 2. Convert a local file or URL
# source = r"docs\02_Remote_and_Hybrid_Work_Policy.pdf"  # Also supports .docx, .pptx, .html, .png, .jpg, or URLs
sources=[
    r"docs\01_Code_of_Conduct_and_Ethics.pdf",
    r"docs\02_Remote_and_Hybrid_Work_Policy.pdf",
    r"docs\03_Annual_and_Sick_Leave_Policy.pdf",
    r"docs\04_Parental_and_Family_Leave_Policy.pdf",
    r"docs\05_Information_Security_and_Access_Control.pdf",
    r"docs\06_Generative_AI_and_LLM_Usage_Policy.pdf",
]

for i in range(len(sources)):
    source = sources[i]
    result = converter.convert(source)

    # 3. Export extracted content to Markdown (preserves headings, lists, and tables)
    markdown_text = result.document.export_to_markdown()
    print(markdown_text)
    print("============================================================\n")


# print("=================================\n")
# doc = result.document  # Access the Document object for further processing

# print("Document Metadata:")
# print(f"Pages: {doc.pages}")
# print(f"Text: {doc.texts}")
# print(f"Tables: {doc.tables}")
# print(f"Pictures: {doc.pictures}")
# print(f"Body: {doc.body}")
# print(f"Status: {result.status}")

# Optional: Export to plain text or structured dictionary/JSON
# plain_text = result.document.export_to_text()
# json_data = result.document.export_to_dict()