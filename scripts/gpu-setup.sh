#!/bin/bash
# 🎮 GPU Setup and Configuration Script
# Automatically detects GPU availability and configures Docker accordingly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎮 vLLM GPU Configuration Setup${NC}"
echo -e "${BLUE}================================${NC}"

# Function to check NVIDIA GPU
check_nvidia_gpu() {
    echo -e "${YELLOW}🔍 Checking for NVIDIA GPU...${NC}"
    
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
            echo -e "${GREEN}✅ NVIDIA GPU detected: ${GPU_INFO}${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  nvidia-smi found but no GPU accessible${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  nvidia-smi not found${NC}"
        return 1
    fi
}

# Function to check Docker GPU runtime
check_docker_gpu() {
    echo -e "${YELLOW}🐳 Checking Docker GPU runtime...${NC}"
    
    # Check if docker has nvidia runtime
    if docker info 2>/dev/null | grep -q nvidia; then
        echo -e "${GREEN}✅ Docker nvidia runtime is available${NC}"
        
        # Test GPU access in container
        if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &> /dev/null; then
            echo -e "${GREEN}✅ Docker can access GPU${NC}"
            return 0
        else
            echo -e "${RED}❌ Docker cannot access GPU${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Docker nvidia runtime not configured${NC}"
        return 1
    fi
}

# Function to install NVIDIA Container Toolkit
install_nvidia_toolkit() {
    echo -e "${YELLOW}📦 Installing NVIDIA Container Toolkit...${NC}"
    
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        echo -e "${RED}❌ Cannot detect OS${NC}"
        return 1
    fi
    
    case $OS in
        ubuntu|debian)
            echo -e "${BLUE}Installing for Ubuntu/Debian...${NC}"
            
            # Add NVIDIA GPG key
            curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
            
            # Add repository
            curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
                sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
            
            # Install toolkit
            sudo apt-get update
            sudo apt-get install -y nvidia-container-toolkit
            
            # Configure Docker
            sudo nvidia-ctk runtime configure --runtime=docker
            sudo systemctl restart docker
            
            echo -e "${GREEN}✅ NVIDIA Container Toolkit installed${NC}"
            ;;
            
        centos|rhel|fedora)
            echo -e "${BLUE}Installing for RHEL/CentOS/Fedora...${NC}"
            
            # Add repository
            distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
            curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | \
                sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
            
            # Install toolkit
            sudo yum install -y nvidia-container-toolkit
            
            # Configure Docker
            sudo nvidia-ctk runtime configure --runtime=docker
            sudo systemctl restart docker
            
            echo -e "${GREEN}✅ NVIDIA Container Toolkit installed${NC}"
            ;;
            
        *)
            echo -e "${RED}❌ Unsupported OS: $OS${NC}"
            echo -e "${YELLOW}Please install NVIDIA Container Toolkit manually:${NC}"
            echo "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            return 1
            ;;
    esac
}

# Function to configure Docker daemon
configure_docker_daemon() {
    echo -e "${YELLOW}⚙️  Configuring Docker daemon...${NC}"
    
    # Backup existing config
    if [ -f /etc/docker/daemon.json ]; then
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
        echo -e "${BLUE}Backed up existing daemon.json${NC}"
    fi
    
    # Create new config with GPU runtime
    cat <<EOF | sudo tee /etc/docker/daemon.json
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "10"
    },
    "storage-driver": "overlay2",
    "features": {
        "buildkit": true
    }
}
EOF
    
    # Restart Docker
    echo -e "${YELLOW}Restarting Docker...${NC}"
    sudo systemctl restart docker
    
    # Verify
    if docker info 2>/dev/null | grep -q nvidia; then
        echo -e "${GREEN}✅ Docker daemon configured for GPU${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker daemon configuration failed${NC}"
        return 1
    fi
}

