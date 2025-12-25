# Human-in-the-Loop (HITL) Voice Interfaces for Games: Research Report

**Date:** December 23, 2025
**Focus:** Practical implementation patterns, latency constraints, and accessibility considerations

---

## Executive Summary

Human-in-the-Loop voice interfaces for games represent a rapidly evolving technology with stringent latency requirements and complex architectural challenges. As of 2025, achieving conversational-quality voice AI requires end-to-end latency under 500ms, with the ideal target being 200-300ms to match human conversational patterns. This report synthesizes current best practices, technical implementations, real-world examples, and accessibility requirements for integrating voice AI into gaming experiences.

---

## 1. Real-Time Voice Synthesis for NPCs

### 1.1 Latency Requirements

**Target Benchmarks:**
- **Sub-500ms to first sound** - Industry standard for conversational AI in games
- **Under 100ms for ultra-fast TTS** - State-of-the-art APIs (2025)
- **200-300ms total latency** - Ideal target matching human turn-taking in conversation
- **~500ms end-to-end** - Achievable through parallel processing architecture

**Specific Performance Levels:**
- Chatterbox: <200ms inference latency
- XTTS-v2: <150ms streaming latency on consumer GPU
- Fast speech synthesizers: ~200ms for high-quality audio
- OpenAI Whisper: 519ms/712ms
- ElevenLabs: 350ms (US) to 527ms (India)

**Critical Constraint:** Multi-second delays between player questions and NPC responses are a major deployment barrier in current games. Cloud-based NLG and TTS services integrated via API create unacceptable lag.

### 1.2 Solutions for Low-Latency Gaming

**TTS Game Engine Plugins:**
- Direct integration into game engines (Unity, Unreal)
- On-device audio generation eliminates network latency
- Dynamic TTS at runtime for procedurally generated dialogue
- Instant audio playback without cloud round-trips

**Parallel Processing Architecture:**
- Handle transcription, response generation, and speech synthesis concurrently
- Start TTS before LLM sentence completion
- Pre-warm TTS pipeline during ASR processing
- Stream ASR with partials and strong endpointing

**Transport Layer Optimization:**
- WebRTC: Sub-second round-trips for interactive dialogue
- WebSockets: Acceptable for slightly higher latency tolerance
- UDP prioritization over TCP (up to 50% latency reduction)

### 1.3 Production-Ready TTS Solutions

**ElevenLabs:**
- Gold standard for English voice cloning quality
- Voices "virtually indistinguishable from real voices"
- Strong accent and emotion capture
- Easy API integration
- Latency: 350-527ms depending on region

**Fish Audio:**
- Emotion control at word level
- <500ms latency suitable for interactive dialogue
- Consistent character voices across emotional ranges
- Good for dynamic NPC systems

**Hume AI (Octave):**
- Generate voices from prompt or brief recording
- Emulate gender, age, accent, vocal register, emotional intonation
- Advanced emotional range capabilities
- Suitable for procedural character generation

**Neuphonic (NeuTTS Air):**
- 748M-parameter on-device model
- Real-time on mid-tier CPU (no GPU required)
- Instant voice cloning from 3-second samples
- 24kHz output quality
- Privacy-focused (no cloud required)

---

## 2. Speech-to-Text for Player Input

### 2.1 Latency Benchmarks

**Industry Standards:**
- **<100ms ideal** - Optimal real-time STT performance
- **Few hundred milliseconds** - Maximum acceptable for real-time systems
- **Real-time processing** - Streaming architecture required

**Provider Performance:**
- Deepgram: Industry-leading low latency
- AssemblyAI, Groq, FireworksAI: Strong emphasis on speed
- Deepgram Nova-3: $0.0077/min vs AWS Transcribe $0.024/min (3.1x cheaper)

### 2.2 Latency Factors

**Network Infrastructure:**
- Bluetooth: +150-250ms latency
- Distant cloud data centers: +100-300ms latency
- Local/edge processing: Eliminates network variable

**Processing Pipeline:**
- LLM typically primary latency source (700-1000ms for GPT-4/Claude)
- Gemini Flash 1.5: <350ms (fastest production LLM)
- STT + LLM + TTS combined affects overall responsiveness

**Model Characteristics:**
- Smaller 10ms frames: Faster onset detection, more false positives in noise
- Larger 30ms windows: Better accuracy, higher detection delay
- Real-time vs offline: Streaming required for interactive applications

### 2.3 Voice Activity Detection (VAD)

**Purpose:**
- Detect presence/absence of human speech
- Enable turn-taking in conversational AI
- Reduce unnecessary processing and network bandwidth

**Production Solutions:**

**Picovoice Cobra:**
- 2x accuracy of WebRTC VAD
- Lightweight, cross-platform
- Real-time speech identification

**Silero VAD:**
- <1ms per 30ms audio chunk on single CPU thread
- Trained on 6000+ languages
- Excellent performance across noise levels and quality

**OpenAI Realtime API VAD:**
- Automatic start/stop detection
- Configurable threshold (0-1 scale)
- Adjustable silence duration (faster turn detection with lower values)
- Prefix padding for context preservation

**Key Tradeoffs:**
- Accuracy vs Latency: Balance detection speed with classification precision
- Fixed latency ranges: Milliseconds to seconds depending on implementation
- Environment adaptation: Higher thresholds for noisy environments

---

## 3. Conversational AI Latency Requirements

### 3.1 Human Conversational Benchmarks

**Ideal Targets:**
- **200ms turn-taking delay** - Human conversational standard
- **~500ms response rhythm** - Natural dialogue flow
- **Beyond 500ms** - Users perceive system as unresponsive

**Industry Implementation:**
- Twilio ConversationRelay: <500ms median, <725ms p95
- Vapi voice agents: ~465ms end-to-end
- Real-time voice chat: ~500ms with local models + streaming

### 3.2 Gaming-Specific Requirements

**Immersion Factors:**
- Voice chat with minimal AI latency maintains immersion
- Competitive gameplay demands near-instant responses
- NPCs must feel responsive to maintain player engagement

**Critical Metric:**
- **Time to First Audio (TTFA)** - How long until agent starts speaking after player finishes
- More important than total response completion time
- First tokens set user perception of responsiveness

### 3.3 Optimization Strategies

**Component Selection:**
- LLM choice critical: 350ms (Gemini Flash) vs 700-1000ms (GPT-4/Claude)
- Lightweight models for immediate responses
- Reserve larger models for deep reasoning after interaction

**Caching and Streaming:**
- Pre-compute frequent phrases (greetings, confirmations)
- Zero playback latency for cached content
- Stream audio playback as soon as first tokens arrive

