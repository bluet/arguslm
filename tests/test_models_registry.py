"""Tests for models registry loading and validation."""

import json
from pathlib import Path


def test_models_registry_exists():
    """Test that models registry file exists."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    assert registry_path.exists(), f"Registry file not found at {registry_path}"


def test_models_registry_valid_json():
    """Test that models registry is valid JSON."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)
    assert isinstance(data, dict), "Registry root must be a dict"


def test_models_registry_structure():
    """Test that models registry has required structure."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    assert "models" in data, "Registry must have 'models' key"
    assert "metadata" in data, "Registry must have 'metadata' key"
    assert isinstance(data["models"], list), "'models' must be a list"
    assert len(data["models"]) > 0, "'models' list must not be empty"


def test_models_registry_model_fields():
    """Test that each model has required fields."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    required_fields = {"id", "provider", "name", "context_window", "pricing", "status"}

    for model in data["models"]:
        assert isinstance(model, dict), "Each model must be a dict"
        for field in required_fields:
            assert field in model, f"Model {model.get('id', 'unknown')} missing field: {field}"

        # Validate pricing structure
        assert isinstance(model["pricing"], dict), f"Model {model['id']} pricing must be a dict"
        assert "input_per_mtok" in model["pricing"], f"Model {model['id']} missing input_per_mtok"
        assert "output_per_mtok" in model["pricing"], f"Model {model['id']} missing output_per_mtok"


def test_models_registry_anthropic_models():
    """Test that Anthropic models are present."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    anthropic_models = [m for m in data["models"] if m["provider"] == "anthropic"]
    assert len(anthropic_models) >= 3, "Should have at least 3 Anthropic models"

    model_ids = {m["id"] for m in anthropic_models}
    assert "claude-3-5-sonnet-20241022" in model_ids, "Missing Claude 3.5 Sonnet"
    assert "claude-3-5-haiku-20241022" in model_ids, "Missing Claude 3.5 Haiku"
    assert "claude-3-opus-20250219" in model_ids, "Missing Claude 3 Opus"


def test_models_registry_mistral_models():
    """Test that Mistral models are present."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    mistral_models = [m for m in data["models"] if m["provider"] == "mistral"]
    assert len(mistral_models) >= 2, "Should have at least 2 Mistral models"

    model_ids = {m["id"] for m in mistral_models}
    assert "mistral-large-2407" in model_ids, "Missing Mistral Large"
    assert "mistral-small-2503" in model_ids, "Missing Mistral Small"


def test_models_registry_cohere_models():
    """Test that Cohere models are present."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    cohere_models = [m for m in data["models"] if m["provider"] == "cohere"]
    assert len(cohere_models) >= 2, "Should have at least 2 Cohere models"

    model_ids = {m["id"] for m in cohere_models}
    assert "command-r-plus-08-2024" in model_ids, "Missing Command R+"
    assert "command-r-08-2024" in model_ids, "Missing Command R"


def test_models_registry_pricing_valid():
    """Test that all pricing values are non-negative numbers."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    for model in data["models"]:
        pricing = model["pricing"]
        assert isinstance(pricing["input_per_mtok"], (int, float)), (
            f"Model {model['id']} input_per_mtok must be a number"
        )
        assert isinstance(pricing["output_per_mtok"], (int, float)), (
            f"Model {model['id']} output_per_mtok must be a number"
        )
        assert pricing["input_per_mtok"] >= 0, (
            f"Model {model['id']} input_per_mtok must be non-negative"
        )
        assert pricing["output_per_mtok"] >= 0, (
            f"Model {model['id']} output_per_mtok must be non-negative"
        )


def test_models_registry_context_window_valid():
    """Test that context windows are positive integers."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    for model in data["models"]:
        assert isinstance(model["context_window"], int), (
            f"Model {model['id']} context_window must be an integer"
        )
        assert model["context_window"] > 0, f"Model {model['id']} context_window must be positive"


def test_models_registry_no_duplicates():
    """Test that there are no duplicate model IDs."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    model_ids = [m["id"] for m in data["models"]]
    assert len(model_ids) == len(set(model_ids)), "Duplicate model IDs found"


def test_models_registry_metadata():
    """Test that metadata is present and valid."""
    registry_path = Path(__file__).parent.parent / "data" / "models_registry.json"
    with open(registry_path) as f:
        data = json.load(f)

    metadata = data["metadata"]
    assert "version" in metadata, "Metadata missing version"
    assert "last_updated" in metadata, "Metadata missing last_updated"
    assert "sources" in metadata, "Metadata missing sources"
    assert isinstance(metadata["sources"], dict), "Sources must be a dict"
