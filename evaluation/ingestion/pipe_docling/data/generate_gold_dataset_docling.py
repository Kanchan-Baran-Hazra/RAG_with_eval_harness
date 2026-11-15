# This is only for the research purpose in the real situation the .md file create by the domain expart this is only like a synthetic data

from pathlib import Path
from docling.document_converter import DocumentConverter

# 1. Point to your folder
docs_dir = Path(r"raw_docs")
output_dir = Path("ground_truth")
output_dir.mkdir(parents=True, exist_ok=True)

# 2. Automatically find all PDF files in the folder
sources = list(docs_dir.glob("*.pdf"))

if not sources:
    print(f"No PDF files found in {docs_dir.absolute()}")
else:
    print(f"Found {len(sources)} files. Starting conversion...")
    
    # Optional: converter.convert_all() is faster for batch processing
    converter = DocumentConverter()

    for source_path in sources:
        print(f"Processing: {source_path.name}...")
        try:
            result = converter.convert(source_path)
            markdown_text = result.document.export_to_markdown()

            # Save with the exact same file name but with .md extension
            output_file = output_dir / f"{source_path.stem}.md"
            output_file.write_text(markdown_text, encoding="utf-8")
            print(f" -> Saved to {output_file}")
            
        except Exception as e:
            print(f" -> Failed to process {source_path.name}: {e}")

    print("\nBatch conversion complete!")





































# from pathlib import Path
# from docling.document_converter import DocumentConverter

# converter = DocumentConverter()

# sources = [
#     r"docs\01_Code_of_Conduct_and_Ethics.pdf",
#     r"docs\02_Remote_and_Hybrid_Work_Policy.pdf",
#     r"docs\03_Annual_and_Sick_Leave_Policy.pdf",
#     r"docs\04_Parental_and_Family_Leave_Policy.pdf",
#     r"docs\05_Information_Security_and_Access_Control.pdf",
#     r"docs\06_Generative_AI_and_LLM_Usage_Policy.pdf",
# ]

# # Create output directory if it doesn't exist
# output_dir = Path("extracted_md")
# output_dir.mkdir(parents=True, exist_ok=True)

# for source in sources:
#     source_path = Path(source)
#     result = converter.convert(source_path)

#     # Export extracted content to Markdown
#     markdown_text = result.document.export_to_markdown()

#     # Save using the original filename stem (e.g., 01_Code_of_Conduct_and_Ethics.md)
#     output_file = output_dir / f"{source_path.stem}.md"
#     output_file.write_text(markdown_text, encoding="utf-8")

#     print(f"Saved: {output_file}")