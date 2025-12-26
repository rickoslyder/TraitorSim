"""HITL WebSocket Server for TraitorSim.

Provides a real-time WebSocket interface for Human-in-the-Loop (HITL) mode,
enabling voice-based interaction between a human player and AI agents.

The server handles:
- WebSocket connection management
- Audio streaming (both directions)
- Game state synchronization
- Session management
- Voice protocol negotiation

Protocol:
    Client sends:
        - Binary: Raw audio chunks (16kHz, 16-bit PCM or opus)
        - JSON: Control messages (join, config, heartbeat)

    Server sends:
        - Binary: Synthesized audio chunks
        - JSON: Game events, state updates, transcripts

Usage:
    from traitorsim.voice import HITLServer

    server = HITLServer(
        host="0.0.0.0",
        port=8765,
        game_engine=engine,
    )
    await server.start()
"""

import asyncio
import json
import logging
import struct
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Set,
    Callable,
    Union,
)
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional websockets import
try:
    import websockets
    from websockets import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any  # Type stub


class MessageType(str, Enum):
    """WebSocket message types."""
    # Client -> Server
    JOIN = "join"                    # Join game session
    LEAVE = "leave"                  # Leave game session
    CONFIG = "config"                # Configure audio settings
    HEARTBEAT = "heartbeat"          # Keep-alive
    TRANSCRIPT = "transcript"        # Manual transcript (text input fallback)

    # Server -> Client
    WELCOME = "welcome"              # Welcome message with session info
    GAME_STATE = "game_state"        # Game state update
    PHASE_CHANGE = "phase_change"    # Game phase changed
    TRANSCRIPT_RESULT = "transcript_result"  # STT transcript
    SPEAKER_START = "speaker_start"  # AI speaker started
    SPEAKER_END = "speaker_end"      # AI speaker ended
    VOTE_RESULT = "vote_result"      # Vote has been recorded
    BANISHMENT = "banishment"        # Player banished
    ERROR = "error"                  # Error message
    GOODBYE = "goodbye"              # Disconnection acknowledgment


class AudioFormat(str, Enum):
    """Supported audio formats."""
    PCM_16K_16BIT = "pcm_16k_16bit"    # Raw PCM, 16kHz, 16-bit mono
    PCM_48K_16BIT = "pcm_48k_16bit"    # Raw PCM, 48kHz, 16-bit mono
    OPUS = "opus"                       # Opus encoded
    MP3 = "mp3"                         # MP3 encoded (output only)


@dataclass
class AudioConfig:
    """Audio configuration for a client session."""
    input_format: AudioFormat = AudioFormat.PCM_16K_16BIT
    output_format: AudioFormat = AudioFormat.MP3
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16


@dataclass
class ClientSession:
    """Represents a connected client session."""
    session_id: str
    websocket: Any  # WebSocketServerProtocol
    player_id: str = ""
    player_name: str = ""
    is_human_player: bool = True
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    audio_config: AudioConfig = field(default_factory=AudioConfig)

    # State
    is_authenticated: bool = False
    current_phase: str = "inactive"

    # Statistics
    bytes_received: int = 0
    bytes_sent: int = 0
    messages_received: int = 0
    messages_sent: int = 0

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def record_received(self, size: int):
        """Record received data."""
        self.bytes_received += size
        self.messages_received += 1
        self.update_activity()

    def record_sent(self, size: int):
        """Record sent data."""
        self.bytes_sent += size
        self.messages_sent += 1


@dataclass
class ServerStats:
    """Server statistics."""
    started_at: datetime = field(default_factory=datetime.now)
    total_connections: int = 0
    active_connections: int = 0
    total_bytes_received: int = 0
    total_bytes_sent: int = 0
    total_messages: int = 0