**Infrastructure Optimization:**
- Dedicated processors (Groq LPUs) for faster inference
- Edge computing near players reduces network travel time
- Hybrid architectures: Fast models for conversation, slow models for analysis

**Parallel Processing:**
- Simultaneous STT, LLM, and TTS operations
- Start TTS before LLM completes full response
- Sentence streaming: Segment LLM output in real-time

### 3.4 Future Outlook

By late 2025/2026, voice AI latency expected to drop below 100ms, making conversations "not just instant, but intuitively human."

---

## 4. Games with Voice-Based AI Interaction

### 4.1 Major AAA Integrations

**PUBG (Krafton + Nvidia ACE):**
- AI-controlled squadmates respond to voice commands
- Realistic tactical assistance (item search, covering fire, spotting)
- Dynamic execution of maneuvers
- Uses Nvidia's Avatar Cloud Engine (ACE)

**inZOI (Krafton):**
- Sims-like life simulation with "Smart ZOIs"
- AI characters react dynamically to player actions
- Spontaneous interactions within virtual world
- Leverages Nvidia ACE technology

**Sony Horizon AI Prototype:**
- AI-powered Aloy from Horizon games
- OpenAI Whisper for speech-to-text
- GPT-4 and Llama 3 for conversation
- Sony Mockingbird and Emotional Voice Synthesis (EVS)
- Responds organically to unscripted prompts

**Cyberpunk 2077: Phantom Liberty:**
- Respeecher used to preserve Viktor Vektor's voice
- Demonstrates voice consistency for DLC content
- Addresses actor availability challenges

### 4.2 Experimental Projects and Mods

**Ubisoft NEO NPCs:**
- LLM-powered background characters
- Writer-created personalities with AI improvisation
- Guardrail systems for behavior control
- Player input analysis and 3D environment awareness

**Skyrim AI Mod (Bloc):**
- Voice-to-voice NPC conversations
- Generative AI transforms vanilla NPCs
- Unscripted dialogue system

**Mount & Blade 2: Bannerlord AI Mod (Bloc):**
- Microphone input for NPC conversations
- Any NPC can engage in dynamic dialogue

**Replica Studios Matrix Awakens Demo:**
- Modified Matrix Awakens with microphone input
- ChatGPT + text-to-speech for street NPCs
- Demonstrates immersive potential of voice AI

**AI Wonderland (Roblox):**
- Generative AI characters
- Voice interaction for mystery solving

### 4.3 Industry Trends and Adoption

**Market Growth:**
- $3.1 billion AI revenue boost to gaming (2024)
- 70% of developers view AI as essential for next-gen games
- 78% of players couldn't distinguish AI voices in 2025 Steam survey (Starforge Saga)
- Over 60% of indie developers use AI voice tools (cost reduction + speed)

**Platform Partnerships:**
- Niantic Spatial + Hume AI: Interactive spatial AI companions
- Game developers increasingly adopt conversational AI for immersion

---

## 5. Mixing Human and AI Voices in Multiplayer

### 5.1 Voice Quality and Consistency Requirements

**Gaming-Specific Demands:**
- **Consistency across thousands of lines** - Voice can't drift over time
- **Emotional range** - Combat barks, calm dialogue, panic, sarcasm
- **Low latency** - Delay breaks immersion for interactive dialogue
- **Scalability** - Generate many lines without manual regeneration

**Challenge:** Perfect consistency without emotional variation feels inauthentic. Solution is layering emotional intent on top of cloned voice base.

### 5.2 Best Practices for AI Voice Implementation

**Source Audio Quality:**
- Record clean audio: single speaker, minimal noise, stable volume
- Short clips work well if controlled
- Consistent recording environment critical

**Emotional Range Design:**
- Define character emotional palette upfront
- Limit extremes to maintain believability
- Design ranges per character archetype
- Spot-check regularly to catch drift

**Hybrid Human-AI Workflow:**
- Record key scenes in studio
- Fill secondary/procedural content with AI
- Use AI for rapid prototyping before final voice actor sessions
- "We use Replica's software to test scripts, dialogue, and gameplay sequences before engaging human voice actors" - PlaySide Studios

### 5.3 Multiplayer Integration Patterns

**Audio Middleware:**
- FMOD, Wwise, Fabric for real-time audio management
- Dynamic mixing, adaptive music, spatialization
- Interactive sound effects integration

**Real-Time Voice Modulation:**
- Choose reliable software with low latency
- Optimize for performance in multiplayer contexts
- Prioritize user feedback for adjustments
- Gaming TTS supports real-time voice modification

**Hardware Mixing Solutions:**
- Dedicated gaming mixers for multiple audio feeds
- Balance game sound, player mic, teammate voices
- Physical controls (knobs/faders) for quick adjustment

**Communication System Design:**
- Mix AI NPC voices with human player voice chat
- Maintain clear distinction between AI and human speakers
- Volume balancing critical for intelligibility
- Consider spatial audio for source identification

### 5.4 Production Workflows

**Ubisoft Approach (NEO NPCs):**
1. Writer creates personality, backstory, conversation style
2. Data scientist teaches model to behave like writer's creation
3. Guardrail systems constrain AI behavior
4. Human actors provide expressive performance capture
5. AI improvises within writer-defined constraints

**Hybrid Development Models:**
- Important story beats: Pre-generated, stored locally
- Side dialogues/sandbox: Real-time cloud generation
- Ensures performance without sacrificing depth
- AAA studios: LLMs handle repetitive interactions, writers focus on plot

**Rapid Prototyping Infrastructure:**
- AI voice for early dialogue testing
- Iterate on scripts before hiring voice actors
- Reduce time and cost of foundation model development
- Codified deployment pipelines (CDK applications)

---

## 6. Accessibility Considerations

### 6.1 Scale of Impact

**Demographics:**
- ~15% of 1.9 billion global gamers are deaf or hard of hearing
- Approximately 300 million deaf and hard-of-hearing gamers worldwide
- Significant market and ethical imperative

### 6.2 Voice Chat Accessibility Challenges

**Primary Issue:**
- Games relying heavily on voice chat exclude deaf/HoH players from start
- Multiplayer communication creates accessibility barriers
- Fast-paced games with voice-only communication problematic

### 6.3 Solutions and Technologies

**Speech-to-Text Transcription:**
- Microsoft Game Chat Transcription enables team participation
- EA uses speech-to-text in multiplayer games
- Transcribe voice communication to written format
- Critical for inclusive team-based gameplay

**Alternative Communication Systems:**

**Text Chat:**
- "Archaic" but invaluable for hearing-impaired gamers
- Should be offered alongside voice options
- Provides asynchronous communication path

