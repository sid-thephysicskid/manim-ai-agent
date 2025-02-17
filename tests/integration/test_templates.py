import pytest
from pathlib import Path
from app.templates import get_example_template, get_api_doc, TEMPLATES_DIR
from app.core.config import BASE_DIR
import importlib.util

@pytest.mark.integration
class TestTemplates:
    def test_directory_structure(self):
        """Test that template directories are created correctly."""
        assert (TEMPLATES_DIR / "examples").exists()
        assert (TEMPLATES_DIR / "api_docs").exists()
        
        # Test relative to project root
        templates_dir = BASE_DIR / "app" / "templates"
        examples_dir = templates_dir / "examples"
        api_docs_dir = templates_dir / "api_docs"
        
        assert (examples_dir / "gcf.py").exists()
        assert (api_docs_dir / "manim_mobjects.py").exists()

    def test_gcf_template(self):
        """Test GCF template content and structure."""
        template = get_example_template("gcf")
        
        # Check base class and structure
        assert "ManimVoiceoverBase" in template
        assert "GCFCalculationScene(ManimVoiceoverBase)" in template
        
        # Check required methods
        assert "def construct(self):" in template
        assert "def intro_scene(self):" in template
        assert "def listing_factors_scene(self):" in template
        assert "def summary_scene(self):" in template
        
        # Check helper methods
        assert "create_title" in template
        assert "ensure_group_visible" in template
        assert "create_factor_mob" in template
        
        # Check cleanup
        assert "*[FadeOut(mob)for mob in self.mobjects if mob != self.background]" in template

    def test_api_docs(self):
        """Test API documentation content."""
        api_doc = get_api_doc("manim_mobjects")
        
        # Check key components
        assert "Mobjects that are simple geometric shapes" in api_doc
        assert "class Polygram(VMobject, metaclass=ConvertToOpenGL):" in api_doc
        assert "class Rectangle(Polygon):" in api_doc
        assert "__all__ = [" in api_doc
        assert "\"Polygon\"," in api_doc

    def test_template_imports(self):
        """Test that template files can be imported without errors."""
        gcf_path = BASE_DIR / "app" / "templates" / "examples" / "gcf.py"
        spec = importlib.util.spec_from_file_location("gcf", gcf_path)
        gcf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gcf_module)
        
        assert hasattr(gcf_module, "GCFCalculationScene")

    def test_error_handling(self):
        """Test error handling for invalid templates."""
        with pytest.raises(ValueError, match="Template nonexistent.py not found"):
            get_example_template("nonexistent")
            
        with pytest.raises(ValueError, match="API doc nonexistent.py not found"):
            get_api_doc("nonexistent") 