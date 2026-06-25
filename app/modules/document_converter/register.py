"""Document Converter module registration helper — FunctionGroupContracts.

The document converter module converts markdown to DOCX, HTML, or both.
Used by the document hub to export tenant documents.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_to_docx",
    title="Document Converter To DOCX (SSOT)",
    description="CANONICAL convert markdown text to Microsoft Word (.docx) format. Returns the converted file.",
    inputs=("markdown", "filename?"),
    outputs=("docx", "filename"),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_to_html",
    title="Document Converter To HTML (SSOT)",
    description="CANONICAL convert markdown text to interactive HTML. Returns the converted HTML.",
    inputs=("markdown", "filename?"),
    outputs=("html", "filename"),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_to_both",
    title="Document Converter To Both (SSOT)",
    description="CANONICAL convert markdown text to both DOCX and HTML. Returns both converted files.",
    inputs=("markdown", "filename?"),
    outputs=("docx", "html", "filename"),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_file",
    title="Document Converter File (SSOT)",
    description="CANONICAL convert an uploaded markdown file to DOCX/HTML. Returns the converted file(s).",
    inputs=("file", "output_format?"),
    outputs=("converted", "filename"),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_from_path",
    title="Document Converter From Path (SSOT)",
    description="CANONICAL convert a markdown file from a server path. Returns the converted file(s).",
    inputs=("file_path", "output_format?"),
    outputs=("converted", "filename"),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_download",
    title="Document Converter Download (SSOT)",
    description="CANONICAL download a converted document by filename. Returns the file for download.",
    inputs=("filename",),
    outputs=("file",),
    dependencies=("app.modules.document_converter.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_list",
    title="Document Converter List (SSOT)",
    description="CANONICAL list all converted documents. Returns filenames and metadata.",
    inputs=(),
    outputs=("documents",),
    dependencies=("app.modules.document_converter.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="document_converter",
    group_name="document_converter_cleanup",
    title="Document Converter Cleanup (SSOT)",
    description="CANONICAL clean up converted documents older than specified days. Admin-only.",
    inputs=("days_old?"),
    outputs=("cleaned",),
    dependencies=("app.modules.document_converter.router",),
    deterministic=False,
))