**Ping Systems:**
- Apex Legends: Robust ping system for communication without voice
- Callouts for teammates without speech required
- Faster and clearer than words for many situations
- EA's patent pledge makes system free for any studio
- Communicate complex info (objects, locations, threats) quickly

**Text-to-Speech (TTS):**
- Convert text chat to speech for hearing players
- Bridge communication gap between deaf/HoH and hearing players
- Enable real-time conversation without typing dependency

### 6.4 Visual Audio Representation

**Fortnite Visual Sound Effects:**
- Revolutionary visualization for all sound effects
- Colored indicators for treasure chests, gliders, gunshots, footsteps
- Directional and distance information conveyed visually
- Industry-leading example of audio accessibility

**General Principles:**
- Visualize sound effects for deaf/HoH players
- Include not just what sound occurred, but direction and distance
- Consider colorblind-friendly indicator systems

### 6.5 Best Practices for Developers

**Multi-Modal Communication:**
- Integrated ping system required
- Voice chat transcriptions (STT)
- Text chat system for barriers/noise/language issues
- Speech-to-text AND text-to-speech options

**Audio Alternatives:**
- Visual sound effect indicators
- Directional cues on screen
- Distance/proximity information
- Subtitle/caption system for all audio

**WHO/ITU Global Standards (February 2025):**
- Safe listening warnings
- Independent volume controls
- Headphone safety modes with automatic adjustment
- Applies to video gameplay and esports

### 6.6 Accessibility Benefits Beyond Disability

**Universal Design:**
- Language barriers: Text chat + translation
- Noisy environments: Visual/text alternatives
- Quiet environments: Text chat instead of voice
- Skill/preference variation: Multiple communication options

---

## 7. Technical Implementation Patterns

### 7.1 WebRTC Voice Streaming

**Protocol Advantages:**
- UDP + RTP for sub-second latency
- 50% latency reduction vs TCP under ideal conditions
- Native browser support for real-time communication

**Optimization Techniques:**

**Network Layer:**
- Quality of Service (QoS) for traffic prioritization
- Prioritize voice/game state over less critical transmissions
- Up to 50% performance boost with proper QoS

**Codec Selection:**
- Opus codec optimized for low-latency
- Excellent clarity despite high compression
- VP8, VP9, H.264 for video with hardware acceleration

**Error Correction:**
- Forward Error Correction (FEC) for packet loss recovery
- Redundancy in critical data transmission
- >5% packet loss causes 30% increase in dropout rates

**Latency Targets:**
- <100ms critical for competitive gaming player satisfaction
- Sub-500ms for conversational AI
- 200-300ms ideal for natural interaction

### 7.2 Edge Computing and On-Device Processing

**Benefits:**
- **Faster responses** - No cloud round-trip delay
- **Lower bandwidth** - Processing happens locally
- **Enhanced privacy** - Sensitive data never transmitted
- **Offline capability** - No cloud dependency
- **Cost reduction** - Eliminate per-request API fees at scale

**Edge Voice AI Model Characteristics:**
- Local processing for privacy
- Low latency (near-instant response)
- Resource efficient (strict memory/power budgets)
- Scalable (no exponential infrastructure costs)

**Available Frameworks:**
- TensorFlow Lite: Cross-platform model deployment
- Edge Impulse: Embedded ML optimization
- PicoVoice: Purpose-built for voice at edge

**On-Device TTS Example (Neuphonic NeuTTS Air):**
- 748M parameters, Qwen architecture
- Real-time on mid-tier CPU (no GPU)
- Instant voice cloning (3-second samples)
- 24kHz output quality
- Zero network latency

**Challenges:**
- Limited computational resources on client devices
- Model size constraints (accuracy vs size tradeoff)
- Scaling edge infrastructure more complex than cloud
- Requires technical expertise (hosting, installation)

**Hardware Solutions:**
- Application-Specific Integrated Circuits (ASICs)
- Co-design of algorithms and hardware
- System-on-Chip (SoC) with CPU, GPU, DSP

### 7.3 Streaming LLM Architecture

**Parallel Processing Approach:**

**Dual-Model Strategy:**
- Small Language Model (SLM): Quick initial responses
- Large Language Model (LLM): Higher-quality comprehensive responses
- System starts speaking with SLM while LLM processes
- Reduces perceived latency dramatically

**Streaming Architecture:**
- Tokens generated and processed incrementally
- Don't wait for complete response before starting TTS
- Threading to parallelize LLM generation and TTS synthesis
- Custom sentence streaming segments LLM output in real-time

**Concurrency Management:**
- Process multiple asynchronous I/O streams
- Handle simultaneous inputs (voice, text, gestures)
- LLM streaming output (text, tool calls)
- Long-running background tool streams
- Unified context for environmental awareness

**Gaming Applications:**
- Lifelike NPCs with dynamic personalities
- Unscripted conversation trees
- Enhanced narrative depth and realism
- Real-time reaction to player actions

**Frameworks:**

**LiveKit Agents SDK:**
- Streaming audio through STT-LLM-TTS pipeline
- Reliable turn detection
- Interruption handling
- LLM orchestration
- Plugins for major AI providers

**AsyncVoice Agent:**
- Decouples streaming LLM backend from voice frontend
- Parallel narration and inference
- User can interrupt, query, steer reasoning anytime
- 600x reduction in interaction latency vs monolithic systems

**Performance Results:**
- Sub-300ms latency achievable with optimization
- One implementation: 239ms total latency
- 40ms to 20ms microphone input latency via WebRTC

### 7.4 Voice Agent Architecture Stack (2025)

**Component Selection:**

**Speech-to-Text (STT):**
- Deepgram Nova-3: Fast, cost-effective
- OpenAI Whisper: High accuracy
- AssemblyAI: Good balance

**Large Language Model (LLM):**
- Gemini Flash 1.5: <350ms (fastest)
- GPT-4 mini: Moderate latency, good quality
- Claude: Higher latency, excellent reasoning

**Text-to-Speech (TTS):**
- ElevenLabs: Best quality, moderate latency
- Cartesia: Fast streaming
- Edge TTS: On-device option

**Transport:**
- WebRTC: Interactive dialogue
- WebSockets: Slightly higher tolerance
- LiveKit: Complete platform solution

**Example Stack Costs (66,000 minutes/month):**
- Economy Stack: ~$1,500/month with discounts
- Premium Stack: ~$2,300/month with discounts
- 30-50% enterprise discounts typical at scale

---

## 8. Cost and Infrastructure Considerations

### 8.1 Pricing Models (2025)

