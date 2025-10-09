# src/utils/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AIConfig:
    use_instructlab: bool = os.getenv('USE_INSTRUCTLAB', 'false').lower() == 'true'
    shadow_mode: bool = os.getenv('SHADOW_MODE', 'true').lower() == 'true'
    instructlab_endpoint: str = os.getenv('INSTRUCTLAB_ENDPOINT', 'http://localhost:8000')
    confidence_threshold: float = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.85'))
    log_comparisons: bool = True
    
    # Model specific
    model_path: str = os.getenv('MODEL_PATH', 'models/mistral-7b-instruct-v0.2.Q4_K_M.gguf')
    model_context_length: int = 4096
    
# Add to .env
# USE_INSTRUCTLAB=true
# SHADOW_MODE=true
# INSTRUCTLAB_ENDPOINT=http://localhost:8000