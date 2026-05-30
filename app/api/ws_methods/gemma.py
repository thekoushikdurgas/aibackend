"""
Gemma WebSocket method handlers
"""

import sys
import asyncio
import logging
import random
from typing import Any, AsyncGenerator, Dict, Optional, Union
from pathlib import Path

from app.config import settings
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.llm import LLMConfig, LLMProviderFactory

logger = logging.getLogger(__name__)

# Standard Gemma models for references
GEMMA_MODELS = [
    {
        "id": "google/gemma-3-270m-it",
        "name": "Gemma 3 270M Instruct",
        "parameters": "270M",
        "type": "Text / Multimodal",
        "context": 8192,
        "description": "Ultra-lightweight model designed for mobile and on-device tasks.",
        "hardware": "CPU (8GB RAM) or mobile chipsets",
    },
    {
        "id": "google/gemma-3-4b-it",
        "name": "Gemma 3 4B Instruct",
        "parameters": "4B",
        "type": "Text / Multimodal",
        "context": 32768,
        "description": "Versatile medium model balancing speed and reasoning.",
        "hardware": "Low-end GPU or CPU (16GB RAM)",
    },
    {
        "id": "google/gemma-3-12b-it",
        "name": "Gemma 3 12B Instruct",
        "parameters": "12B",
        "type": "Text / Multimodal",
        "context": 65536,
        "description": "High-performance model for advanced reasoning and coding.",
        "hardware": "Mid-range GPU (16GB+ VRAM)",
    },
    {
        "id": "google/gemma-4-e4b-it",
        "name": "Gemma 4 E4B Instruct",
        "parameters": "4B (MoE)",
        "type": "Multimodal / JAX Native",
        "context": 131072,
        "description": "Next-generation Mixture of Experts (MoE) JAX model with extended context.",
        "hardware": "High-end GPU (24GB VRAM) or TPU",
    },
]

# Standard checkpoints mapping from gemma-main _paths.py
GEMMA_CHECKPOINTS = [
    {
        "id": "GEMMA2_2B_IT",
        "path": "gs://gemma-data/checkpoints/gemma2-2b-it",
        "version": "Gemma 2",
        "size": "2B",
        "type": "Instruct",
    },
    {
        "id": "GEMMA3_270M_IT",
        "path": "gs://gemma-data/checkpoints/gemma3-270m-it",
        "version": "Gemma 3",
        "size": "270M",
        "type": "Instruct",
    },
    {
        "id": "GEMMA3_4B_IT",
        "path": "gs://gemma-data/checkpoints/gemma3-4b-it",
        "version": "Gemma 3",
        "size": "4B",
        "type": "Instruct",
    },
    {
        "id": "GEMMA3_12B_IT",
        "path": "gs://gemma-data/checkpoints/gemma3-12b-it",
        "version": "Gemma 3",
        "size": "12B",
        "type": "Instruct",
    },
    {
        "id": "GEMMA4_E2B_IT",
        "path": "gs://gemma-data/checkpoints/gemma4-e2b-it",
        "version": "Gemma 4",
        "size": "E2B",
        "type": "Instruct",
    },
    {
        "id": "GEMMA4_E4B_IT",
        "path": "gs://gemma-data/checkpoints/gemma4-e4b-it",
        "version": "Gemma 4",
        "size": "E4B",
        "type": "Instruct",
    },
]


