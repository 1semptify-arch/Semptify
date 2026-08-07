"""PDF Tools module registration helper — FunctionGroupContracts.

The PDF tools module provides PDF manipulation: upload, info, page
extraction, text extraction, split, merge, rotate, and thumbnails.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_test",
        title="PDF Tools Test (SSOT)",
        description="CANONICAL test endpoint. Returns pymupdf version to verify PDF tools are available.",
        inputs=(),
        outputs=("status", "pymupdf_version"),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_upload",
        title="PDF Tools Upload (SSOT)",
        description="CANONICAL upload a PDF for processing. Returns a pdf_id for use with other endpoints.",
        inputs=("file",),
        outputs=("pdf_id", "filename", "page_count"),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_info",
        title="PDF Tools Info (SSOT)",
        description="CANONICAL get info about an uploaded PDF. Returns page count, metadata, and file size.",
        inputs=("pdf_id",),
        outputs=("info",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_page_image",
        title="PDF Tools Page Image (SSOT)",
        description="CANONICAL get a page as a PNG image. Returns the rendered page at the specified zoom level.",
        inputs=("pdf_id", "page_num", "zoom?"),
        outputs=("image",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_page_base64",
        title="PDF Tools Page Base64 (SSOT)",
        description="CANONICAL get a page as base64-encoded PNG. Returns the rendered page for web display.",
        inputs=("pdf_id", "page_num", "zoom?"),
        outputs=("base64",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_page_text",
        title="PDF Tools Page Text (SSOT)",
        description="CANONICAL extract text from a specific page. Returns the text content of the page.",
        inputs=("pdf_id", "page_num"),
        outputs=("text",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_all_text",
        title="PDF Tools All Text (SSOT)",
        description="CANONICAL extract text from all pages. Returns the full text content of the PDF.",
        inputs=("pdf_id",),
        outputs=("text",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_extract_pages",
        title="PDF Tools Extract Pages (SSOT)",
        description="CANONICAL extract specific pages as a new PDF. Returns the extracted pages as a PDF file.",
        inputs=("pdf_id", "pages"),
        outputs=("pdf",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_extract_pages_base64",
        title="PDF Tools Extract Pages Base64 (SSOT)",
        description="CANONICAL extract specific pages as base64-encoded PDF. Returns the extracted pages for web display.",
        inputs=("pdf_id", "pages"),
        outputs=("base64",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_delete",
        title="PDF Tools Delete (SSOT)",
        description="CANONICAL delete an uploaded PDF from cache. Removes the PDF and all associated data.",
        inputs=("pdf_id",),
        outputs=("success",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_thumbnails",
        title="PDF Tools Thumbnails (SSOT)",
        description="CANONICAL get thumbnails of all pages. Returns thumbnail images for quick navigation.",
        inputs=("pdf_id", "max_width?"),
        outputs=("thumbnails",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_split",
        title="PDF Tools Split (SSOT)",
        description="CANONICAL split a PDF into multiple files. Returns split PDFs with the specified pages per file.",
        inputs=("pdf_id", "pages_per_file?"),
        outputs=("split_pdfs",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_merge",
        title="PDF Tools Merge (SSOT)",
        description="CANONICAL merge multiple PDFs into one. Returns the merged PDF file.",
        inputs=("files",),
        outputs=("merged_pdf",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="pdf_tools",
        group_name="pdf_tools_rotate",
        title="PDF Tools Rotate Pages (SSOT)",
        description="CANONICAL rotate specific pages in a PDF. Returns the modified PDF with rotated pages.",
        inputs=("pdf_id", "pages", "rotation"),
        outputs=("pdf",),
        dependencies=("app.modules.pdf_tools.router",),
        deterministic=False,
    )
)