**Cost Range:**
- $0.01 to $0.25 per minute depending on features
- Fully-managed platforms: $0.05-$0.15/min typical
- ~5-10 cents per minute for bundled platforms

**Pricing Structures:**

**Pay-As-You-Go:**
- Retell AI: $0.07+ per minute (AI Voice Agents)
- $0.002+ per message (AI Chat Agents)
- No platform fees

**Subscription:**
- Predictable monthly/annual costs
- Bundled usage quotas
- Overage fees if exceeding plan
- Often includes base features

**Hybrid:**
- Base subscription + discounted overages
- Bulk usage tiers
- Volume discounts

### 8.2 Component Cost Breakdown

**Speech-to-Text:**
- Deepgram Nova-3: $0.0077/min
- AWS Transcribe: $0.024/min (3.1x more expensive)
- Industry benchmark: Under $0.01/min competitive

**Text-to-Speech:**
- Variable by provider and voice quality
- Natural/cloned voices more expensive
- Streaming vs batch pricing differences

**LLM Inference:**
- Primary cost driver in voice agents
- Token-based pricing varies widely
- GPT-4: Higher cost, better reasoning
- Gemini Flash: Lower cost, faster

**Telephony (SIP):**
- $0.006-$0.02 per minute
- Twilio: Cost-effective at low scale, transparent
- Telnyx: Better rates at volume, international
- Additional charges for high-availability, analytics

### 8.3 Platform Comparison (50,000 minutes/month)

**Complex Voice Agents:**
- Retell AI: $3,500 ($0.070/min)
- Vapi AI: $7,215 ($0.144/min)
- Twilio Voice: $7,025 ($0.141/min)
- Euphonia: $18,500 ($0.370/min)

**Economy vs Premium Stack:**
- Economy: 38% cheaper per call
- Considerations: Feature set, quality, reliability
- Enterprise negotiation: 30-50% discounts possible

### 8.4 Hidden Costs and Considerations

**Integration Complexity:**
- CRM integrations (Salesforce, Zendesk) need custom dev
- Custom-branded voices increase implementation complexity
- Testing and QA for voice quality

**Compliance:**
- HIPAA or GDPR compliance raises infrastructure costs
- Certification requirements
- Data residency constraints

**Feature Surcharges:**
- PII redaction
- Speaker diarization
- Custom models/fine-tuning
- Can push bills past six figures at scale

**Infrastructure:**
- High-availability deployment
- Cross-region scaling
- Real-time analytics and monitoring
- Storage for recordings/transcripts

### 8.5 Cost Optimization Strategies

**Hybrid Architecture:**
- Lightweight models for immediate response
- Larger models for deep reasoning (post-interaction)
- Cache frequent responses to eliminate processing

**Edge Computing:**
- On-device processing eliminates API costs at scale
- Higher upfront development cost
- Better for high-volume applications

**Model Selection:**
- Balance latency, quality, cost
- Use smallest model that meets quality bar
- Different models for different interaction types

**Efficient Prompting:**
- Reduce token usage with concise prompts
- Streaming to reduce time-to-first-token costs
- Batch processing where real-time not required

---

## 9. Implementation Recommendations for TraitorSim

### 9.1 HITL Voice Integration Scenarios

**Scenario 1: Human Player as Faithful**
- Player uses voice to participate in Round Table
- AI Traitors must respond to unscripted accusations
- AI Faithful react to player's voting behavior
- Trust Matrix updates based on player voice content and tone

**Scenario 2: Human Player as Traitor**
- Voice input for Turret murder selection
- Coordinate with AI co-Traitors via voice
- Deception detection based on vocal cues
- Stress/emotion analysis from voice patterns

**Scenario 3: Spectator Mode with Voice Queries**
- "Why did Player 5 vote for Player 3?"
- "Show me the Trust Matrix for Player 7"
- "Explain the current Traitor strategy"
- Natural language queries about game state

**Scenario 4: GM Intervention**
- Human game master can voice-control game pace
- Trigger specific events via voice commands
- Modify rules/parameters mid-game
- Narration enhancement with human voice acting

### 9.2 Architecture Recommendations

**Hybrid Cloud-Edge Approach:**

**Cloud Components:**
- LLM inference for AI agent decisions (Gemini Flash for speed)
- Complex reasoning and strategy generation
- Trust Matrix analysis and updates
- Game state orchestration

**Edge Components:**
- STT for human player input (Deepgram or Whisper)
- TTS for AI agent voices (ElevenLabs or Fish Audio)
- VAD for turn detection (Silero VAD)
- Local audio processing and mixing

**Transport:**
- WebRTC for voice communication
- WebSocket for game state synchronization
- HTTP/2 for LLM API calls with streaming

### 9.3 Latency Targets for TraitorSim

**Interactive Phases (Round Table, Social):**
- Target: <500ms end-to-end for AI responses
- Critical for maintaining dramatic tension
- Use parallel processing (STT + LLM + TTS)
- Cache common phrases ("I trust them", "I'm Faithful")

**Deliberative Phases (Turret, Mission Planning):**
- Target: <2s acceptable for thoughtful responses
- Can use larger LLMs for better reasoning
- Streaming output to show "thinking"
- Visual indicators during processing

**Passive Monitoring:**
- Real-time transcription of all voice
- Asynchronous Trust Matrix updates
- Background sentiment analysis
- No strict latency requirement

### 9.4 Character Voice Design

**Persona-Specific Voices:**
- Generate or clone voice for each AI agent
- Match OCEAN personality traits to vocal characteristics:
  - High Extraversion: Louder, more expressive
  - High Neuroticism: Tense, higher pitch variation
  - High Agreeableness: Warmer tone, softer edges
  - Low Openness: Monotone, less variation
  - High Conscientiousness: Measured pace, clear articulation

**Emotional Range Requirements:**
- Calm breakfast conversation
- Tense Round Table accusations
- Panic when accused
- Cold calculation during Turret
- Excitement during mission success/failure

**Implementation:**
- Use Fish Audio for emotion control at word level
- ElevenLabs for high-quality base voices
- Pre-generate emotional variations for common phrases
- Real-time synthesis for unique/procedural lines

### 9.5 Accessibility Integration

**Required Features:**
- Speech-to-text transcription for all voice (AI and human)
- Text chat alternative for human player participation
- Visual indicators for who is speaking
- Captions/subtitles for all AI agent dialogue
- Ping system for non-verbal communication

**Visual Audio Cues:**
- Fortnite-style visual indicators for voice activity
- Directional indicators showing which agent is speaking
- Color-coding by Faithful/Traitor (in appropriate contexts)
- Volume/intensity visualization