async def handle_gemma_chat_completions(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """Handle gemma.chat.completions method"""
    message = params.get("message", "")
    model = str(params.get("model") or settings.gemma_model)
    stream = params.get("stream", False)
    temperature = float(params.get("temperature", 0.7))
    mode = str(params.get("mode") or settings.gemma_mode or "simulated").lower()

    if not message:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: message"
        )

    # If local JAX mode is requested, check if JAX is available
    if mode == "local":
        try:
            # Add gemma-main path to sys.path to enable imports
            gemma_path = Path("e:/durgas_ai/docs/docs/ideas/gemma-main")
            if gemma_path.exists() and str(gemma_path) not in sys.path:
                sys.path.append(str(gemma_path))

            import importlib.util

            if (
                importlib.util.find_spec("jax") is None
                or importlib.util.find_spec("gemma") is None
            ):
                raise ImportError("jax or gemma not installed")

            logger.info("JAX and gemma-main package loaded successfully")
        except ImportError:
            # Graceful fallback with log note
            logger.warning(
                "JAX or gemma package not found, falling back to simulated mode"
            )
            mode = "simulated"

    if mode == "ollama":
        try:
            ollama_prov = LLMProviderFactory.get_provider("ollama")
            config = LLMConfig(model=model or "gemma2", temperature=temperature)
            if stream:
                return _stream_ollama(ollama_prov, message, config)
            resp = await ollama_prov.generate(message, config)
            return {
                "message": resp.text,
                "provider": "gemma-ollama",
                "model": resp.model,
                "usage": resp.usage,
            }
        except Exception as e:
            logger.warning(f"Ollama gemma chat failed: {e}. Falling back to simulated.")
            mode = "simulated"

    if mode == "api":
        try:
            # Use deepinfra or huggingface providers if they are configured
            api_provider = "deepinfra"
            prov = LLMProviderFactory.get_provider(api_provider)
            config = LLMConfig(
                model=model or "google/gemma-7b-it", temperature=temperature
            )
            if stream:
                return _stream_api(prov, message, config)
            resp = await prov.generate(message, config)
            return {
                "message": resp.text,
                "provider": f"gemma-{api_provider}",
                "model": resp.model,
                "usage": resp.usage,
            }
        except Exception as e:
            logger.warning(f"API gemma chat failed: {e}. Falling back to simulated.")
            mode = "simulated"

    # Simulated mode
    if stream:
        return _stream_simulated_gemma_chat(message, model, temperature)

    answer = _generate_simulated_gemma_response(message, model, temperature)
    return {
        "message": answer,
        "provider": "gemma-simulated",
        "model": model,
        "usage": {
            "prompt_tokens": len(message) // 4,
            "completion_tokens": len(answer) // 4,
            "total_tokens": (len(message) + len(answer)) // 4,
        },
    }


