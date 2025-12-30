# Gemini API Integration Guide

A comprehensive reference for integrating Google's Gemini APIs, ADK (Agent Development Kit), and Interactions API. Based on production patterns from TraitorSim.

## Table of Contents

1. [Overview](#overview)
2. [SDK Installation](#sdk-installation)
3. [API Patterns](#api-patterns)
4. [Interactions API (Recommended)](#interactions-api-recommended)
5. [ChatSession API](#chatsession-api)
6. [Deep Research API](#deep-research-api)
7. [File Upload & Grounding](#file-upload--grounding)
8. [Quota Management](#quota-management)
9. [Multi-Key Rotation](#multi-key-rotation)
10. [Error Handling](#error-handling)
11. [Best Practices](#best-practices)

---

## Overview

Google provides multiple APIs for Gemini integration:

| API | Use Case | State Management | Best For |
|-----|----------|------------------|----------|
| **Interactions API** | Conversational AI | Server-side (unlimited) | Long conversations, document grounding |
| **ChatSession API** | Chat applications | Client-side (context window) | Simple chat, quick prototypes |
| **Deep Research** | Background research | Async job-based | Long-running research tasks |
| **ADK** | Agent development | Agent-managed | Complex multi-agent systems |

### Models Available

```python
# Flash models (fast, cost-effective)
"gemini-2.0-flash"           # Current stable
"gemini-2.5-flash"           # Latest flash
"gemini-3-flash-preview"     # Preview (may change - but default to this as it's the latest & greatest Flash model)

# Pro models (higher quality)
"gemini-2.0-pro"
"gemini-2.5-pro"
"gemini-3-pro-preview"     # Preview (may change - but default to this as it's the latest & greatest Pro model)

# Specialized
"deep-research-pro-preview-12-2025"  # Background research agent
```

---

## SDK Installation

```bash
pip install google-genai>=0.3.0    # Interactions API + Deep Research
pip install google-generativeai    # ChatSession API (legacy)
pip install google-adk>=0.1.0      # Agent Development Kit
```

### Environment Variables

```bash
# Primary API key
GEMINI_API_KEY=your_primary_key

# Rotation keys for high-volume (optional)
GEMINI_API_KEY_2=your_second_key
GEMINI_API_KEY_3=your_third_key
GEMINI_API_KEY_4=your_fourth_key
GEMINI_API_KEY_5=your_fifth_key
GEMINI_API_KEY_6=your_sixth_key
```

---

## API Patterns

### Pattern 1: Interactions API (Server-Side State)

```python
from google import genai

class GeminiAgent:
    """Agent using Interactions API with server-side state management."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.interaction_id: str | None = None  # Server manages history

    async def send_message(self, prompt: str) -> str:
        """Send message with automatic history preservation."""
        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt,
            previous_interaction_id=self.interaction_id,  # Chain to previous
            system_instruction=self.system_prompt if not self.interaction_id else None,
        )

        self.interaction_id = interaction.id  # Save for next turn
        return interaction.outputs[-1].text.strip()

    def reset_conversation(self):
        """Start fresh conversation."""
        self.interaction_id = None
```

### Pattern 2: ChatSession API (Client-Side State)

```python
import google.generativeai as genai

class GeminiChat:
    """Chat using ChatSession API with client-side history."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=self.system_prompt,
        )
        self.chat = self.model.start_chat()  # Client maintains history

    async def send_message(self, prompt: str) -> str:
        """Send message - history automatically included."""
        response = await self.chat.send_message_async(prompt)
        return response.text.strip()

    def reset_conversation(self):
        """Start fresh chat session."""
        self.chat = self.model.start_chat()
```

### Pattern 3: Single-Shot (No State)

```python
import google.generativeai as genai

class GeminiOneShot:
    """Stateless single-shot completions."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        """Generate response without conversation history."""
        response = self.model.generate_content(prompt)
        return response.text.strip()
```

---

## Interactions API (Recommended)

The Interactions API is the preferred approach for production systems:

### Advantages

1. **Server-side state** - No context window limits
2. **Document grounding** - Upload files for RAG
3. **Conversation persistence** - Sessions can span days/weeks
4. **Background jobs** - Async processing for long tasks

### Basic Usage

```python
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# First turn - include system instruction
interaction = client.interactions.create(
    model="gemini-2.5-flash",
    input="Hello, how can you help me?",
    system_instruction="You are a helpful assistant.",
)

print(interaction.outputs[-1].text)
interaction_id = interaction.id

# Subsequent turns - chain via previous_interaction_id
interaction = client.interactions.create(
    model="gemini-2.5-flash",
    input="Tell me more about that.",
    previous_interaction_id=interaction_id,  # Links to previous turn
)
```

### Multi-Turn Conversation Class

```python
from google import genai
from dataclasses import dataclass
from typing import Optional

@dataclass
class ConversationState:
    interaction_id: Optional[str] = None
    turn_count: int = 0

class InteractionsAgent:
    """Production-ready agent using Interactions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        system_instruction: str = "",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.system_instruction = system_instruction
        self.state = ConversationState()

    async def chat(self, user_input: str) -> str:
        """Send message and get response."""
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=user_input,
                previous_interaction_id=self.state.interaction_id,
                system_instruction=(
                    self.system_instruction
                    if not self.state.interaction_id
                    else None
                ),
            )

            self.state.interaction_id = interaction.id
            self.state.turn_count += 1

            return interaction.outputs[-1].text.strip()

        except Exception as e:
            print(f"API error: {e}")
            return self._fallback_response(user_input)

    def reset(self):
        """Reset conversation state."""
        self.state = ConversationState()

    def _fallback_response(self, user_input: str) -> str:
        """Graceful fallback when API fails."""
        return "I apologize, but I'm having trouble responding right now."
```

---

## ChatSession API

The legacy ChatSession API maintains history client-side:

```python
import google.generativeai as genai
from typing import Optional

class ChatSessionAgent:
    """Agent using ChatSession with client-side history."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        system_instruction: str = "",
    ):
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction,
        )
        self.chat: Optional[genai.ChatSession] = None
        self._init_chat()

    def _init_chat(self):
        """Initialize or reset chat session."""
        self.chat = self.model_instance.start_chat()

    async def send_async(self, message: str) -> str:
        """Send message asynchronously."""
        if not self.chat:
            self._init_chat()

        response = await self.chat.send_message_async(message)
        return response.text.strip()

    def send_sync(self, message: str) -> str:
        """Send message synchronously."""
        if not self.chat:
            self._init_chat()

        response = self.chat.send_message(message)
        return response.text.strip()

    def get_history(self) -> list:
        """Get conversation history."""
        if self.chat:
            return self.chat.history
        return []

    def reset(self):
        """Reset conversation."""
        self._init_chat()
```

### When to Use ChatSession vs Interactions

| Criteria | ChatSession | Interactions |
|----------|-------------|--------------|
| Conversation length | <100 turns | Unlimited |
| Document grounding | No | Yes |
| State management | Client | Server |
| Background jobs | No | Yes |
| Simplicity | Higher | Lower |
| Cost | Same | Same |

---

## Deep Research API

For long-running research tasks that exceed normal timeout limits:

### Submitting Background Jobs

```python
from google import genai
import asyncio

async def submit_research_job(
    client: genai.Client,
    research_prompt: str,
) -> str:
    """Submit a Deep Research background job."""

    interaction = client.interactions.create(
        agent="deep-research-pro-preview-12-2025",
        input=research_prompt,
        background=True,  # Required - runs asynchronously
        store=True,       # Required for background jobs
    )

    return interaction.id  # Use this to poll for results


async def poll_job_status(
    client: genai.Client,
    job_id: str,
    poll_interval: int = 30,
    timeout: int = 1800,  # 30 minutes
) -> tuple[str, str | None]:
    """Poll job until complete or timeout."""

    elapsed = 0
    while elapsed < timeout:
        interaction = client.interactions.get(job_id)

        status = getattr(interaction, 'status', 'unknown')

        if status == "completed":
            report = interaction.outputs[-1].text
            return ("completed", report)

        elif status in ["failed", "error"]:
            return ("failed", None)

        elif status in ["processing", "pending", "in_progress"]:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        else:
            # Unknown status - keep polling
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    return ("timeout", None)
```

### Complete Deep Research Workflow

```python
from google import genai
from dataclasses import dataclass
from typing import Optional
import asyncio
import os

@dataclass
class ResearchJob:
    job_id: str
    prompt: str
    status: str = "pending"
    result: Optional[str] = None

class DeepResearchManager:
    """Manage Deep Research background jobs."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.jobs: dict[str, ResearchJob] = {}

    async def submit(self, prompt: str) -> str:
        """Submit research job and return job ID."""
        interaction = self.client.interactions.create(
            agent="deep-research-pro-preview-12-2025",
            input=prompt,
            background=True,
            store=True,
        )

        job = ResearchJob(
            job_id=interaction.id,
            prompt=prompt,
            status="submitted",
        )
        self.jobs[interaction.id] = job

        return interaction.id

    async def check_status(self, job_id: str) -> str:
        """Check job status."""
        interaction = self.client.interactions.get(job_id)
        status = getattr(interaction, 'status', 'unknown')

        if job_id in self.jobs:
            self.jobs[job_id].status = status

            if status == "completed":
                self.jobs[job_id].result = interaction.outputs[-1].text

        return status

    async def get_result(self, job_id: str) -> Optional[str]:
        """Get result if job is complete."""
        if job_id in self.jobs and self.jobs[job_id].result:
            return self.jobs[job_id].result

        await self.check_status(job_id)
        return self.jobs.get(job_id, ResearchJob("", "")).result

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 30,
        timeout: int = 1800,
    ) -> Optional[str]:
        """Wait for job completion with polling."""
        elapsed = 0

        while elapsed < timeout:
            status = await self.check_status(job_id)

            if status == "completed":
                return self.jobs[job_id].result
            elif status in ["failed", "error"]:
                return None

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return None  # Timeout
```

---

## File Upload & Grounding

Upload documents to ground the model's responses:

### Uploading Files

```python
from google import genai
from pathlib import Path

def upload_document(
    client: genai.Client,
    file_path: str | Path,
) -> str:
    """Upload document and return file URI."""

    path = Path(file_path)

    # Determine MIME type
    mime_types = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".json": "application/json",
    }
    mime_type = mime_types.get(path.suffix, "text/plain")

    uploaded = client.files.upload(
        file=str(path),
        config={"mime_type": mime_type},
    )

    return uploaded.uri
```

### Using Documents in Conversations

```python
class GroundedAgent:
    """Agent grounded in uploaded documents."""

    def __init__(
        self,
        api_key: str,
        document_path: str,
        model: str = "gemini-2.5-flash",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.interaction_id: str | None = None

        # Upload grounding document
        self.document_uri = upload_document(self.client, document_path)

    async def chat(self, user_input: str) -> str:
        """Chat with document-grounded context."""

        # First turn: include document
        if not self.interaction_id:
            input_content = [
                {"type": "document", "uri": self.document_uri},
                {"type": "text", "text": user_input},
            ]
        else:
            input_content = user_input

        interaction = self.client.interactions.create(
            model=self.model,
            input=input_content,
            previous_interaction_id=self.interaction_id,
            system_instruction=(
                "Use the provided document as your knowledge base. "
                "Always cite relevant sections when answering."
            ) if not self.interaction_id else None,
        )

        self.interaction_id = interaction.id
        return interaction.outputs[-1].text.strip()
```

---

## Quota Management

### API Key Rotation for High Volume

```python
from dataclasses import dataclass, field
from typing import Optional
import os

@dataclass
class APIKeyManager:
    """Rotate between multiple API keys for quota management."""

    keys: list[str] = field(default_factory=list)
    usage_counts: dict[str, int] = field(default_factory=dict)
    current_index: int = 0
    jobs_per_key_limit: int = 12  # Conservative per-key limit

    @classmethod
    def from_environment(cls, key_prefix: str = "GEMINI_API_KEY") -> "APIKeyManager":
        """Load keys from environment variables."""
        keys = []

        # Primary key
        primary = os.getenv(key_prefix)
        if primary:
            keys.append(primary)

        # Numbered keys (KEY_2 through KEY_10)
        for i in range(2, 11):
            key = os.getenv(f"{key_prefix}_{i}")
            if key:
                keys.append(key)

        manager = cls(keys=keys)
        manager.usage_counts = {k: 0 for k in keys}
        return manager

    def get_next_key(self) -> str:
        """Get next key in rotation."""
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

    def get_key_with_capacity(self) -> Optional[str]:
        """Get a key that hasn't exceeded its limit."""
        for _ in range(len(self.keys)):
            key = self.get_next_key()
            if self.usage_counts[key] < self.jobs_per_key_limit:
                return key
        return None  # All keys exhausted

    def record_usage(self, key: str):
        """Record that a key was used."""
        self.usage_counts[key] = self.usage_counts.get(key, 0) + 1

    def mark_exhausted(self, key: str):
        """Mark a key as exhausted (hit quota)."""
        self.usage_counts[key] = self.jobs_per_key_limit

    def get_total_capacity(self) -> int:
        """Get remaining capacity across all keys."""
        return sum(
            max(0, self.jobs_per_key_limit - count)
            for count in self.usage_counts.values()
        )

    def reset(self):
        """Reset usage counts."""
        self.usage_counts = {k: 0 for k in self.keys}
        self.current_index = 0
```

### Rate-Limited Client

```python
from google import genai
import asyncio
import time

class RateLimitedClient:
    """Gemini client with rate limiting and key rotation."""

    def __init__(
        self,
        key_manager: APIKeyManager,
        requests_per_minute: int = 10,
    ):
        self.key_manager = key_manager
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0
        self._clients: dict[str, genai.Client] = {}

    def _get_client(self, api_key: str) -> genai.Client:
        """Get or create client for API key."""
        if api_key not in self._clients:
            self._clients[api_key] = genai.Client(api_key=api_key)
        return self._clients[api_key]

    async def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    async def create_interaction(self, **kwargs) -> any:
        """Create interaction with rate limiting and key rotation."""
        api_key = self.key_manager.get_key_with_capacity()

        if not api_key:
            raise Exception("All API keys exhausted")

        await self._wait_for_rate_limit()

        client = self._get_client(api_key)

        try:
            interaction = client.interactions.create(**kwargs)
            self.key_manager.record_usage(api_key)
            return interaction

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate" in error_msg:
                self.key_manager.mark_exhausted(api_key)
                # Retry with different key
                return await self.create_interaction(**kwargs)
            raise
```

---

## Multi-Key Rotation

### Batch Processing with Multiple Keys

```python
from google import genai
from dataclasses import dataclass
from typing import Optional
import asyncio
import os

@dataclass
class BatchJob:
    id: str
    prompt: str
    api_key_index: int
    status: str = "pending"
    result: Optional[str] = None

class BatchProcessor:
    """Process multiple jobs with key rotation."""

    def __init__(self, rate_limit_seconds: float = 6.0):
        self.key_manager = APIKeyManager.from_environment()
        self.rate_limit = rate_limit_seconds
        self.jobs: list[BatchJob] = []

    async def submit_batch(self, prompts: list[str]) -> list[str]:
        """Submit batch of prompts, return job IDs."""
        job_ids = []

        for i, prompt in enumerate(prompts):
            api_key = self.key_manager.get_key_with_capacity()

            if not api_key:
                print(f"Capacity exhausted after {i} jobs")
                break

            # Rate limiting
            if i > 0:
                await asyncio.sleep(self.rate_limit)

            client = genai.Client(api_key=api_key)

            try:
                interaction = client.interactions.create(
                    agent="deep-research-pro-preview-12-2025",
                    input=prompt,
                    background=True,
                    store=True,
                )

                key_index = self.key_manager.keys.index(api_key) + 1
                job = BatchJob(
                    id=interaction.id,
                    prompt=prompt,
                    api_key_index=key_index,
                )
                self.jobs.append(job)
                job_ids.append(interaction.id)

                self.key_manager.record_usage(api_key)
                print(f"Submitted job {i+1}/{len(prompts)} with KEY_{key_index}")

            except Exception as e:
                if "quota" in str(e).lower():
                    self.key_manager.mark_exhausted(api_key)
                    print(f"Quota exceeded on KEY_{key_index}, rotating...")
                else:
                    raise

        return job_ids

    async def poll_all(
        self,
        poll_interval: int = 30,
        timeout: int = 1800,
    ) -> dict[str, str]:
        """Poll all jobs until complete or timeout."""
        results = {}
        pending = set(job.id for job in self.jobs)
        elapsed = 0

        while pending and elapsed < timeout:
            for job in self.jobs:
                if job.id not in pending:
                    continue

                # Use the same key that submitted the job
                api_key = self.key_manager.keys[job.api_key_index - 1]
                client = genai.Client(api_key=api_key)

                try:
                    interaction = client.interactions.get(job.id)
                    status = getattr(interaction, 'status', 'unknown')

                    if status == "completed":
                        job.status = "completed"
                        job.result = interaction.outputs[-1].text
                        results[job.id] = job.result
                        pending.remove(job.id)

                    elif status in ["failed", "error"]:
                        job.status = "failed"
                        pending.remove(job.id)

                except Exception as e:
                    print(f"Poll error for {job.id}: {e}")

            if pending:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                print(f"Polling... {len(pending)} jobs remaining")

        return results
```

---

## Error Handling

### Graceful Fallbacks

```python
class ResilientAgent:
    """Agent with comprehensive error handling."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.interaction_id: str | None = None
        self.fallback_enabled = True

    async def chat(self, user_input: str) -> str:
        """Chat with fallback handling."""

        # Check if API is available
        if not self.client:
            return self._fallback_response(user_input)

        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=user_input,
                previous_interaction_id=self.interaction_id,
            )

            self.interaction_id = interaction.id
            response = interaction.outputs[-1].text.strip()

            # Validate response
            if not response:
                return self._fallback_response(user_input)

            return response

        except Exception as e:
            return self._handle_error(e, user_input)

    def _handle_error(self, error: Exception, user_input: str) -> str:
        """Handle specific error types."""
        error_msg = str(error).lower()

        if "quota" in error_msg or "rate" in error_msg:
            print(f"Rate limit hit: {error}")
            return "I'm currently experiencing high demand. Please try again shortly."

        elif "invalid" in error_msg or "auth" in error_msg:
            print(f"Authentication error: {error}")
            return "There's a configuration issue. Please contact support."

        elif "timeout" in error_msg:
            print(f"Timeout error: {error}")
            return "The request timed out. Please try a shorter message."

        else:
            print(f"Unexpected error: {error}")
            return self._fallback_response(user_input)

    def _fallback_response(self, user_input: str) -> str:
        """Generate fallback response without API."""
        if not self.fallback_enabled:
            return "Service temporarily unavailable."

        # Simple rule-based fallback
        if "hello" in user_input.lower():
            return "Hello! How can I help you today?"
        elif "?" in user_input:
            return "That's an interesting question. Let me think about that."
        else:
            return "I understand. Please continue."
```

---

## Best Practices

### 1. Always Use Fallbacks

```python
# Bad - crashes on API failure
response = client.interactions.create(...)

# Good - graceful degradation
try:
    response = client.interactions.create(...)
except Exception as e:
    response = fallback_handler(e)
```

### 2. Chain Interactions Properly

```python
# Bad - loses conversation context
interaction = client.interactions.create(model=model, input=prompt)

# Good - maintains conversation history
interaction = client.interactions.create(
    model=model,
    input=prompt,
    previous_interaction_id=self.interaction_id,  # Link to previous
    system_instruction=system_prompt if not self.interaction_id else None,
)
self.interaction_id = interaction.id  # Save for next turn
```

### 3. Use Async for Production

```python
# Bad - blocks event loop
response = client.interactions.create(...)

# Good - non-blocking
response = await asyncio.to_thread(
    client.interactions.create,
    model=model,
    input=prompt,
)
```

### 4. Implement Rate Limiting

```python
# Bad - hammers API
for prompt in prompts:
    client.interactions.create(input=prompt)

# Good - respects rate limits
for i, prompt in enumerate(prompts):
    if i > 0:
        await asyncio.sleep(6)  # 10 requests/minute
    client.interactions.create(input=prompt)
```

### 5. Track Costs

```python
# Approximate token costs
COST_PER_1K_INPUT = 0.00025   # $0.25 per 1M input tokens (Flash)
COST_PER_1K_OUTPUT = 0.00075  # $0.75 per 1M output tokens (Flash)

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000 * COST_PER_1K_INPUT +
            output_tokens / 1000 * COST_PER_1K_OUTPUT)
```

### 6. Validate Responses

```python
def validate_response(response: str) -> bool:
    """Ensure response is usable."""
    if not response:
        return False
    if len(response) < 10:
        return False
    if response.startswith("Error:"):
        return False
    return True
```

---

## Configuration Reference

### Complete Configuration Class

```python
from dataclasses import dataclass, field
from typing import Optional
import os

@dataclass
class GeminiConfig:
    """Complete Gemini integration configuration."""

    # API Keys
    api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )

    # Model selection
    model: str = "gemini-2.5-flash"
    research_model: str = "deep-research-pro-preview-12-2025"

    # Rate limiting
    requests_per_minute: int = 10
    jobs_per_key_limit: int = 12

    # Timeouts
    request_timeout_seconds: int = 30
    research_timeout_seconds: int = 1800
    poll_interval_seconds: int = 30

    # Features
    enable_fallbacks: bool = True
    enable_key_rotation: bool = True
    enable_document_grounding: bool = False

    # Paths
    grounding_document_path: Optional[str] = None

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        return True
```

---

## Quick Reference

### Import Patterns

```python
# Interactions API (recommended)
from google import genai
client = genai.Client(api_key=key)
interaction = client.interactions.create(...)

# ChatSession API (legacy)
import google.generativeai as genai
genai.configure(api_key=key)
model = genai.GenerativeModel(model_name)
chat = model.start_chat()
response = chat.send_message(...)

# File uploads
uploaded = client.files.upload(file=path, config={"mime_type": mime})
```

### Key Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `model` | Model to use | `"gemini-3-flash-preview"` |
| `input` | User message | `"Hello"` or `[{type, ...}]` |
| `system_instruction` | System prompt | `"You are helpful..."` |
| `previous_interaction_id` | Chain conversations | `interaction.id` |
| `background` | Async job | `True` for Deep Research |
| `store` | Persist job | Required with `background` |

---

## See Also

- [Google AI Python SDK](https://github.com/google/generative-ai-python)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [ADK Documentation](https://google.github.io/adk-docs/)