**WHO Safe Listening Compliance:**
- Independent volume controls per agent
- Safe listening warnings for extended sessions
- Automatic audio adjustment modes

### 9.6 Cost Projections

**Assumptions:**
- 20 players per game
- 10 days (game rounds) per simulation
- 5 phases per day: 50 total phases
- Average 2 minutes voice per player per phase
- 2000 minutes total per full game

**Cost Per Game (Cloud-Based):**
- STT (Deepgram): 2000 min × $0.0077/min = $15.40
- LLM (Gemini Flash): ~5000 requests × $0.01 = $50
- TTS (Fish Audio): 2000 min × $0.05/min = $100
- Infrastructure/hosting: ~$20
- **Total per game: ~$185**

**Cost Optimization:**
- Edge TTS reduces to ~$65/game
- Caching common responses: ~$140/game
- Hybrid (key moments cloud, rest edge): ~$100/game
- Pre-generated voice assets: ~$50/game

**Annual Cost (1000 games):**
- Full cloud: $185,000
- Optimized hybrid: $100,000
- Mostly edge: $50,000

### 9.7 Implementation Phases

**Phase 1: Proof of Concept (1-2 weeks)**
- Single human player in spectator mode
- Voice queries about game state
- Simple LLM + TTS response
- No AI agent voice generation yet
- Validate STT accuracy and latency

**Phase 2: AI Agent Voice (2-3 weeks)**
- Generate/clone voices for 20 agent archetypes
- Implement emotional range testing
- Integrate TTS into Round Table phase
- Test latency with full 20-agent conversation
- Validate voice consistency across game

**Phase 3: Interactive HITL (3-4 weeks)**
- Human player can speak during Round Table
- AI agents respond to human voice input
- Trust Matrix updates from voice content
- Voting integration with voice commands
- Full game loop with one human player

**Phase 4: Accessibility & Polish (2-3 weeks)**
- Add speech-to-text transcription
- Visual audio indicators
- Text chat alternative
- Caption system for all dialogue
- Volume controls and mixing

**Phase 5: Scale Testing (1-2 weeks)**
- Multiple concurrent games
- Stress test voice infrastructure
- Optimize caching and edge processing
- Cost validation and optimization
- Performance benchmarking

**Total Estimated Timeline: 9-14 weeks**

### 9.8 Technology Stack Recommendation

**Speech-to-Text:**
- Primary: Deepgram Nova-3 (cost + latency balance)
- Fallback: OpenAI Whisper (higher quality, higher cost)

**Large Language Model:**
- Real-time dialogue: Gemini Flash 1.5 (<350ms)
- Complex reasoning: GPT-4 or Claude (for strategy)
- Emotion/sentiment: Hume AI integration for analysis

**Text-to-Speech:**
- Character voices: ElevenLabs (quality) or Fish Audio (emotion control)
- High-volume/edge: Neuphonic NeuTTS Air (on-device)
- Caching: Pre-generate with ElevenLabs, serve from storage

**Voice Activity Detection:**
- Silero VAD (<1ms per chunk, multilingual)

**Transport/Communication:**
- WebRTC for player voice input/output
- WebSocket for game state sync
- HTTP/2 streaming for LLM APIs

**Audio Middleware:**
- Integration with game engine via FMOD or Wwise
- Spatial audio for Round Table positioning
- Dynamic mixing for multiple simultaneous speakers

**Infrastructure:**
- Edge: Player client for STT/TTS processing
- Cloud: Game Master orchestration, LLM inference
- Hybrid: Critical path on edge, complex reasoning in cloud

---

## 10. Key Takeaways and Best Practices

### 10.1 Latency is Design, Not Just Infrastructure

- **200-300ms target** for conversational feel
- **Sub-500ms required** to avoid perceived lag
- **Parallel processing** essential for meeting targets
- **Streaming** at every layer (STT, LLM, TTS)
- **Caching** for common responses eliminates latency entirely

### 10.2 Hybrid Approaches Win

- **Cloud for quality**, edge for speed
- **Human for key moments**, AI for scale
- **Pre-generated for consistency**, real-time for flexibility
- **Multiple models**: Fast for interaction, slow for reasoning

### 10.3 Accessibility is Not Optional

- **300 million deaf/HoH gamers** worldwide
- **Ping systems** proven effective (Apex Legends)
- **Visual audio** industry standard (Fortnite)
- **Multi-modal communication** benefits everyone
- **WHO standards** emerging for safe gaming audio

### 10.4 Voice Quality Matters, But Consistency Matters More

- **Emotional flatness** feels inauthentic even if perfect
- **Spot-check regularly** to prevent drift
- **Design emotional ranges** per character archetype
- **Layer emotion** on consistent voice base
- **Hybrid workflows** balance quality and cost

### 10.5 Cost Scales Quickly

- **$0.05-$0.15/min** typical for managed platforms
- **Edge processing** better for high volume
- **Caching** delivers massive savings
- **Enterprise discounts** (30-50%) at scale
- **Hidden costs** in integration, compliance, features

### 10.6 The Technology is Ready

- **70% of developers** view AI as essential
- **78% of players** can't distinguish AI voices
- **Major titles** shipping with voice AI (PUBG, Horizon)
- **Production tools** available from multiple vendors
- **Latency targets** achievable with current tech

---

## 11. References and Sources

### Real-Time Voice Synthesis and Latency