class HITLServer:
    """WebSocket server for HITL voice interaction.

    Provides real-time voice communication between a human player
    and the AI-driven game. Handles bidirectional audio streaming,
    game state synchronization, and session management.
    """

    # Protocol version
    PROTOCOL_VERSION = "1.0.0"

    # Timeouts
    HEARTBEAT_INTERVAL = 30.0  # seconds
    SESSION_TIMEOUT = 300.0    # 5 minutes of inactivity

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        game_engine: Any = None,
        hitl_handler: Any = None,
        roundtable_orchestrator: Any = None,
        stt_client: Any = None,
        tts_client: Any = None,
        voice_cache: Any = None,
        ssl_context: Any = None,
        max_connections: int = 10,
    ):
        """Initialize HITL server.

        Args:
            host: Server host address
            port: Server port
            game_engine: Game engine instance
            hitl_handler: HITL voice handler
            roundtable_orchestrator: Round Table orchestrator
            stt_client: Deepgram STT client
            tts_client: ElevenLabs TTS client
            voice_cache: Voice cache manager
            ssl_context: SSL context for WSS
            max_connections: Maximum concurrent connections
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets package required. Install with: pip install websockets"
            )

        self.host = host
        self.port = port
        self.engine = game_engine
        self.hitl_handler = hitl_handler
        self.roundtable = roundtable_orchestrator
        self.stt = stt_client
        self.tts = tts_client
        self.voice_cache = voice_cache
        self.ssl_context = ssl_context
        self.max_connections = max_connections

        # Session management
        self._sessions: Dict[str, ClientSession] = {}
        self._websocket_to_session: Dict[Any, str] = {}

        # Server state
        self._server: Any = None
        self._running = False
        self._stats = ServerStats()

        # Event callbacks
        self._on_player_join: Optional[Callable] = None
        self._on_player_leave: Optional[Callable] = None
        self._on_player_speak: Optional[Callable] = None

        # Audio processing
        self._audio_processors: Dict[str, asyncio.Task] = {}

        logger.info(f"HITLServer initialized on {host}:{port}")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    @property
    def active_sessions(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    @property
    def stats(self) -> ServerStats:
        """Get server statistics."""
        return self._stats

    # === Server Lifecycle ===

    async def start(self):
        """Start the WebSocket server."""
        if self._running:
            logger.warning("Server already running")
            return

        logger.info(f"Starting HITL server on ws://{self.host}:{self.port}")

        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ssl=self.ssl_context,
            ping_interval=self.HEARTBEAT_INTERVAL,
            ping_timeout=self.HEARTBEAT_INTERVAL * 2,
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )

        self._running = True
        self._stats.started_at = datetime.now()

        logger.info(f"HITL server started on ws://{self.host}:{self.port}")

        # Start cleanup task
        asyncio.create_task(self._cleanup_stale_sessions())

    async def stop(self):
        """Stop the WebSocket server."""
        if not self._running:
            return

        logger.info("Stopping HITL server...")

        self._running = False

        # Close all sessions
        for session_id in list(self._sessions.keys()):
            await self._close_session(session_id, "Server shutdown")

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("HITL server stopped")

    async def wait_closed(self):
        """Wait for server to close."""
        if self._server:
            await self._server.wait_closed()

    # === Connection Handling ===

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection."""
        session_id = str(uuid.uuid4())

        # Check connection limit
        if len(self._sessions) >= self.max_connections:
            await websocket.close(1013, "Server full")
            return

        # Create session
        session = ClientSession(
            session_id=session_id,
            websocket=websocket,
        )

        self._sessions[session_id] = session
        self._websocket_to_session[websocket] = session_id
        self._stats.total_connections += 1
        self._stats.active_connections += 1

        logger.info(f"New connection: {session_id}")

        try:
            # Send welcome message
            await self._send_welcome(session)

            # Main message loop
            async for message in websocket:
                await self._handle_message(session, message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed: {session_id} - {e.code}")
        except Exception as e:
            logger.error(f"Connection error: {session_id} - {e}")
        finally:
            await self._close_session(session_id, "Connection closed")

    async def _close_session(self, session_id: str, reason: str = ""):
        """Close a client session."""
        session = self._sessions.get(session_id)
        if not session:
            return

        logger.info(f"Closing session: {session_id} - {reason}")

        # Cancel audio processor if running
        if session_id in self._audio_processors:
            self._audio_processors[session_id].cancel()
            del self._audio_processors[session_id]

        # Send goodbye
        try:
            await self._send_message(session, {
                "type": MessageType.GOODBYE.value,
                "reason": reason,
            })
            await session.websocket.close()
        except Exception:
            pass

        # Cleanup
        del self._websocket_to_session[session.websocket]
        del self._sessions[session_id]
        self._stats.active_connections -= 1

        # Callback
        if self._on_player_leave and session.player_id:
            await self._on_player_leave(session.player_id)

    # === Message Handling ===

    async def _handle_message(self, session: ClientSession, message: Union[bytes, str]):
        """Handle an incoming WebSocket message."""
        session.update_activity()

        if isinstance(message, bytes):
            # Binary audio data
            await self._handle_audio(session, message)
        else:
            # JSON control message
            try:
                data = json.loads(message)
                await self._handle_control(session, data)
            except json.JSONDecodeError:
                await self._send_error(session, "Invalid JSON")

    async def _handle_control(self, session: ClientSession, data: Dict[str, Any]):
        """Handle a JSON control message."""
        msg_type = data.get("type", "")
        session.record_received(len(json.dumps(data)))

        handlers = {
            MessageType.JOIN.value: self._handle_join,
            MessageType.LEAVE.value: self._handle_leave,
            MessageType.CONFIG.value: self._handle_config,
            MessageType.HEARTBEAT.value: self._handle_heartbeat,
            MessageType.TRANSCRIPT.value: self._handle_transcript,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(session, data)
        else:
            await self._send_error(session, f"Unknown message type: {msg_type}")

    async def _handle_join(self, session: ClientSession, data: Dict[str, Any]):
        """Handle player join request."""
        player_id = data.get("player_id", "")
        player_name = data.get("player_name", "")
        is_human = data.get("is_human", True)

        if not player_id:
            await self._send_error(session, "player_id required")
            return

        session.player_id = player_id
        session.player_name = player_name
        session.is_human_player = is_human
        session.is_authenticated = True

        logger.info(f"Player joined: {player_name} ({player_id})")

        # Update HITL handler with player info
        if self.hitl_handler:
            self.hitl_handler.session.human_player_id = player_id
            self.hitl_handler.session.human_player_name = player_name

        # Send game state
        await self._send_game_state(session)

        # Callback
        if self._on_player_join:
            await self._on_player_join(player_id, player_name)

    async def _handle_leave(self, session: ClientSession, data: Dict[str, Any]):
        """Handle player leave request."""
        await self._close_session(session.session_id, "Player left")

    async def _handle_config(self, session: ClientSession, data: Dict[str, Any]):
        """Handle audio configuration."""
        audio_config = data.get("audio", {})

        if "input_format" in audio_config:
            try:
                session.audio_config.input_format = AudioFormat(
                    audio_config["input_format"]
                )
            except ValueError:
                pass

        if "output_format" in audio_config:
            try:
                session.audio_config.output_format = AudioFormat(
                    audio_config["output_format"]
                )
            except ValueError:
                pass

        if "sample_rate" in audio_config:
            session.audio_config.sample_rate = int(audio_config["sample_rate"])

        logger.debug(f"Audio config updated: {session.audio_config}")

        await self._send_message(session, {
            "type": "config_ack",
            "audio": {
                "input_format": session.audio_config.input_format.value,
                "output_format": session.audio_config.output_format.value,
                "sample_rate": session.audio_config.sample_rate,
            }
        })

    async def _handle_heartbeat(self, session: ClientSession, data: Dict[str, Any]):
        """Handle heartbeat (keep-alive)."""
        await self._send_message(session, {
            "type": "heartbeat_ack",
            "timestamp": datetime.now().isoformat(),
        })

    async def _handle_transcript(self, session: ClientSession, data: Dict[str, Any]):
        """Handle manual transcript (text input fallback)."""
        text = data.get("text", "").strip()
        if not text:
            return

        await self._process_human_speech(session, text)

    # === Audio Handling ===

    async def _handle_audio(self, session: ClientSession, audio_data: bytes):
        """Handle incoming audio data."""
        session.record_received(len(audio_data))
        self._stats.total_bytes_received += len(audio_data)

        if not self.stt:
            logger.warning("No STT client configured")
            return

        # Start or continue audio processing
        if session.session_id not in self._audio_processors:
            self._audio_processors[session.session_id] = asyncio.create_task(
                self._process_audio_stream(session)
            )

        # Queue audio for processing
        # (In a full implementation, we'd have an audio buffer queue here)

    async def _process_audio_stream(self, session: ClientSession):
        """Process audio stream from client."""
        # This would integrate with Deepgram streaming API
        # For now, this is a placeholder showing the flow

        try:
            # Create audio iterator from buffered chunks
            # audio_stream = self._create_audio_stream(session)

            # Transcribe
            # async for transcript in self.stt.transcribe_stream(audio_stream):
            #     if transcript.is_final:
            #         await self._process_human_speech(session, transcript.text)

            await asyncio.sleep(0)  # Placeholder

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Audio processing error: {e}")

    async def _process_human_speech(self, session: ClientSession, text: str):
        """Process transcribed human speech."""
        logger.info(f"Human speech: {text}")

        # Send transcript to client
        await self._send_message(session, {
            "type": MessageType.TRANSCRIPT_RESULT.value,
            "text": text,
            "is_final": True,
        })

        # Callback
        if self._on_player_speak:
            await self._on_player_speak(session.player_id, text)

        # Route through HITL handler
        if self.hitl_handler:
            try:
                # Process and get response
                async for audio_chunk in self.hitl_handler.process_voice_input(
                    self._create_single_chunk_stream(b"")  # Already transcribed
                ):
                    if audio_chunk:
                        await self._send_audio(session, audio_chunk)
            except Exception as e:
                logger.error(f"HITL handler error: {e}")

        # Update Round Table orchestrator if active
        if self.roundtable and self.roundtable.session:
            self.roundtable.receive_human_input(text)

    async def _create_single_chunk_stream(self, chunk: bytes):
        """Create a single-item async iterator."""
        yield chunk

    async def _send_audio(self, session: ClientSession, audio_data: bytes):
        """Send audio data to client."""
        try:
            await session.websocket.send(audio_data)
            session.record_sent(len(audio_data))
            self._stats.total_bytes_sent += len(audio_data)
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")

    # === Message Sending ===

    async def _send_message(self, session: ClientSession, data: Dict[str, Any]):
        """Send a JSON message to client."""
        try:
            message = json.dumps(data)
            await session.websocket.send(message)
            session.record_sent(len(message))
            self._stats.total_messages += 1
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def _send_welcome(self, session: ClientSession):
        """Send welcome message to new client."""
        await self._send_message(session, {
            "type": MessageType.WELCOME.value,
            "session_id": session.session_id,
            "protocol_version": self.PROTOCOL_VERSION,
            "server_time": datetime.now().isoformat(),
            "audio_formats": {
                "input": [f.value for f in AudioFormat],
                "output": [AudioFormat.MP3.value, AudioFormat.PCM_16K_16BIT.value],
            },
        })

    async def _send_game_state(self, session: ClientSession):
        """Send current game state to client."""
        if not self.engine:
            return

        try:
            state = self.engine.game_state

            await self._send_message(session, {
                "type": MessageType.GAME_STATE.value,
                "day": state.day,
                "phase": state.phase.value if hasattr(state.phase, 'value') else str(state.phase),
                "players": [
                    {
                        "id": p.player_id,
                        "name": p.name,
                        "alive": p.alive,
                    }
                    for p in state.players
                ],
                "pot": state.prize_pot,
            })

            session.current_phase = str(state.phase)

        except Exception as e:
            logger.error(f"Failed to send game state: {e}")

    async def _send_error(self, session: ClientSession, message: str):
        """Send error message to client."""
        await self._send_message(session, {
            "type": MessageType.ERROR.value,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    # === Broadcasting ===

    async def broadcast(self, data: Dict[str, Any], exclude: Set[str] = None):
        """Broadcast message to all connected clients."""
        exclude = exclude or set()

        for session_id, session in self._sessions.items():
            if session_id not in exclude and session.is_authenticated:
                await self._send_message(session, data)

    async def broadcast_phase_change(self, new_phase: str, day: int):
        """Broadcast game phase change."""
        await self.broadcast({
            "type": MessageType.PHASE_CHANGE.value,
            "phase": new_phase,
            "day": day,
            "timestamp": datetime.now().isoformat(),
        })

    async def broadcast_speaker_event(
        self,
        speaker_id: str,
        speaker_name: str,
        event: str,  # "start" or "end"
        text: Optional[str] = None,
    ):
        """Broadcast speaker start/end event."""
        msg_type = (
            MessageType.SPEAKER_START if event == "start"
            else MessageType.SPEAKER_END
        )

        data = {
            "type": msg_type.value,
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "timestamp": datetime.now().isoformat(),
        }

        if text and event == "start":
            data["text"] = text

        await self.broadcast(data)

    async def broadcast_banishment(
        self,
        player_id: str,
        player_name: str,
        role: str,
        votes: Dict[str, str],
    ):
        """Broadcast banishment result."""
        await self.broadcast({
            "type": MessageType.BANISHMENT.value,
            "player_id": player_id,
            "player_name": player_name,
            "role": role,
            "votes": votes,
            "timestamp": datetime.now().isoformat(),
        })

    # === Callbacks ===

    def on_player_join(self, callback: Callable):
        """Register callback for player join."""
        self._on_player_join = callback

    def on_player_leave(self, callback: Callable):
        """Register callback for player leave."""
        self._on_player_leave = callback

    def on_player_speak(self, callback: Callable):
        """Register callback for player speech."""
        self._on_player_speak = callback

    # === Maintenance ===

    async def _cleanup_stale_sessions(self):
        """Periodically clean up stale sessions."""
        while self._running:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.now()
            stale = []

            for session_id, session in self._sessions.items():
                idle_time = (now - session.last_activity).total_seconds()
                if idle_time > self.SESSION_TIMEOUT:
                    stale.append(session_id)

            for session_id in stale:
                logger.info(f"Closing stale session: {session_id}")
                await self._close_session(session_id, "Session timeout")


# === Convenience Functions ===


def create_hitl_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    game_engine: Any = None,
    hitl_handler: Any = None,
    **kwargs,
) -> HITLServer:
    """Create a configured HITL server.

    Args:
        host: Server host
        port: Server port
        game_engine: Game engine instance
        hitl_handler: HITL voice handler
        **kwargs: Additional server options

    Returns:
        Configured HITLServer
    """
    return HITLServer(
        host=host,
        port=port,
        game_engine=game_engine,
        hitl_handler=hitl_handler,
        **kwargs,
    )


async def run_server(
    server: HITLServer,
    shutdown_event: Optional[asyncio.Event] = None,
):
    """Run HITL server until shutdown.

    Args:
        server: HITL server instance
        shutdown_event: Event to signal shutdown
    """
    await server.start()

    try:
        if shutdown_event:
            await shutdown_event.wait()
        else:
            # Run forever
            while server.is_running:
                await asyncio.sleep(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    # Simple test server
    logging.basicConfig(level=logging.INFO)

    async def main():
        server = HITLServer()
        await server.start()
        print(f"HITL server running on ws://{server.host}:{server.port}")
        print("Press Ctrl+C to stop")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await server.stop()

    asyncio.run(main())
