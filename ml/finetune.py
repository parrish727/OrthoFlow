"""
OrthoFlow AI — Custom LLM Fine-Tuning Pipeline

Trains a local model (Mistral/Llama) on orthodontic vendor catalog data
so it can classify invoice line items with high accuracy without cloud APIs.

Usage:
    python -m ml.finetune --data ml/training_data/ortho_catalog.json --model mistral

Requirements:
    - Ollama running with base model pulled
    - Training data in JSON format (input/output pairs)

Pipeline:
    1. Load training data (ortho_catalog.json + practice-specific corrections)
    2. Format as instruction-tuning pairs
    3. Create Modelfile with system prompt + training examples
    4. Push to Ollama as custom model
"""
import json
import argparse
import httpx


SYSTEM_PROMPT = """You are an orthodontic accounts payable specialist. Given a line item description from a vendor invoice, classify it into the correct expense category.

Categories: supplies, lab, equipment, services, insurance, software, rent, utilities, other

Subcategories for supplies: brackets, archwires, elastics, bonding, sterilization, prophylaxis, ppe, disposables, imaging, impressions, restorative, bands
Subcategories for lab: retainer, retainer_material, aligners, rush_fee
Subcategories for equipment: imaging, furniture, instruments
Subcategories for insurance: clearinghouse, credentialing
Subcategories for services: it, janitorial, consulting

Respond with JSON only: {"category": "...", "subcategory": "...", "vendor_type": "..."}"""


def load_training_data(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def format_modelfile(base_model: str, training_data: list[dict]) -> str:
    """Create an Ollama Modelfile with embedded training examples."""
    examples = ""
    for item in training_data:
        examples += f'\nMESSAGE user {item["input"]}\nMESSAGE assistant {json.dumps(item["output"])}'

    modelfile = f"""FROM {base_model}

SYSTEM {SYSTEM_PROMPT}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
{examples}
"""
    return modelfile


def create_model(ollama_url: str, model_name: str, modelfile: str):
    """Push the fine-tuned model to Ollama."""
    resp = httpx.post(
        f"{ollama_url}/api/create",
        json={"name": model_name, "modelfile": modelfile},
        timeout=300,
    )
    resp.raise_for_status()
    print(f"✅ Model '{model_name}' created successfully")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune OrthoFlow classification model")
    parser.add_argument("--data", default="ml/training_data/ortho_catalog.json")
    parser.add_argument("--model", default="mistral", help="Base model to fine-tune from")
    parser.add_argument("--name", default="orthoflow-classify", help="Name for the fine-tuned model")
    parser.add_argument("--ollama-url", default="http://localhost:11435")
    args = parser.parse_args()

    print(f"Loading training data from {args.data}...")
    data = load_training_data(args.data)
    print(f"  {len(data)} training examples loaded")

    print(f"Creating Modelfile from {args.model}...")
    modelfile = format_modelfile(args.model, data)

    print(f"Pushing model '{args.name}' to Ollama...")
    create_model(args.ollama_url, args.name, modelfile)

    print(f"\nDone! Use the model with:")
    print(f"  OLLAMA_MODEL={args.name}")


if __name__ == "__main__":
    main()
