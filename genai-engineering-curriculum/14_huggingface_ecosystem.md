# Module 14 — HuggingFace Ecosystem

> HuggingFace is the GitHub of machine learning. This module covers the full HF stack: Transformers, Tokenizers, Datasets, PEFT, and the Inference API — everything needed to work with open-source models in production.

---

## Table of Contents

1. [HuggingFace Ecosystem Overview](#1-huggingface-ecosystem-overview)
2. [Tokenizers — Deep Dive](#2-tokenizers)
3. [Transformers Pipeline API](#3-transformers-pipeline-api)
4. [Loading and Using Models Directly](#4-loading-and-using-models-directly)
5. [HuggingFace Datasets](#5-huggingface-datasets)
6. [Inference API and Inference Endpoints](#6-inference-api-and-inference-endpoints)
7. [Text Generation Configuration](#7-text-generation-configuration)
8. [Embeddings with Sentence Transformers](#8-embeddings-with-sentence-transformers)
9. [PEFT and LoRA Fine-Tuning](#9-peft-and-lora-fine-tuning)
10. [Integrating HF Models with LangChain](#10-integrating-hf-models-with-langchain)
11. [Model Selection and Evaluation](#11-model-selection-and-evaluation)
12. [Interview Questions](#12-interview-questions)

---

## 1. HuggingFace Ecosystem Overview

```
HuggingFace Stack:
├── Hub                   — Model/dataset/space repository (huggingface.co)
├── transformers          — Model loading, inference, training
├── tokenizers            — Fast Rust tokenizers
├── datasets              — Efficient dataset loading and processing
├── evaluate              — Metrics (BLEU, ROUGE, accuracy, F1)
├── peft                  — Parameter-efficient fine-tuning (LoRA, QLoRA)
├── trl                   — Reinforcement learning from human feedback (RLHF/DPO)
├── accelerate            — Multi-GPU/TPU training coordination
├── diffusers             — Diffusion models (Stable Diffusion, etc.)
├── sentence-transformers — Sentence embeddings
└── huggingface_hub       — Hub API client
```

### Installation

```bash
pip install transformers datasets tokenizers evaluate
pip install peft accelerate trl          # for fine-tuning
pip install sentence-transformers        # for embeddings
pip install bitsandbytes                 # for quantization
pip install huggingface_hub              # for Hub API
```

### Hub Concepts

```python
from huggingface_hub import HfApi, login, snapshot_download

# Authenticate (required for private models)
login(token="hf_your_token")  # or set HF_TOKEN env var

api = HfApi()

# Search models
models = api.list_models(
    filter="text-generation",
    sort="downloads",
    direction=-1,
    limit=10,
    cardData=True
)
for m in models:
    print(f"{m.id}: {m.downloads:,} downloads")

# Get model info
model_info = api.model_info("meta-llama/Llama-3.1-8B-Instruct")
print(f"Parameters: {model_info.safetensors}")
print(f"License: {model_info.cardData.get('license', 'unknown')}")
print(f"Tags: {model_info.tags}")

# Download entire model locally
snapshot_download(
    repo_id="google/gemma-2-2b-it",
    local_dir="./models/gemma-2-2b-it",
    ignore_patterns=["*.msgpack", "*.h5"],  # Skip TF/Flax weights
)
```

---

## 2. Tokenizers

Understanding tokenizers is essential for working with LLMs — they control how text becomes numbers.

### How Tokenization Works

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")

# Basic tokenization
text = "HuggingFace tokenizers are fast!"
tokens = tokenizer.tokenize(text)
print(tokens)
# ['H', 'ugging', 'F', 'ace', 'Ġtoken', 'izers', 'Ġare', 'Ġfast', '!']

# Token IDs (what the model actually sees)
ids = tokenizer.encode(text)
print(ids)  # [1, 44, 57, 29954, 459, ...]

# Full encoding with attention mask
encoding = tokenizer(
    text,
    return_tensors="pt",          # "pt" for PyTorch, "np" for NumPy
    padding=True,
    truncation=True,
    max_length=512,
    add_special_tokens=True,
)
print(encoding.keys())
# ['input_ids', 'attention_mask']

# Decode back to text
decoded = tokenizer.decode(ids, skip_special_tokens=True)
print(decoded)  # "HuggingFace tokenizers are fast!"

# Count tokens (critical for prompt management)
def count_tokens(text: str, tokenizer) -> int:
    return len(tokenizer.encode(text))

print(count_tokens("The quick brown fox jumps over the lazy dog.", tokenizer))
# → 10
```

### Batch Tokenization with Padding

```python
texts = [
    "Short text.",
    "This is a much longer piece of text that will need padding.",
    "Medium length text here.",
]

# Pad to longest in batch
batch_encoding = tokenizer(
    texts,
    padding=True,       # Pad to longest in batch
    truncation=True,
    max_length=128,
    return_tensors="pt",
)

print(batch_encoding["input_ids"].shape)  # [3, max_len]
print(batch_encoding["attention_mask"])   # 1=real token, 0=padding
```

### Chat Templates

Modern instruction-tuned models use special chat formats:

```python
# Llama 3.1 chat template
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is RAG?"},
    {"role": "assistant", "content": "RAG stands for Retrieval-Augmented Generation..."},
    {"role": "user", "content": "Can you give an example?"},
]

# Apply model-specific chat template
formatted = tokenizer.apply_chat_template(
    messages,
    tokenize=False,          # Return string (not token IDs)
    add_generation_prompt=True,  # Add the assistant turn starter
)
print(formatted)
# <|begin_of_text|><|start_header_id|>system<|end_header_id|>
# You are a helpful assistant.<|eot_id|>...

# Tokenize for inference
inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    return_tensors="pt",
    add_generation_prompt=True,
)
```

### Special Tokens

```python
# Common special tokens
print(f"BOS: {tokenizer.bos_token} ({tokenizer.bos_token_id})")
print(f"EOS: {tokenizer.eos_token} ({tokenizer.eos_token_id})")
print(f"PAD: {tokenizer.pad_token} ({tokenizer.pad_token_id})")
print(f"UNK: {tokenizer.unk_token}")

# Vocabulary size
print(f"Vocab size: {tokenizer.vocab_size:,}")

# Check if text is likely one token
for word in ["cat", "photosynthesis", "supercalifragilistic"]:
    n = count_tokens(word, tokenizer)
    print(f"'{word}': {n} tokens")
```

### Tokenizer Gotchas

```python
# Gotcha 1: Whitespace matters
print(tokenizer.tokenize("hello"))   # ['hello']
print(tokenizer.tokenize(" hello"))  # ['Ġhello']  — different!

# Gotcha 2: Numbers split into many tokens
print(tokenizer.tokenize("1234567890"))
# ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']  — 10 tokens!

# Gotcha 3: Code is verbose in tokens
code = "def fibonacci(n):\n    if n <= 1: return n"
print(f"Code tokens: {count_tokens(code, tokenizer)}")

# Gotcha 4: Languages vary greatly
print(count_tokens("Hello world", tokenizer))   # ~3 tokens
print(count_tokens("こんにちは世界", tokenizer)) # ~8-15 tokens (Japanese)
```

---

## 3. Transformers Pipeline API

The Pipeline API is the fastest way to run inference with any HF model.

### Basic Pipelines

```python
from transformers import pipeline
import torch

# Text generation (causal LM)
generator = pipeline(
    "text-generation",
    model="meta-llama/Llama-3.2-1B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto",   # Automatically use GPU if available
)

result = generator(
    "Explain transformer architecture in one sentence:",
    max_new_tokens=100,
    temperature=0.7,
    do_sample=True,
    repetition_penalty=1.1,
)
print(result[0]["generated_text"])

# Text classification (sentiment, etc.)
classifier = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    device=0  # GPU 0
)
print(classifier("This product is amazing!"))
# [{'label': 'positive', 'score': 0.989}]

# Named entity recognition
ner = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple",  # Merge subword tokens
)
print(ner("Viru works at Wells Fargo in Hyderabad."))

# Question answering (extractive)
qa = pipeline("question-answering", model="deepset/roberta-base-squad2")
result = qa(
    question="Where is Wells Fargo headquartered?",
    context="Wells Fargo is a major American bank headquartered in San Francisco, California."
)
print(result)  # {'answer': 'San Francisco, California', 'score': 0.95}

# Summarization
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
summary = summarizer(long_text, max_length=150, min_length=40)
print(summary[0]["summary_text"])

# Translation
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-fr")
print(translator("Hello, how are you?")[0]["translation_text"])
# "Bonjour, comment allez-vous ?"

# Zero-shot classification (no fine-tuning needed)
zero_shot = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
result = zero_shot(
    "This movie has excellent visual effects but a weak plot.",
    candidate_labels=["positive review", "negative review", "mixed review"],
)
print(result)  # Labels sorted by score
```

### Pipeline with Batching

```python
generator = pipeline(
    "text-generation",
    model="gpt2",
    device=0,
    batch_size=8,      # Process 8 inputs at once
)

texts = [f"The capital of {country} is" for country in ["France", "Japan", "Brazil", "India"]]
results = generator(texts, max_new_tokens=10, do_sample=False)

for text, result in zip(texts, results):
    print(f"{text} → {result[0]['generated_text']}")
```

### Chat Pipeline (Instruction Models)

```python
from transformers import pipeline

chat_pipeline = pipeline(
    "text-generation",
    model="meta-llama/Llama-3.1-8B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

messages = [
    {"role": "system", "content": "You are a Python expert."},
    {"role": "user", "content": "Write a one-line function to check if a number is prime."},
]

response = chat_pipeline(
    messages,
    max_new_tokens=200,
    temperature=0.1,
    do_sample=True,
)
print(response[0]["generated_text"][-1]["content"])
```

---

## 4. Loading and Using Models Directly

For more control than the Pipeline API provides:

### AutoModel Pattern

```python
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BitsAndBytesConfig,
)
import torch

# Load with 4-bit quantization (saves ~75% VRAM)
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct",
    quantization_config=quantization_config,
    device_map="auto",
    trust_remote_code=False,
    attn_implementation="flash_attention_2",  # Faster attention if available
)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
tokenizer.pad_token = tokenizer.eos_token  # Set pad token if missing

# Inference
def generate_response(
    messages: list[dict],
    max_new_tokens: int = 512,
    temperature: float = 0.1,
) -> str:
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    
    # Decode only new tokens (not the input)
    new_tokens = outputs[0][inputs.shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)

result = generate_response([
    {"role": "user", "content": "Explain HNSW in 2 sentences."}
])
print(result)
```

### Model Parameters and Memory

```python
def model_summary(model) -> dict:
    """Get model parameter count and memory estimate."""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    # Estimate memory (rough: 2 bytes per param for fp16, 4 for fp32)
    dtype_bytes = {"float32": 4, "float16": 2, "bfloat16": 2, "int8": 1, "int4": 0.5}
    model_dtype = str(next(model.parameters()).dtype).split(".")[-1]
    bytes_per_param = dtype_bytes.get(model_dtype, 2)
    memory_gb = total_params * bytes_per_param / (1024**3)
    
    return {
        "total_parameters": f"{total_params/1e9:.2f}B",
        "trainable_parameters": f"{trainable_params/1e6:.2f}M",
        "model_dtype": model_dtype,
        "estimated_memory_gb": f"{memory_gb:.1f} GB",
    }

print(model_summary(model))
```

### Streaming Generation

```python
from transformers import TextStreamer, TextIteratorStreamer
from threading import Thread

# TextStreamer: prints tokens as they generate
streamer = TextStreamer(tokenizer, skip_special_tokens=True)

model.generate(inputs, max_new_tokens=200, streamer=streamer)

# TextIteratorStreamer: iterate over tokens (for FastAPI/async)
streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)

# Run generation in background thread
generation_kwargs = dict(
    inputs=inputs,
    max_new_tokens=200,
    streamer=streamer,
)
thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Yield tokens as they arrive
full_response = ""
for token in streamer:
    full_response += token
    print(token, end="", flush=True)
```

---

## 5. HuggingFace Datasets

```python
from datasets import load_dataset, Dataset, DatasetDict
import pandas as pd

# Load from Hub
squad = load_dataset("rajpurkar/squad", split="train")
print(squad)
# Dataset({features: ['id', 'title', 'context', 'question', 'answers'], num_rows: 87599})

# Access like a dictionary
print(squad[0])  # First example
print(squad["question"][:3])  # First 3 questions

# Filter
filtered = squad.filter(lambda x: len(x["context"]) < 500)
print(f"Filtered: {len(filtered)} examples")

# Map transform (vectorized operations)
def preprocess(example):
    return {
        "question_lower": example["question"].lower(),
        "context_len": len(example["context"].split()),
    }

processed = squad.map(preprocess, batched=False, num_proc=4)

# Batched map (much faster for tokenization)
def tokenize_batch(batch):
    return tokenizer(
        batch["question"],
        batch["context"],
        truncation=True,
        max_length=512,
        padding="max_length",
    )

tokenized = squad.map(tokenize_batch, batched=True, batch_size=32)

# Create dataset from pandas
df = pd.DataFrame({"text": ["Example 1", "Example 2"], "label": [0, 1]})
hf_dataset = Dataset.from_pandas(df)

# Create from dict
my_dataset = Dataset.from_dict({
    "question": ["What is AI?", "What is ML?"],
    "answer": ["AI is...", "ML is..."],
})

# Save and load
my_dataset.save_to_disk("./my_dataset")
loaded = Dataset.load_from_disk("./my_dataset")

# Streaming (for large datasets that don't fit in memory)
large_dataset = load_dataset("HuggingFaceFW/fineweb", streaming=True, split="train")
for example in large_dataset.take(10):
    print(example["text"][:100])
```

---

## 6. Inference API and Inference Endpoints

### Serverless Inference API (Free Tier)

```python
import requests

HF_TOKEN = "hf_your_token"
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_hf_api(payload: dict) -> dict:
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

# Text generation
result = query_hf_api({
    "inputs": "What is the capital of France?",
    "parameters": {
        "max_new_tokens": 100,
        "temperature": 0.7,
        "return_full_text": False,
    }
})
print(result[0]["generated_text"])
```

### HuggingFace Inference Client (Recommended)

```python
from huggingface_hub import InferenceClient

client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    token="hf_your_token",
)

# Text generation
response = client.text_generation(
    prompt="Explain neural networks:",
    max_new_tokens=200,
    temperature=0.7,
    stream=False,
)
print(response)

# Chat completion (OpenAI-compatible API)
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is LangGraph?"},
    ],
    max_tokens=300,
    temperature=0.1,
)
print(response.choices[0].message.content)

# Streaming chat
for chunk in client.chat_completion(
    messages=[{"role": "user", "content": "Tell me about RAG"}],
    max_tokens=200,
    stream=True,
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# Embeddings
embeddings = client.feature_extraction(
    text="This is a sentence to embed",
    model="BAAI/bge-small-en-v1.5",
)
print(f"Embedding shape: {len(embeddings[0])}")
```

### Dedicated Inference Endpoints

For production workloads, deploy a dedicated endpoint:

```python
from huggingface_hub import InferenceClient

# After creating endpoint at huggingface.co/inference-endpoints
endpoint_url = "https://your-endpoint.endpoints.huggingface.cloud"

client = InferenceClient(
    base_url=endpoint_url,
    token="hf_your_token",
)

# Same API as serverless
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100,
)
```

---

## 7. Text Generation Configuration

Understanding generation parameters is critical for controlling LLM output:

```python
from transformers import GenerationConfig

# Create a generation config
gen_config = GenerationConfig(
    # Length control
    max_new_tokens=512,           # Hard cap on new tokens
    min_new_tokens=10,            # Force at least N tokens
    
    # Sampling strategy
    do_sample=True,               # False = greedy decoding
    temperature=0.7,              # Higher = more random (0.1-1.5 typical)
    top_p=0.9,                    # Nucleus sampling: sample from top 90% probability mass
    top_k=50,                     # Sample only from top 50 tokens
    
    # Repetition control
    repetition_penalty=1.1,       # Penalize repeated tokens (1.0 = no penalty)
    no_repeat_ngram_size=3,       # Prevent repeating 3-grams
    
    # Beam search (alternative to sampling)
    # num_beams=4,                # Use beam search with 4 beams
    # early_stopping=True,
    
    # Special tokens
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.pad_token_id,
    
    # Output format
    return_dict_in_generate=True,
    output_scores=True,           # Return per-token logits
)

outputs = model.generate(inputs, generation_config=gen_config)
```

### Decoding Strategies Explained

```
GREEDY (do_sample=False):
→ Always picks highest probability token
→ Fast, deterministic, but repetitive for long outputs
→ Use for: factual QA, structured outputs

TEMPERATURE SAMPLING (do_sample=True, temperature=T):
→ T < 1.0: more focused/conservative
→ T = 1.0: sample from raw distribution
→ T > 1.0: more creative/random
→ T = 0.0: equivalent to greedy

TOP-K (top_k=K):
→ Sample only from the K most likely tokens
→ Prevents very unlikely tokens

TOP-P NUCLEUS (top_p=P):
→ Sample from smallest set of tokens whose cumulative probability >= P
→ Dynamically adjusts based on distribution shape
→ Often better than top-k

BEAM SEARCH (num_beams=N):
→ Explore N candidate sequences in parallel, keep best overall
→ Better for translation and summarization
→ Slower, memory-intensive
```

---

## 8. Embeddings with Sentence Transformers

```python
from sentence_transformers import SentenceTransformer, util
import torch

# Load a sentence embedding model
model = SentenceTransformer("BAAI/bge-large-en-v1.5")

# Encode sentences
sentences = [
    "The quick brown fox jumps over the lazy dog",
    "A fast reddish fox leaps above a sleepy canine",
    "Python is a programming language",
    "Machine learning requires data",
]

embeddings = model.encode(
    sentences,
    batch_size=32,
    normalize_embeddings=True,   # L2 normalize for cosine similarity
    show_progress_bar=True,
    convert_to_tensor=True,      # Return torch tensor
)
print(f"Embedding shape: {embeddings.shape}")  # [4, 1024]

# Cosine similarity
similarity_matrix = util.cos_sim(embeddings, embeddings)
print(similarity_matrix)
# Sentences 0 and 1 should have high similarity (~0.9)
# Sentence 0 and 2 should have low similarity (~0.1)

# Semantic search
query = "fast animal"
query_embedding = model.encode(query, normalize_embeddings=True, convert_to_tensor=True)
hits = util.semantic_search(query_embedding, embeddings, top_k=3)
for hit in hits[0]:
    print(f"Score: {hit['score']:.3f} | {sentences[hit['corpus_id']]}")

# Asymmetric search (query vs passage) — use appropriate models
bi_encoder = SentenceTransformer("BAAI/bge-m3")  # Multilingual, bi-encoder

# Cross-encoder for re-ranking (slower but more accurate)
from sentence_transformers import CrossEncoder
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

pairs = [
    (query, sentences[0]),
    (query, sentences[2]),
]
scores = cross_encoder.predict(pairs)
print(scores)  # [0.8, 0.1] — sentence 0 more relevant

# Complete retrieval pipeline with re-ranking
def semantic_search_with_reranking(
    query: str,
    corpus: list[str],
    bi_enc: SentenceTransformer,
    cross_enc: CrossEncoder,
    top_k_retrieve: int = 50,
    top_k_rerank: int = 5,
) -> list[tuple[float, str]]:
    """Two-stage retrieval: fast bi-encoder + accurate cross-encoder."""
    corpus_embeddings = bi_enc.encode(corpus, normalize_embeddings=True, convert_to_tensor=True)
    query_embedding = bi_enc.encode(query, normalize_embeddings=True, convert_to_tensor=True)
    
    # Stage 1: Fast retrieval
    hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=top_k_retrieve)
    candidates = [(corpus[h["corpus_id"]], h["score"]) for h in hits[0]]
    
    # Stage 2: Rerank with cross-encoder
    cross_input = [(query, doc) for doc, _ in candidates]
    cross_scores = cross_enc.predict(cross_input)
    
    # Sort by cross-encoder score
    reranked = sorted(zip(cross_scores, [doc for doc, _ in candidates]), reverse=True)
    return reranked[:top_k_rerank]
```

### Popular Embedding Models Comparison

```python
EMBEDDING_MODELS = {
    # Best quality, English
    "text-embedding-3-large": {"provider": "OpenAI", "dim": 3072, "cost": "$0.13/1M tokens"},
    "BAAI/bge-large-en-v1.5": {"provider": "HF/local", "dim": 1024, "cost": "free"},
    
    # Balanced quality/speed
    "text-embedding-3-small": {"provider": "OpenAI", "dim": 1536, "cost": "$0.02/1M tokens"},
    "BAAI/bge-base-en-v1.5": {"provider": "HF/local", "dim": 768, "cost": "free"},
    
    # Multilingual
    "BAAI/bge-m3": {"provider": "HF/local", "dim": 1024, "cost": "free"},
    
    # Production re-rankers
    "cross-encoder/ms-marco-MiniLM-L-6-v2": {"provider": "HF/local", "type": "cross-encoder"},
    "BAAI/bge-reranker-large": {"provider": "HF/local", "type": "cross-encoder"},
}
```

---

## 9. PEFT and LoRA Fine-Tuning

Parameter-Efficient Fine-Tuning (PEFT) allows fine-tuning large models by training only a small number of additional parameters.

### LoRA Concepts

```
Full Fine-Tuning:     Update ALL parameters (billions)
LoRA Fine-Tuning:     Only train small adapter matrices (millions)

How LoRA works:
- Freeze the original model weights W
- Add low-rank decomposition: ΔW = A × B
  where A ∈ R^(d×r), B ∈ R^(r×k), rank r << min(d,k)
- During inference: W' = W + α × (A × B)

Example: Llama-3 8B
- Full fine-tune: ~30GB VRAM, update 8B parameters
- LoRA (r=16): ~6GB VRAM, update ~10M parameters
- QLoRA (4-bit + LoRA): ~5GB VRAM
```

### LoRA Fine-Tuning Setup

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from trl import SFTTrainer
from datasets import load_dataset
import torch

# 1. Load model in 4-bit (QLoRA)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    quantization_config=bnb_config,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")
tokenizer.pad_token = tokenizer.eos_token

# 2. Prepare for PEFT
model = prepare_model_for_kbit_training(model)

# 3. Configure LoRA
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                          # Rank (4-64, higher = more parameters = better but slower)
    lora_alpha=32,                 # Scaling factor (usually 2x rank)
    lora_dropout=0.05,
    target_modules=[               # Which layers to apply LoRA to
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
)

# 4. Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# trainable params: 9,175,040 || all params: 8,039,469,056 || trainable%: 0.11%

# 5. Training arguments
training_args = TrainingArguments(
    output_dir="./fine-tuned-llama",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,   # Effective batch size = 4 * 4 = 16
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    optim="paged_adamw_32bit",       # Memory-efficient optimizer
)

# 6. Load dataset
dataset = load_dataset("your-dataset", split="train")

# 7. Format function
def format_instruction(example):
    return f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>
{example['instruction']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{example['output']}<|eot_id|>"""

# 8. Train with SFTTrainer
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    tokenizer=tokenizer,
    formatting_func=format_instruction,
    max_seq_length=2048,
    packing=False,
)

trainer.train()

# 9. Save adapter
model.save_pretrained("./lora-adapter")
tokenizer.save_pretrained("./lora-adapter")

# 10. Load and merge (optional — merge for faster inference)
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B")
model_with_lora = PeftModel.from_pretrained(base_model, "./lora-adapter")
merged_model = model_with_lora.merge_and_unload()  # Merge into base weights
merged_model.save_pretrained("./merged-model")
```

---

## 10. Integrating HF Models with LangChain

```python
from langchain_huggingface import HuggingFacePipeline, HuggingFaceEmbeddings
from transformers import pipeline
import torch

# Local model as LangChain LLM
hf_pipeline = pipeline(
    "text-generation",
    model="meta-llama/Llama-3.2-1B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    max_new_tokens=512,
)

llm = HuggingFacePipeline(pipeline=hf_pipeline)

# Use in LCEL chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

chain = ChatPromptTemplate.from_template("Question: {q}\nAnswer:") | llm | StrOutputParser()
result = chain.invoke({"q": "What is HNSW?"})
print(result)

# HuggingFace Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)

# Drop-in replacement for OpenAI embeddings
from langchain_community.vectorstores import Chroma

vectorstore = Chroma.from_texts(
    texts=["Document 1 content", "Document 2 content"],
    embedding=embeddings,
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# HuggingFace Inference API as LLM
from langchain_huggingface import HuggingFaceEndpoint

endpoint_llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    task="text-generation",
    max_new_tokens=512,
    temperature=0.1,
    huggingfacehub_api_token="hf_your_token",
)
```

---

## 11. Model Selection and Evaluation

### Model Selection Framework

```python
SELECTION_CRITERIA = {
    "task": {
        "chat/instruction": ["Llama-3.1-8B-Instruct", "Mistral-7B-Instruct", "Phi-3.5-mini"],
        "code_generation": ["Qwen2.5-Coder-7B", "DeepSeek-Coder-V2", "CodeLlama-13B"],
        "embeddings": ["BAAI/bge-large-en-v1.5", "e5-large-v2", "mxbai-embed-large-v1"],
        "reranking": ["BAAI/bge-reranker-large", "cross-encoder/ms-marco-MiniLM-L-12-v2"],
        "summarization": ["Llama-3.1-8B-Instruct", "facebook/bart-large-cnn"],
    },
    "constraints": {
        "4GB_VRAM": ["phi-3.5-mini", "BAAI/bge-small-en"],
        "8GB_VRAM": ["Llama-3.2-1B", "Mistral-7B-Instruct-Q4"],
        "16GB_VRAM": ["Llama-3.1-8B-Instruct", "Qwen2.5-7B"],
        "24GB_VRAM": ["Llama-3.1-13B", "Mixtral-8x7B-Q4"],
        "80GB_VRAM": ["Llama-3.1-70B", "Qwen2.5-72B"],
    },
    "benchmarks": {
        "MMLU": "General knowledge",
        "HumanEval": "Code generation",
        "MT-Bench": "Multi-turn chat",
        "MTEB": "Embeddings quality",
    }
}
```

### Automated Evaluation

```python
from evaluate import load

# ROUGE for summarization
rouge = load("rouge")
results = rouge.compute(
    predictions=["The cat sat on the mat."],
    references=["The feline rested on the carpet."]
)
print(results)  # {'rouge1': 0.4, 'rouge2': 0.0, 'rougeL': 0.4}

# BLEU for translation
bleu = load("bleu")
results = bleu.compute(
    predictions=["the cat is on the mat"],
    references=[["the cat is on the mat", "there is a cat on the mat"]]
)
print(results)  # {'bleu': 0.756, 'precisions': [...]}

# Perplexity (measures how "surprised" a model is by text)
perplexity = load("perplexity", module_type="metric")
results = perplexity.compute(
    model_id="gpt2",
    predictions=["This is natural text", "xzkq fjmn wrpq sklm"],
)
print(results["mean_perplexity"])  # Low = natural text

# F1 for classification
f1 = load("f1")
results = f1.compute(predictions=[0, 1, 1, 0], references=[0, 1, 0, 0], average="macro")
print(results)  # {'f1': 0.75}
```

---

## 12. Interview Questions

**Q1: What is the difference between a tokenizer's vocabulary size and the model's embedding dimension?**

Vocabulary size is the number of distinct tokens the tokenizer can represent — typically 32K–128K entries. This determines the size of the embedding lookup table: `[vocab_size × embedding_dim]`. The embedding dimension is the size of the vector representation for each token — typically 768–8192 for modern models. They are independent: a model can have vocab_size=128K and embedding_dim=4096, meaning its embedding matrix is `128K × 4096`. The vocabulary determines coverage (can the model represent all words?), while embedding dimension determines representational capacity.

**Q2: Explain the difference between LoRA rank and alpha.**

Rank (r) controls the size of the LoRA adapter matrices — `A ∈ R^(d×r)` and `B ∈ R^(r×k)`. Higher rank = more trainable parameters = more expressive adapter, but uses more memory and risks overfitting. Alpha is a scaling factor applied to the LoRA output: the final update is `(alpha/r) × AB`. Setting alpha = 2r is a common heuristic. Practically: r controls capacity, alpha controls the magnitude of the adapter's influence on the base model's activations.

**Q3: When would you use the HuggingFace Inference API vs deploying a model locally?**

Inference API when: prototyping quickly, variable/unpredictable load (serverless scales to zero), you don't want to manage GPU infrastructure, the model is too large to run locally. Local deployment when: latency requirements are strict (no network round-trip), data privacy prevents sending data to HF, you need custom generation config or batching control, you're doing high-volume inference where API costs exceed GPU hosting costs, or you need the model available offline. Dedicated Inference Endpoints on HF is the middle ground: managed GPU, your VPC, better latency than serverless.

**Q4: What is QLoRA and why is it important for fine-tuning on limited hardware?**

QLoRA (Quantized LoRA) combines 4-bit quantization of the base model with LoRA adapters. The base model weights are quantized to NF4 (4-bit NormalFloat), reducing memory from ~16 bytes/param (bf16) to ~0.5 bytes. LoRA adapters are trained in bf16 and remain small. During the forward/backward pass, quantized weights are dequantized on-the-fly to bf16. This enables fine-tuning a 70B model on a single A100 (80GB) or a 7B model on a consumer GPU (12GB). Quality loss versus full bf16 fine-tuning is minimal for most tasks.

---

*Next: Module 15 — Open Source LLMs and Serving*