# Function to create GPU-enabled compose file
create_gpu_compose() {
    echo -e "${YELLOW}📝 Creating GPU-enabled Docker Compose configuration...${NC}"
    
    cat <<'EOF' > docker-compose.gpu.yml
# 🎮 GPU-Enabled Docker Compose Configuration
# Automatically uses GPU if available, falls back to CPU

services:
  # vLLM with GPU support
  vllm-phi-gpu:
    image: vllm/vllm-openai:latest
    container_name: vllm-phi-gpu
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - vllm_cache:/root/.cache/huggingface
    environment:
      VLLM_HOST: 0.0.0.0
      VLLM_PORT: 8000
      VLLM_MODEL: microsoft/Phi-3.5-mini-instruct
      VLLM_TENSOR_PARALLEL_SIZE: ${GPU_COUNT:-1}
      VLLM_GPU_MEMORY_UTILIZATION: ${GPU_MEMORY_UTIL:-0.80}
      VLLM_MAX_MODEL_LEN: ${MAX_MODEL_LEN:-16384}
      VLLM_TRUST_REMOTE_CODE: true
      CUDA_VISIBLE_DEVICES: ${CUDA_DEVICES:-0}
    command: >
      --model microsoft/Phi-3.5-mini-instruct
      --host 0.0.0.0
      --port 8000
      --tensor-parallel-size ${GPU_COUNT:-1}
      --gpu-memory-utilization ${GPU_MEMORY_UTIL:-0.80}
      --max-model-len ${MAX_MODEL_LEN:-16384}
      --trust-remote-code
      --served-model-name phi-3.5-mini
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: ${GPU_COUNT:-1}
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - vllm-network
    restart: unless-stopped

  # CPU fallback version
  vllm-phi-cpu:
    build:
      context: .
      dockerfile: docker/Dockerfile.cpu-inference
    container_name: vllm-phi-cpu
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - vllm_cache:/root/.cache/huggingface
    environment:
      MODEL_NAME: microsoft/Phi-3.5-mini-instruct
      MAX_LENGTH: 2048
      DEVICE: cpu
      NUM_THREADS: ${CPU_THREADS:-4}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vllm-network
    profiles:
      - cpu
    restart: unless-stopped

volumes:
  vllm_cache:
    driver: local

networks:
  vllm-network:
    external: true
EOF
    
    echo -e "${GREEN}✅ GPU compose file created${NC}"
}

# Function to create CPU inference Dockerfile
create_cpu_dockerfile() {
    echo -e "${YELLOW}📝 Creating CPU inference Dockerfile...${NC}"
    
    cat <<'EOF' > docker/Dockerfile.cpu-inference
# CPU-based inference for fallback
FROM python:3.11-slim

WORKDIR /app

# Install CPU-optimized packages
RUN pip install --no-cache-dir \
    torch==2.5.1+cpu torchvision==0.20.1+cpu -f https://download.pytorch.org/whl/torch_stable.html \
    transformers==4.48.0 \
    fastapi==0.115.5 \
    uvicorn[standard]==0.34.0 \
    accelerate==1.2.1 \
    optimum==1.24.1

# Copy inference server
COPY docker/scripts/cpu_inference_server.py /app/

# Set environment for CPU optimization
ENV OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    TORCH_NUM_THREADS=4

EXPOSE 8000

CMD ["python", "cpu_inference_server.py"]
EOF
    
    echo -e "${GREEN}✅ CPU Dockerfile created${NC}"
}

