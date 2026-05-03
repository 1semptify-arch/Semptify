#!/usr/bin/env python3
"""
Page Recipe Renderer
===================
Render a PageRecipe as an interactive HTML visualization.

Usage:
    python scripts/render_page_recipe.py <page_id>
    python scripts/render_page_recipe.py --all
    python scripts/render_page_recipe.py --incomplete

Examples:
    python scripts/render_page_recipe.py document_intake
    python scripts/render_page_recipe.py --all --output-dir ./recipes
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.page_recipe import RecipeRegistry, create_document_intake_recipe


def render_recipe_to_html(page_id: str, output_path: Optional[Path] = None) -> str:
    """
    Render a page recipe to HTML visualization.
    
    Args:
        page_id: The recipe ID to render
        output_path: Where to save the HTML file (optional)
    
    Returns:
        HTML string
    """
    recipe = RecipeRegistry.get(page_id)
    if not recipe:
        raise ValueError(f"Recipe not found: {page_id}")
    
    # Convert recipe to dict
    recipe_dict = recipe.to_dict()
    
    # Read template
    template_path = Path(__file__).parent.parent / "app" / "templates" / "page_recipe_template.html"
    template = template_path.read_text(encoding="utf-8")
    
    # Simple template rendering (replace Jinja2 variables)
    # In production, you'd use Jinja2, but this avoids dependency issues
    html = template
    
    # Replace simple variables
    html = html.replace("{{ recipe.page_id }}", recipe_dict["page_id"])
    html = html.replace("{{ recipe.page_title }}", recipe_dict.get("page_title", recipe_dict["page_id"]))
    html = html.replace("{{ recipe.intent }}", recipe_dict["intent"])
    html = html.replace("{{ recipe.purpose }}", recipe_dict["purpose"])
    html = html.replace("{{ recipe.user_intent }}", recipe_dict["user_intent"])
    
    # Replace validation
    validation = recipe_dict["validation"]
    html = html.replace("{{ recipe.validation.complete }}", str(validation["complete"]).lower())
    html = html.replace("{{ recipe.validation.implemented_count }}", str(validation["implemented_count"]))
    html = html.replace("{{ recipe.validation.total_components }}", str(validation["total_components"]))
    
    # Replace steps count
    html = html.replace("{{ recipe.steps|length }}", str(len(recipe_dict["steps"])))
    html = html.replace("{{ recipe.error_handling.error_states|length }}", str(len(recipe_dict["error_handling"]["error_states"])))
    
    # Render components list
    components_html = ""
    for comp in recipe_dict["components"]:
        status_class = "implemented" if comp["implemented"] else "missing"
        req_class = "required" if comp["required"] else "optional"
        depends = f"Depends: {', '.join(comp['depends_on'])}" if comp['depends_on'] else ""
        path = f'<div class="component-path">{comp["file_path"]}</div>' if comp["file_path"] else ""
        
        components_html += f'''
        <div class="component-item {req_class} {status_class}">
            <div class="component-status {status_class}">{'Done' if comp["implemented"] else 'Needed'}</div>
            <div class="component-info">
                <div class="component-name">{comp["name"]}</div>
                <div class="component-type">{comp["type"]}</div>
                <div class="component-desc">{comp["description"]}</div>
                {path}
                {f'<div class="component-path">{depends}</div>' if depends else ""}
            </div>
        </div>
        '''
    
    # Replace components loop
    html = html.replace(
        "{% for component in recipe.components %}",
        "<!-- COMPONENTS START -->"
    ).replace(
        "{% endfor %}",
        "<!-- COMPONENTS END -->"
    )
    # Simple replacement for now - in production use proper Jinja2
    start_idx = html.find("<!-- COMPONENTS START -->")
    end_idx = html.find("<!-- COMPONENTS END -->")
    if start_idx != -1 and end_idx != -1:
        html = html[:start_idx + len("<!-- COMPONENTS START -->")] + components_html + html[end_idx:]
    
    # Save if output path provided
    if output_path:
        output_path.write_text(html, encoding="utf-8")
        print(f"✅ Recipe rendered: {output_path}")
    
    return html


def main():
    parser = argparse.ArgumentParser(description="Render page recipes to HTML")
    parser.add_argument("page_id", nargs="?", help="Page ID to render")
    parser.add_argument("--all", action="store_true", help="Render all recipes")
    parser.add_argument("--incomplete", action="store_true", help="Render only incomplete recipes")
    parser.add_argument("--output-dir", default="./recipe_visualizations", help="Output directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of HTML")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine which recipes to render
    if args.all:
        recipes = RecipeRegistry.all_recipes()
    elif args.incomplete:
        recipes = {k: v for k, v in RecipeRegistry.all_recipes().items() if not v.validate()["complete"]}
    elif args.page_id:
        recipes = {args.page_id: RecipeRegistry.get(args.page_id)} if RecipeRegistry.get(args.page_id) else {}
    else:
        # Default: show available recipes
        print("\n📋 Available Recipes:")
        for page_id, recipe in RecipeRegistry.all_recipes().items():
            status = "✅" if recipe.validate()["complete"] else "🚧"
            print(f"  {status} {page_id}: {recipe.page_title}")
        print("\nUsage: python render_page_recipe.py <page_id>")
        return
    
    if not recipes:
        print("❌ No recipes found")
        return
    
    # Render each recipe
    for page_id, recipe in recipes.items():
        if args.json:
            output_path = output_dir / f"{page_id}_recipe.json"
            output_path.write_text(
                json.dumps(recipe.to_dict(), indent=2),
                encoding="utf-8"
            )
            print(f"✅ JSON exported: {output_path}")
        else:
            output_path = output_dir / f"{page_id}_recipe.html"
            try:
                render_recipe_to_html(page_id, output_path)
            except Exception as e:
                print(f"❌ Error rendering {page_id}: {e}")
    
    print(f"\n📁 Output: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