- [Top Fastest Text-to-Speech APIs in 2025](https://smallest.ai/blog/fastest-text-to-speech-apis)
- [Dasha: AI NPCs in Video Games](https://dasha.ai/blog/ai-npcs-video-games)
- [AI Text to Speech Characters - VideoSDK](https://www.videosdk.live/developer-hub/tts/ai-text-to-speech-characters)
- [The Best Open-Source Text-to-Speech Models in 2026](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)
- [Audio in Video Games: Text to Speech and the AI NPC - ReadSpeaker AI](https://www.readspeaker.ai/blog/audio-in-video-games/)
- [LLM Voice AI: The Future of Voice Synthesis - VideoSDK](https://www.videosdk.live/developer-hub/developer-hub/llm/llm-voice-ai)
- [Real-Time AI Voice Agents With Ultra-Low Latency - DZone](https://dzone.com/articles/real-time-ai-voice-agents-with-ultra-low-latency)
- [Open doors to more players with text to speech for games - ReadSpeaker](https://www.readspeaker.com/sectors/gaming/)
- [AI Voices For Video Games - Resemble AI](https://www.resemble.ai/games/)
- [AI Voice Cloning in Real-Time - Smallest.ai](https://smallest.ai/blog/real-time-ai-voice-cloning-deep-learning-tts-clone)

### Speech-to-Text and Latency Benchmarks

- [GitHub: tts-latency-benchmark - Picovoice](https://github.com/Picovoice/tts-latency-benchmark)
- [Comparing speech latency of leading text-to-speech vendors - Jambonz](https://blog.jambonz.org/text-to-speech-latency-the-jambonz-leaderboard)
- [Text-to-Speech Latency: How to Read Vendor Claims - Picovoice](https://picovoice.ai/blog/text-to-speech-latency/)
- [Open-Source Text-to-Speech Latency Benchmark - Picovoice Docs](https://picovoice.ai/docs/benchmark/tts-latency/)
- [Text to Speech Latency - Deepgram Docs](https://developers.deepgram.com/docs/text-to-speech-latency)
- [Comprehensive Guide to TTS Models - Inferless](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-for-different-use-cases)
- [TTS Benchmark 2025: Smallest.ai vs ElevenLabs Report](https://smallest.ai/blog/tts-benchmark-2025-smallestai-vs-elevenlabs-report)
- [STT API Benchmarks - Gladia](https://www.gladia.io/blog/stt-api-benchmarks)
- [Reviewing performance of speech-to-text providers - Speechall](https://speechall.com/blog/stated_performance_of_speech-to-text_providers)
- [NVIDIA Riva Performance](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tts/tts-performance.html)

### Conversational AI and Voice Latency

- [Low latency Voice AI - Telnyx](https://telnyx.com/resources/low-latency-voice-ai)
- [Core Latency in AI Voice Agents - Twilio](https://www.twilio.com/en-us/blog/developers/best-practices/guide-core-latency-ai-voice-agents)
- [The Ultimate Guide to Speech Latency - VideoSDK](https://www.videosdk.live/developer-hub/rtmp/speech-latency)
- [Why Low Latency Matters for AI Agents - Retell AI](https://www.retellai.com/blog/why-low-latency-matters-how-retell-ai-outpaces-traditional-players)
- [Voice AI Agents Performance - Phonely AI](https://www.phonely.ai/blogs/performance-reliability-in-voice-ai-why-sub-second-latency-matters)
- [Millis AI - 600ms Latency Voice Agents](https://www.millis.ai/)
- [Engineering low-latency voice agents - Sierra](https://sierra.ai/blog/voice-latency)
- [Show HN: Real-time AI Voice Chat ~500ms - Hacker News](https://news.ycombinator.com/item?id=43899028)
- [Optimize latency for Conversational AI - ElevenLabs](https://elevenlabs.io/blog/how-do-you-optimize-latency-for-conversational-ai)
- [Lowest latency voice agent in Vapi - AssemblyAI](https://www.assemblyai.com/blog/how-to-build-lowest-latency-voice-agent-vapi)

### Games with Voice AI Interaction

- [Best AI games 2024 - Inworld AI](https://inworld.ai/blog/best-ai-games-2023)
- [AI + Gaming Roundup Q1 2025 - Medium](https://medium.com/@onbeam/ai-gaming-roundup-q1-2025-nintendo-unveils-switch-2-sony-tests-ai-driven-npcs-ubisofts-fac619926a24)
- [Video games with AI chatbots for NPC dialogue - NeoGAF](https://www.neogaf.com/threads/have-any-video-games-relied-on-ai-chatbots-for-npc-dialogue-yet.1685641/)
- [Conversational AI revolutionizing gaming - ElevenLabs](https://elevenlabs.io/blog/the-role-of-conversational-ai-in-gaming)
- [AI NPC voice conversations - FreeThink](https://www.freethink.com/robots-ai/ai-npc-voice-conversations)
- [ARC Raiders AI voice acting - Top Gear](https://www.topgear.com/car-news/gaming/extraction-shooter-arc-raiders-already-a-hit-its-ai-voice-acting-has-ruffled-some)
- [Top 15 AI-Powered Games 2025 - AIxploria](https://www.aixploria.com/en/category/games-en/)
- [Hume AI](https://www.hume.ai/)
- [AI Trends 2024 Game Development - MODL.ai](https://modl.ai/ai-trends-2024-game-development/)
- [AI Voice for Games - ElevenLabs](https://elevenlabs.io/use-cases/gaming)

### Multiplayer Voice Mixing

- [5 Best AI Voice Cloning Tools for Games - Fish Audio](https://fish.audio/blog/5-best-ai-voice-cloning-tools-for-games-and-characters/)
- [Live Voice Modulation in Multiplayer Games - BaseLice](https://baselice.org/2385/ultimate-techniques-for-effortless-live-voice-modulation-in-multiplayer-games)
- [Integrating audio with game logic and AI - LinkedIn](https://www.linkedin.com/advice/0/what-some-best-practices-integrating-audio-game)
- [Game Audio Mixing - Routledge](https://www.routledge.com/Game-Audio-Mixing-Insights-to-Improve-Your-Mixing-Performance/Riviere/p/book/9781032397351)
- [AI Voice for Games - ElevenLabs](https://elevenlabs.io/use-cases/gaming)
- [Use AI to improve in-game voice-overs - GameAnalytics](https://www.gameanalytics.com/blog/ai-improve-voice-overs)
- [AI Voice Generator for Games - Respeecher](https://www.respeecher.com/game-development)
- [Gaming Audio's Top 5 Vocal Effects - Voquent](https://www.voquent.com/blog/how-to-recreate-gaming-audios-top-5-vocal-effects/)
- [AI Voice Changer for Games - Respeecher Marketplace](https://www.respeecher.com/marketplace/game-developers)
- [Five Ways a Mixer Improves Multiplayer Gaming - Yamaha](https://hub.yamaha.com/audio/gaming/five-ways-a-mixer-can-improve-your-multiplayer-gaming/)

### Accessibility in Gaming

- [Deaf Accessibility in Video Games - Morgan L. Baker](https://leahybaker.com/deaf_access/)
- [Deaf Accessibility for Developers - Accessibility.com](https://www.accessibility.com/blog/what-video-game-developers-should-know-about-deaf-accessibility)
- [Accessibility in Gaming for the Deaf-Blind - AFB](https://afb.org/aw/winter2024/accessibility-gaming-deaf-blind)
- [Deaf Accessibility in Video Games 2 - Game Developer](https://www.gamedeveloper.com/audio/deaf-accessibility-in-video-games)
- [Inclusive Gaming for Hearing-Impaired - PIA](https://www.privateinternetaccess.com/blog/silent-gamers/)
- [Deaf Accessibility Tools - Morgan L. Baker](https://leahybaker.com/a11ytogaming2020/)
- [Game On for Deaf Accessibility - Ava.me](https://www.ava.me/blog/game-on-for-deaf-accessibility)
- [Best Accessible Games for Deaf/HoH - EIP Gaming](https://eip.gg/news/accessible-games-for-deaf-and-hoh-gamers/)
- [4 Innovations in Video Game Accessibility - AI Media](https://blog.ai-media.tv/blog/accessibility-in-video-games)
- [Audio accessibility in gaming - TweakTown](https://www.tweaktown.com/news/100726/inclusive-gaming-how-audio-accessibility-delivers-more-accessible-experience/index.html)

### WebRTC and Voice Streaming

- [WebRTC Low Latency Guide 2025 - VideoSDK](https://www.videosdk.live/developer-hub/webrtc/webrtc-low-latency)
- [Reducing Voice Agent Latency - WebRTC.ventures](https://webrtc.ventures/2025/06/reducing-voice-agent-latency-with-parallel-slms-and-llms/)
- [WebRTC in Mobile Gaming - MoldStud](https://moldstud.com/articles/p-webrtc-in-mobile-gaming-effective-real-time-communication-strategies)
- [Understanding WebRTC Latency - VideoSDK](https://www.videosdk.live/developer-hub/webrtc/webrtc-latency)
- [Low-Latency WebRTC Streaming - Flussonic](https://flussonic.com/blog/article/low-latency-webrtc-streaming)
- [How to Reduce WebRTC Latency - BlogGeek](https://bloggeek.me/reducing-latency-webrtc/)
- [Ultra-Low-Latency WebRTC Streaming - ResearchGate](https://www.researchgate.net/publication/393480947_Innovative_Architectures_for_Ultra-Low-Latency_WebRTC_Streaming_and_Server-Side_Recording_in_2025_A_Multi-Operator_Perspective_for_Metro_Manila)
- [When GPU Matters in WebRTC - WebRTC.ventures](https://webrtc.ventures/2025/02/when-gpu-matters-in-webrtc-accelerating-ai-video-streaming-and-real-time-communication/)
- [WebRTC on Slow Networks - WebRTC.ventures](https://webrtc.ventures/2025/01/optimizing-webrtc-performance-on-slow-networks-key-network-level-considerations/)
- [Fastest Voice Agent with AI and WebRTC - Medium](https://medium.com/@BeingOttoman/the-worlds-fastest-voice-agent-with-ai-webrtc-whisper-and-latency-comparisons-fd4604ebe537)

### Edge Computing and On-Device AI

- [Lightweight AI Models for Edge Voice - Smallest.ai](https://smallest.ai/blog/lightweight-ai-models-edge-voice-solutions)
- [Edge AI for Voice and Audio - Synervoz](https://synervoz.com/blog/edge-ai-for-voice-and-audio/)
- [Edge Computing in TTS - ReadSpeaker](https://www.readspeaker.com/blog/what-is-edge-computing/)
- [Voice Recognition at the Edge - Omi AI](https://www.omi.me/blogs/firmware-features/how-to-implement-voice-recognition-at-the-edge-in-your-firmware)
- [Build Real-Time Voice AI with WebRTC - ZedIoT](https://zediot.com/blog/building-full-duplex-conversational-ai-with-rtc-ai/)
- [Best TTS APIs in 2025 - Speechmatics](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [Edge-TTS MCP Server - Skywork AI](https://skywork.ai/skypage/en/ai-voice-edge-tts/1980156769687162880)
- [AON Edge AI - AON Devices](https://aondevices.com/aon-edge-ai-done-right/)
- [Open Voice OS on Jetson Orin Nano - NVIDIA Forums](https://forums.developer.nvidia.com/t/open-voice-os-on-jetson-orin-nano-offline-ai-assistant-with-llm-tts-stt-on-k3s/330132)
- [Why Edge-AI for voice technologies - Medium](https://medium.com/@KadhoInc/why-edge-ai-provides-a-more-robust-method-for-voice-enabled-technologies-9a61a78b0967)

### LLM Streaming and Parallel Processing

- [Reducing Voice Agent Latency with Parallel SLMs - WebRTC.ventures](https://webrtc.ventures/2025/06/reducing-voice-agent-latency-with-parallel-slms-and-llms/)
- [Real-time Bidirectional Streaming Multi-agent - Google](https://developers.googleblog.com/en/beyond-request-response-architecting-real-time-bidirectional-streaming-multi-agent-system/)
- [GPT-4 vs Claude vs LLaMA for voice agents - Gladia](https://www.gladia.io/blog/comparing-llms-for-voice-agents)
- [LLM for AI Voice Agent - VideoSDK](https://www.videosdk.live/developer-hub/llm/llm-for-ai-voice-agent)
- [Low-Latency End-to-End Voice Agents - arXiv](https://arxiv.org/html/2508.04721v1)
- [Build LLM-Powered Voice Agent in Python - Data Professor](https://dataprofessor.beehiiv.com/p/build-an-llm-powered-voice-agent-in-python)
- [AsyncVoice Agent - arXiv](https://arxiv.org/html/2510.16156v1)
- [LiveKit Agents Introduction](https://docs.livekit.io/agents/)
- [The voice AI stack for 2025 - AssemblyAI](https://www.assemblyai.com/blog/the-voice-ai-stack-for-building-agents)
- [Build AI Voice Agent with LLM Guide - VideoSDK](https://www.videosdk.live/developer-hub/llm/build-ai-voice-agent-with-llm)

### Voice Activity Detection

- [Voice Activity Detection - OpenAI API](https://platform.openai.com/docs/guides/realtime-vad)
- [Cobra Voice Activity Detection - Picovoice](https://picovoice.ai/platform/cobra/)
- [Silero VAD - GitHub](https://github.com/snakers4/silero-vad)
- [Voice Activity Detection - ScienceDirect Topics](https://www.sciencedirect.com/topics/computer-science/voice-activity-detection)
- [VAD - Introduction to Speech Processing](https://speechprocessingbook.aalto.fi/Recognition/Voice_activity_detection.html)
- [Voice activity detection - Wikipedia](https://en.wikipedia.org/wiki/Voice_activity_detection)
- [VAD Realtime - GitHub](https://github.com/hanifabd/voice-activity-detection-vad-realtime)
- [Voice Activity Detection Overview - Deepgram](https://deepgram.com/learn/voice-activity-detection)
- [VAD - SpeechBrain Documentation](https://speechbrain.readthedocs.io/en/latest/tutorials/tasks/voice-activity-detection.html)
- [What is VAD - Picovoice Blog](https://picovoice.ai/blog/what-is-voice-activity-detection/)

### Cost and Infrastructure

- [Real-Time Pricing Showdown - Retell AI](https://www.retellai.com/resources/voice-ai-platform-pricing-comparison-2025)
- [AI Voice Agent Cost Calculator 2025 - Softcery](https://softcery.com/ai-voice-agents-calculator)
- [How Much Does Voice AI Cost - CloudTalk](https://www.cloudtalk.io/blog/how-much-does-voice-ai-cost/)
- [Voice AI Providers Comparison 2025](https://comparevoiceai.com/providers)
- [Speech-to-Text API Pricing Breakdown - Deepgram](https://deepgram.com/learn/speech-to-text-api-pricing-breakdown-2025)
- [Voice AI Cost Calculator](https://comparevoiceai.com/)
- [Cost to Run Voice-AI Agent at Scale - DEV Community](https://dev.to/cloudx/how-much-does-it-really-cost-to-run-a-voice-ai-agent-at-scale-8en)
- [AI Voice Agent Pricing 2025 - VideoSDK](https://www.videosdk.live/developer-hub/ai/ai-voice-agent-pricing)
- [Voice Agent Pricing Calculator](https://comparevoiceai.com/llm)
- [AssemblyAI Pricing](https://www.assemblyai.com/pricing)

### Hybrid Human-AI Workflows

- [AI NPC Engine - Inworld UE Marketplace](https://www.unrealengine.com/marketplace/en-US/product/inworld-ai-characters-dialogue)
- [Ubisoft Generative AI NPC Narrative](https://news.ubisoft.com/en-us/article/5qXdxhshJBXoanFZApdG3L/how-ubisofts-new-generative-ai-prototype-changes-the-narrative-for-npcs)
- [Generative AI for NPC dialogs - DEV Community](https://dev.to/jacklehamster/using-generative-ai-for-npc-dialogs-5b97)
- [Ubisoft NEO NPCs - UK Article](https://news.ubisoft.com/en-gb/article/5qXdxhshJBXoanFZApdG3L/how-ubisofts-new-generative-ai-prototype-changes-the-narrative-for-npcs)
- [Conversational AI in Unreal Engine 5 - Yelzkizi](https://yelzkizi.org/conversational-ai-in-unreal-engine/)
- [Dynamic NPC Dialogue on AWS](https://aws.amazon.com/solutions/guidance/dynamic-non-player-character-dialogue-on-aws/)
- [LLMs for Game Dialogue - Pyxidis Tech](https://pyxidis.tech/llm-for-dialogue)
- [NPC Dialogue Video Generator - Mootion](https://www.mootion.com/use-cases/en/npc-dialogue-video-generator)
- [AI NPC Tools 2025 - Gamespublisher](https://gamespublisher.com/ai-npc-tools-for-game-developers-2025/)
- [Agentic Workflows for Human-AI Interaction - arXiv](https://arxiv.org/html/2501.18002v1)

### Voice Cloning for Characters

- [5 Best AI Voice Cloning Tools - Fish Audio Blog](https://fish.audio/blog/5-best-ai-voice-cloning-tools-for-games-and-characters/)
- [Creating game character voices with AI - Hume AI](https://www.hume.ai/blog/creating-video-game-character-voices-with-ai)
- [Top 7 Voice Cloning Software 2025 - MURF AI](https://murf.ai/blog/best-voice-cloning-software)
- [AI Voice Acting for Video Games - ReelMind](https://reelmind.ai/blog/ai-voice-acting-synthetic-character-voices-for-video-games)
- [AI Voice Cloning - ElevenLabs](https://elevenlabs.io/voice-cloning)
- [10 Best Voice Cloning Tools 2025 - Kukarella](https://www.kukarella.com/resources/ai-voice-cloning/the-10-best-voice-cloning-tools-in-2025-tested-and-compared)
- [AI Text To Speech & Voice Cloning - Fish Audio](https://fish.audio/)
- [Character Voice-Consistent Videos - Wavel](https://wavel.ai/blog/create-character-voice-consistent-videos-at-scale-using-advanced-video-generation-models)
- [Top 10 Voice Cloning APIs 2025 - Reverie](https://reverieinc.com/blog/voice-cloning-apis/)
- [Emotional Voice Styles with Clone - Kukarella](https://www.kukarella.com/resources/ai-voice-cloning/how-to-create-emotional-and-varied-voice-styles-with-your-clone)

---

## Appendix: Quick Reference Tables

### A. Latency Targets by Use Case

| Use Case | Target Latency | Acceptable Range | Critical? |
|----------|----------------|------------------|-----------|
| Human conversational turn-taking | 200ms | 200-300ms | Yes |
| Interactive NPC dialogue | <500ms | 300-700ms | Yes |
| Deliberative AI response | <2s | 1-3s | No |
| Background transcription | N/A | <5s | No |
| Competitive gaming voice | <100ms | 50-150ms | Yes |

### B. Technology Stack Comparison

| Component | Option 1 | Option 2 | Option 3 | Best For |
|-----------|----------|----------|----------|----------|
| **STT** | Deepgram Nova-3 | OpenAI Whisper | AssemblyAI | Deepgram (cost+speed) |
| **LLM** | Gemini Flash 1.5 | GPT-4 mini | Claude | Gemini (speed), Claude (quality) |
| **TTS** | ElevenLabs | Fish Audio | NeuTTS Air | ElevenLabs (quality), Edge (cost) |
| **VAD** | Silero VAD | Picovoice Cobra | OpenAI VAD | Silero (open source) |
| **Transport** | WebRTC | WebSocket | HTTP/2 | WebRTC (real-time) |

### C. Cost Estimates (per 1000 minutes)

| Service Type | Low-End | Mid-Range | High-End | Notes |
|--------------|---------|-----------|----------|-------|
| STT | $7.70 | $15 | $24 | Deepgram to AWS |
| TTS | $10 | $50 | $100 | Edge to premium cloud |
| LLM (per 1000 requests) | $10 | $50 | $200 | Flash to GPT-4 |
| Full managed platform | $50 | $100 | $150 | All-in-one solutions |
| Telephony (SIP) | $6 | $12 | $20 | Basic to advanced features |

### D. Accessibility Feature Checklist

- [ ] Speech-to-text for all voice content
- [ ] Text-to-speech for text content
- [ ] Visual audio indicators (direction, distance)
- [ ] Ping system for non-verbal communication
- [ ] Text chat alternative to voice
- [ ] Captions/subtitles for all dialogue
- [ ] Independent volume controls per source
- [ ] Safe listening warnings
- [ ] Colorblind-friendly indicators
- [ ] Customizable UI for readability

---

**Report compiled:** December 23, 2025
**Research conducted for:** TraitorSim HITL Voice Interface Integration