# Function to create CPU inference server
create_cpu_server() {
    echo -e "${YELLOW}📝 Creating CPU inference server...${NC}"
    
    cat <<'EOF' > docker/scripts/cpu_inference_server.py
"""
CPU-based inference server for vLLM fallback
Provides OpenAI-compatible API using CPU
"""

import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CPU Inference Server")

# Global model and tokenizer
model = None
tokenizer = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-cpu"
    object: str = "chat.completion"
    created: int = 0
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.on_event("startup")
async def load_model():
    """Load model on startup"""
    global model, tokenizer
    
    model_name = os.getenv("MODEL_NAME", "microsoft/Phi-3.5-mini-instruct")
    device = "cpu"
    
    logger.info(f"Loading model {model_name} on {device}")
    
    try:
        # Load with CPU optimizations
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,  # Use float32 for CPU
            device_map=device,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        # Optimize for CPU inference
        model.eval()
        torch.set_num_threads(int(os.getenv("NUM_THREADS", "4")))
        
        logger.info("Model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": "cpu",
        "threads": torch.get_num_threads()
    }

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": os.getenv("MODEL_NAME", "microsoft/Phi-3.5-mini-instruct"),
                "object": "model",
                "owned_by": "cpu-inference"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint"""
    
    if not model or not tokenizer:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Format messages for the model
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Tokenize input
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = tokenizer(text, return_tensors="pt")
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                do_sample=True if request.temperature > 0 else False,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the assistant's response
        if len(messages) > 0:
            last_user_msg = messages[-1]["content"]
            if last_user_msg in response_text:
                response_text = response_text.split(last_user_msg)[-1].strip()
        
        # Format response
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            usage={
                "prompt_tokens": len(inputs["input_ids"][0]),
                "completion_tokens": len(outputs[0]) - len(inputs["input_ids"][0]),
                "total_tokens": len(outputs[0])
            }
        )
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
EOF
    
    echo -e "${GREEN}✅ CPU inference server created${NC}"
}

# Function to detect and configure
auto_configure() {
    echo -e "${BLUE}🤖 Auto-configuring based on system capabilities...${NC}"
    
    GPU_AVAILABLE=false
    USE_CPU_FALLBACK=false
    
    # Check for GPU
    if check_nvidia_gpu; then
        # Check Docker GPU support
        if check_docker_gpu; then
            GPU_AVAILABLE=true
            echo -e "${GREEN}✅ GPU configuration verified${NC}"
        else
            echo -e "${YELLOW}GPU detected but Docker not configured${NC}"
            
            # Offer to install NVIDIA toolkit
            read -p "Install NVIDIA Container Toolkit? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if install_nvidia_toolkit && configure_docker_daemon; then
                    GPU_AVAILABLE=true
                    echo -e "${GREEN}✅ GPU support configured${NC}"
                else
                    USE_CPU_FALLBACK=true
                    echo -e "${YELLOW}⚠️  Using CPU fallback${NC}"
                fi
            else
                USE_CPU_FALLBACK=true
                echo -e "${YELLOW}⚠️  Using CPU fallback${NC}"
            fi
        fi
    else
        USE_CPU_FALLBACK=true
        echo -e "${YELLOW}ℹ️  No GPU detected, using CPU inference${NC}"
    fi
    
    # Create appropriate configuration
    create_gpu_compose
    create_cpu_dockerfile
    create_cpu_server
    
    # Create .env file with configuration
    echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
    
    if [ "$GPU_AVAILABLE" = true ]; then
        cat <<EOF > .env.gpu
# GPU Configuration
USE_GPU=true
GPU_COUNT=1
GPU_MEMORY_UTIL=0.80
MAX_MODEL_LEN=16384
CUDA_DEVICES=0
INFERENCE_PROFILE=gpu
EOF
        echo -e "${GREEN}✅ GPU configuration saved to .env.gpu${NC}"
        
        # Create start script
        cat <<'EOF' > start-gpu.sh
#!/bin/bash
echo "Starting with GPU acceleration..."
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d vllm-phi-gpu
EOF
        chmod +x start-gpu.sh
        
    else
        cat <<EOF > .env.gpu
# CPU Configuration (No GPU available)
USE_GPU=false
CPU_THREADS=4
MAX_LENGTH=2048
DEVICE=cpu
INFERENCE_PROFILE=cpu
EOF
        echo -e "${GREEN}✅ CPU configuration saved to .env.gpu${NC}"
        
        # Create start script
        cat <<'EOF' > start-cpu.sh
#!/bin/bash
echo "Starting with CPU inference..."
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml --profile cpu up -d vllm-phi-cpu
EOF
        chmod +x start-cpu.sh
    fi
}

# Main execution
main() {
    echo -e "${BLUE}Starting GPU setup...${NC}"
    echo
    
    # Run auto-configuration
    auto_configure
    
    echo
    echo -e "${BLUE}================================${NC}"
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo
    
    if [ -f .env.gpu ]; then
        source .env.gpu
        if [ "$USE_GPU" = "true" ]; then
            echo -e "${YELLOW}📋 Next Steps (GPU Mode):${NC}"
            echo "  1. Start services: ${GREEN}./start-gpu.sh${NC}"
            echo "  2. Check GPU usage: ${GREEN}nvidia-smi${NC}"
            echo "  3. Monitor logs: ${GREEN}docker logs -f vllm-phi-gpu${NC}"
        else
            echo -e "${YELLOW}📋 Next Steps (CPU Mode):${NC}"
            echo "  1. Build CPU image: ${GREEN}docker build -f docker/Dockerfile.cpu-inference -t vllm-cpu .${NC}"
            echo "  2. Start services: ${GREEN}./start-cpu.sh${NC}"
            echo "  3. Monitor logs: ${GREEN}docker logs -f vllm-phi-cpu${NC}"
        fi
    fi
    
    echo
    echo -e "${BLUE}For manual configuration, edit .env.gpu${NC}"
}

# Run main function
main "$@"