async def _stream_ollama(
    provider: Any, message: str, config: LLMConfig
) -> AsyncGenerator[Dict[str, Any], None]:
    yield {"type": "start", "provider": "gemma-ollama", "model": config.model}
    async for chunk in provider.stream(message, config=config):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def _stream_api(
    provider: Any, message: str, config: LLMConfig
) -> AsyncGenerator[Dict[str, Any], None]:
    yield {"type": "start", "provider": "gemma-api", "model": config.model}
    async for chunk in provider.stream(message, config=config):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def _stream_simulated_gemma_chat(
    message: str, model: str, temperature: float
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream simulated Gemma responses token-by-token"""
    yield {"type": "start", "provider": "gemma-simulated", "model": model}

    answer = _generate_simulated_gemma_response(message, model, temperature)

    # Split text into chunks to simulate stream
    words = answer.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        # Add a realistic small delay
        await asyncio.sleep(random.uniform(0.01, 0.04))
        yield {"type": "chunk", "content": chunk}

    yield {"type": "done", "full_response": answer}


def _generate_simulated_gemma_response(
    message: str, model: str, temperature: float
) -> str:
    """Generate intelligent mock responses matching user prompt for testing"""
    msg_lower = message.lower()

    gemma_details = (
        f"This response is simulated by the Google Gemma integrations. Configured model: `{model}`.\n\n"
        "Gemma models use JAX-native weights and Flax architectures. Key features include:\n"
        "- **Grouped Query Attention (GQA)** in Gemma 2+ for fast memory decoding.\n"
        "- **Rotary Position Embeddings (RoPE)** for efficient sequence scaling.\n"
        "- **Mixture of Experts (MoE)** support in Gemma 4 implementations."
    )

    if "hello" in msg_lower or "hi" in msg_lower:
        return f"Hello! I am Google Gemma ({model}), running in simulated local mode. How can I assist you with your JAX/Flax developments today?"
    elif "jax" in msg_lower or "flax" in msg_lower:
        return (
            "JAX is a high-performance numerical computation library that provides Autograd and XLA compilation. "
            "Flax is a flexible neural network library built on top of JAX. In Gemma, models are defined under `gemma.gm.nn` "
            "as Flax modules, allowing high-throughput TPU and GPU sharding.\n\n"
            "Here is how parameters are usually sharded in JAX:\n"
            "```python\n"
            "from gemma import gm\n"
            "sharding = gm.sharding.get_sharding_for_model(model)\n"
            "params = gm.ckpts.load_params(path, sharding=sharding)\n"
            "```"
        )
    elif "lora" in msg_lower or "fine" in msg_lower:
        return (
            "LoRA (Low-Rank Adaptation) freezes pre-trained model weights and injects trainable rank decomposition matrices. "
            "In this Gemma application, you can use the LoRA Trainer to configure rank, alpha, and learning rate parameters, "
            "run a simulated training loop, and save the adapter weights to your local storage bucket."
        )
    else:
        return (
            f'You asked: "{message}"\n\n'
            f"Here is a Gemma model response from **{model}**:\n\n"
            "I've received your query in DurgasOS. To test real-time weights loading or fine-tuning workflows, "
            "please navigate to the other tabs in the Gemma App (Checkpoints Loader and LoRA Trainer).\n\n"
            f"{gemma_details}"
        )


async def handle_gemma_checkpoints_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle gemma.checkpoints.list method"""
    # Check if a custom checkpoint path is defined
    has_local = False
    if settings.gemma_checkpoint_path:
        has_local = Path(settings.gemma_checkpoint_path).exists()

    result = []
    for ckpt in GEMMA_CHECKPOINTS:
        c = ckpt.copy()
        c["status"] = (
            "available"
            if has_local and ckpt["id"] == "GEMMA3_4B_IT"
            else "download_required"
        )
        result.append(c)

    return {"checkpoints": result}


async def handle_gemma_checkpoints_load(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Handle gemma.checkpoints.load method (streams progress logs)"""
    checkpoint_id = params.get("checkpoint_id", "GEMMA3_4B_IT")

    # Find checkpoint details
    checkpoint = next(
        (c for c in GEMMA_CHECKPOINTS if c["id"] == checkpoint_id), GEMMA_CHECKPOINTS[2]
    )

    logs = [
        f"[INFO] Initializing connection to Google Storage bucket: {checkpoint['path']}",
        "[INFO] Resolving Orbax checkpoint metadata...",
        "[INFO] Downloading checkpoint files (weight arrays, model parameters, tokenizer)...",
        "[PROGRESS] Downloading: 10%",
        "[PROGRESS] Downloading: 30%",
        "[PROGRESS] Downloading: 55%",
        "[PROGRESS] Downloading: 80%",
        "[PROGRESS] Downloading: 100%",
        f"[INFO] Download completed. Total size: {random.randint(4, 16)} GB.",
        "[INFO] Parsing Orbax checkpoint structure... (Format: FLAT / NESTED)",
        f"[INFO] Constructing Gemma {checkpoint['version']} {checkpoint['size']} Flax Module...",
        "[INFO] Setting up sharding constraints and JAX meshes...",
        "[INFO] Loading parameter matrices to device memory (CPU/GPU)...",
        f"[SUCCESS] Checkpoint '{checkpoint_id}' successfully loaded! Model is active and ready for inference.",
    ]

    for log in logs:
        # Simulate time for each step
        delay = 0.8 if "PROGRESS" in log else 0.5
        if "100%" in log:
            delay = 1.2
        await asyncio.sleep(delay)

        # Parse log status
        level = "info"
        percent = None
        if "[PROGRESS]" in log:
            level = "progress"
            # Extract number
            try:
                percent = int(log.split(":")[-1].strip().replace("%", ""))
            except (ValueError, IndexError):
                percent = 50
        elif "[SUCCESS]" in log:
            level = "success"

        yield {
            "log": log,
            "level": level,
            "percent": percent,
            "checkpoint": checkpoint_id,
            "timestamp": asyncio.get_event_loop().time(),
        }


async def handle_gemma_finetune_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Handle gemma.finetune.run method (streams training logs and saves dummy adapter)"""
    dataset = params.get("dataset", "Coding Skills")
    epochs = int(params.get("epochs", 1))
    _learning_rate = float(params.get("learning_rate", 1e-4))
    rank = int(params.get("rank", 8))
    alpha = int(params.get("alpha", 16))

    yield {
        "log": f"[INFO] Initializing Gemma LoRA training. Dataset: '{dataset}', Rank: {rank}, Alpha: {alpha}",
        "level": "info",
    }
    await asyncio.sleep(0.6)

    yield {
        "log": "[INFO] Constructing Flax train state with Kauldron optimizer and cross-entropy loss...",
        "level": "info",
    }
    await asyncio.sleep(0.8)

    yield {
        "log": "[INFO] Loading train and validation datasets into memory...",
        "level": "info",
    }
    await asyncio.sleep(0.8)

    total_steps = epochs * 20
    current_loss = 2.80 + random.uniform(-0.1, 0.1)

    for step in range(1, total_steps + 1):
        # Calculate step metrics
        current_loss -= random.uniform(0.04, 0.11)
        if current_loss < 0.8:
            current_loss = 0.8 + random.uniform(0.01, 0.05)

        acc = 0.40 + (step / total_steps) * 0.45 + random.uniform(-0.02, 0.02)
        if acc > 0.95:
            acc = 0.95

        mem = 12.4 + random.uniform(-0.2, 0.4)

        log_msg = f"[STEP {step}/{total_steps}] Loss: {current_loss:.4f} | Accuracy: {acc * 100:.2f}% | Speed: {random.randint(110, 140)} tok/s | VRAM: {mem:.1f} GB"

        yield {
            "log": log_msg,
            "level": "step",
            "metrics": {
                "step": step,
                "total_steps": total_steps,
                "loss": current_loss,
                "accuracy": acc,
                "vram": mem,
            },
        }
        await asyncio.sleep(0.4)

    # Complete training and save dummy file in storage
    adapter_name = f"gemma_lora_adapter_{dataset.lower().replace(' ', '_')}"
    adapter_dir = (
        Path(settings.storage_root) / settings.storage_bucket_uploads / "gemma_adapters"
    )
    adapter_file = adapter_dir / f"{adapter_name}.bin"

    try:
        adapter_dir.mkdir(parents=True, exist_ok=True)
        # Write dummy model adapter file
        with open(adapter_file, "w") as f:
            f.write(
                f"DUMMY GEMMA LORA ADAPTER WEIGHTS\nDataset: {dataset}\nEpochs: {epochs}\nRank: {rank}\nAlpha: {alpha}\nLoss: {current_loss:.4f}\n"
            )
        logger.info(f"LoRA adapter saved successfully: {adapter_file}")

        # Format a relative path for the Files explorer
        relative_path = f"user-uploads/gemma_adapters/{adapter_name}.bin"

        yield {
            "log": f"[SUCCESS] LoRA Adapter training completed! Saved adapter file to storage at: {relative_path}",
            "level": "success",
            "adapter_file": relative_path,
        }
    except Exception as e:
        logger.error(f"Failed to save LoRA adapter: {e}")
        yield {
            "log": f"[SUCCESS] LoRA Adapter training completed! (Failed to write adapter file to disk: {str(e)})",
            "level": "success",
            "adapter_file": None,
        }


async def handle_gemma_models_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle gemma.models.list method"""
    return {"models": GEMMA_MODELS}


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "gemma.chat.completions": handle_gemma_chat_completions,
        "gemma.checkpoints.list": handle_gemma_checkpoints_list,
        "gemma.checkpoints.load": handle_gemma_checkpoints_load,
        "gemma.finetune.run": handle_gemma_finetune_run,
        "gemma.models.list": handle_gemma_models_list,
    }
