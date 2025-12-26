"""Example usage of Deepgram STT client for TraitorSim HITL mode.

Demonstrates:
1. Dry-run mode (no API calls)
2. Batch transcription
3. Streaming transcription
4. Voice Activity Detection (VAD)
5. Usage stats tracking
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.voice import (
    DeepgramClient,
    DeepgramModel,
    DeepgramConfig,
    create_deepgram_client,
    quick_transcribe,
)


async def demo_batch_transcription():
    """Demo batch transcription with dry-run mode."""
    print("\n=== Batch Transcription Demo ===\n")

    # Create client in dry-run mode
    client = create_deepgram_client(dry_run=True)

    # Simulate audio data (in real use, this would be actual audio bytes)
    mock_audio = b"\x00" * 32000  # 1 second of silence at 16kHz

    # Configure transcription
    config = DeepgramConfig(
        model=DeepgramModel.NOVA_3,
        language="en",
        punctuate=True,
        smart_format=True,
    )

    # Transcribe
    result = await client.transcribe_audio(mock_audio, config)

    print(f"Transcript: {result.text}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Duration: {result.end_time - result.start_time:.2f}s")
    print(f"Words: {len(result.words)}")
    print(f"Is final: {result.is_final}")
    print(f"Dry run: {result.is_dry_run}")

    # Show usage stats
    print("\n--- Usage Stats ---")
    stats = client.get_usage_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Total audio: {stats['total_audio_duration_s']:.2f}s")
    print(f"Estimated cost: ${stats['estimated_cost_usd']['pay_as_you_go']:.4f}")

    await client.close()


async def demo_streaming_transcription():
    """Demo streaming transcription with interim results."""
    print("\n=== Streaming Transcription Demo ===\n")

    client = create_deepgram_client(dry_run=True)

    # Simulate streaming audio
    async def mock_audio_stream():
        """Generate mock audio chunks."""
        for i in range(10):
            # 200ms chunks at 16kHz
            chunk = b"\x00" * 3200
            yield chunk
            await asyncio.sleep(0.05)  # Simulate real-time streaming

    # Configure for streaming
    config = DeepgramConfig(
        model=DeepgramModel.NOVA_3,
        language="en",
        interim_results=True,  # Get partial results
        utterance_end_ms=1000,  # Trigger final after 1s silence
    )

    # Stream transcription
    transcript_count = 0
    async for result in client.transcribe_stream(mock_audio_stream(), config):
        transcript_count += 1
        status = "FINAL" if result.is_final else "interim"
        print(f"[{status}] {result.text} (confidence: {result.confidence:.2f})")

        if transcript_count >= 5:  # Limit for demo
            break

    # Show stats
    print("\n--- Usage Stats ---")
    stats = client.get_usage_stats()
    print(f"Final transcripts: {stats['final_transcripts']}")
    print(f"Interim transcripts: {stats['interim_transcripts']}")

    await client.close()


async def demo_voice_activity_detection():
    """Demo Voice Activity Detection (VAD)."""
    print("\n=== Voice Activity Detection Demo ===\n")

    client = create_deepgram_client(dry_run=True)

    # Simulate different audio samples
    silence = b"\x00" * 16000  # 1s of silence
    noise = bytes([i % 256 for i in range(16000)])  # 1s of noise

    # Test VAD on silence
    vad_silence = client.detect_voice_activity(silence, sample_rate=16000, threshold=0.01)
    print(f"Silence - Is speech: {vad_silence.is_speech}, "
          f"Energy: {vad_silence.energy:.4f}, "
          f"Confidence: {vad_silence.confidence:.2f}")

    # Test VAD on noise
    vad_noise = client.detect_voice_activity(noise, sample_rate=16000, threshold=0.01)
    print(f"Noise - Is speech: {vad_noise.is_speech}, "
          f"Energy: {vad_noise.energy:.4f}, "
          f"Confidence: {vad_noise.confidence:.2f}")

    await client.close()


async def demo_quick_transcribe():
    """Demo quick one-off transcription helper."""
    print("\n=== Quick Transcribe Demo ===\n")

    # Simulate audio
    mock_audio = b"\x00" * 32000

    # Quick transcribe (creates and closes client automatically)
    transcript = await quick_transcribe(
        mock_audio,
        model=DeepgramModel.NOVA_3,
        language="en",
    )

    print(f"Transcript: {transcript}")


async def demo_speaker_diarization():
    """Demo speaker diarization for multi-speaker scenarios."""
    print("\n=== Speaker Diarization Demo ===\n")

    client = create_deepgram_client(dry_run=True)

    # Configure with diarization
    config = DeepgramConfig(
        model=DeepgramModel.NOVA_3,
        language="en",
        diarize=True,  # Enable speaker diarization
        punctuate=True,
    )

    mock_audio = b"\x00" * 64000  # 2 seconds

    result = await client.transcribe_audio(mock_audio, config)

    print(f"Transcript: {result.text}")
    print("\nWord-level speaker info:")
    for word in result.words[:5]:  # Show first 5 words
        speaker = f"Speaker {word.speaker}" if word.speaker is not None else "Unknown"
        print(f"  {word.word} ({word.start:.2f}s - {word.end:.2f}s) - {speaker}")

    await client.close()


async def main():
    """Run all demos."""
    print("=" * 60)
    print("Deepgram STT Client Demo for TraitorSim HITL Mode")
    print("=" * 60)

    await demo_batch_transcription()
    await demo_streaming_transcription()
    await demo_voice_activity_detection()
    await demo_quick_transcribe()
    await demo_speaker_diarization()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
