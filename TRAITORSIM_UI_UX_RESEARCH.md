# TraitorSim UI/UX Research & Design Brainstorm

## Executive Summary

This document compiles comprehensive research on UI/UX patterns for TraitorSim - an AI-powered simulation of "The Traitors" social deduction game. The goal is to create a compelling viewing experience that transforms 22-player, multi-day game simulations from text logs into an engaging narrative-driven interface.

**Key Finding**: The ideal TraitorSim UI combines:
1. **Social network visualization** (trust matrix evolution over time)
2. **Scrollytelling narrative structure** (guided story with interactive elements)
3. **Multi-modal timeline navigation** (scrubbing, phase jumping, event markers)
4. **Professional esports observer patterns** (camera control, HUD overlays, context switching)
5. **Poker tracker psychology displays** (player profiling, tendency visualization)

---

## 1. Competitive Analysis

### 1.1 Social Deduction Games

#### Blood on the Clocktower Online
**Platform**: [clocktower.online](https://clocktower.online/), [botc.app](https://botc.app/)

**Key Features**:
- Virtual grimoire (storyteller's notebook) showing all player roles, states, and deaths
- Town square circular player layout with role tokens
- Real-time vote tracking with visual vote counters
- Night sheet generation showing phase-by-phase actions
- Integrated audio/video for remote play
- Post-processing effects for dramatic moments

**Lessons for TraitorSim**:
- Circular player layout is intuitive for social games with no teams
- Role/status tokens provide at-a-glance game state
- Grimoire pattern: separate "ground truth" view for storyteller vs. player POV
- Night sheets = phase sequencing UI pattern we can adapt

**Source**: [Blood on the Clocktower Town Square](https://clocktower.online/), [GitHub - bra1n/townsquare](https://github.com/bra1n/townsquare)

#### Among Us Replay Mod
**Platform**: GitHub community tools

**Key Features**:
- Timeline scrubbing through recorded games
- Multiple camera perspectives (follow player, free cam, overview map)
- Ghost vision toggle (see through walls, see impostor kills)
- Task completion tracking overlay
- Meeting/voting history playback

**Lessons for TraitorSim**:
- Recording and replay is separate concern from live viewing
- "Ghost vision" = revealing hidden information progressively
- Map-based spatial visualization (we need relationship-space equivalent)
- Meeting history = Round Table voting patterns

**Source**: [GitHub - Smertig/among-us-replay-mod](https://github.com/Smertig/among-us-replay-mod), [GitHub - Smertig/among-us-replayer](https://github.com/Smertig/among-us-replayer)

#### BBC The Traitors Official Prediction Game
**Platform**: [bbc.co.uk/traitors](https://bbc.co.uk/traitors)

**Key Features**:
- Episode-by-episode prediction interface
- Predict next murder victim, next banishment
- Points system with global leaderboard
- Private leagues with friends
- "Who makes it to endgame" long-term predictions
- Bonus trivia questions

**Lessons for TraitorSim**:
- Gamification increases engagement
- Prediction mechanics force viewers to think strategically
- Social features (leagues) drive retention
- Episode structure = day structure in our sim

**Source**: [BBC launches The Traitors online game](https://www.televisual.com/news/bbc-launches-the-traitors-online-game/)

### 1.2 Reality TV Companion Tools

#### BrantSteele Simulators
**Platform**: [brantsteele.com/bigbrother](https://brantsteele.com/bigbrother/)

**Key Features**:
- Automatic season simulation with randomized outcomes
- Character profile cards with photos and bios
- Episode-by-episode elimination tracking
- Voting records and competition results
- Winner reveal and final statistics

**Lessons for TraitorSim**:
- Profile cards are essential for multi-character stories
- Episode structure creates natural save/resume points
- Post-game statistics satisfy data-hungry viewers
- Simple animations (fade out eliminated players) enhance drama

**Source**: [BrantSteele Big Brother Simulator](https://brantsteele.com/bigbrother/)

#### Tengaged (Online Reality Games)
**Platform**: [tengaged.com](https://tengaged.com/)

**Key Features**:
- Multiplayer online Big Brother/Survivor games
- Real-time nomination and eviction voting
- Private messaging for alliance building
- Challenge competitions with scoring
- Public and private game modes

**Lessons for TraitorSim**:
- Chat/messaging UI patterns for social strategy
- Alliance visualization through message threads
- Challenge scoreboard design
- Public vs. private information layers

**Source**: [Big Brother Game - Play Survivor, Big Brother and online reality TV games](https://tengaged.com/)

---

## 2. UI Patterns for Social Dynamics

### 2.1 Trust Network Visualization

#### Gephi / SocNetV Patterns
**Tools**: [Gephi](https://gephi.org/), [SocNetV](https://socnetv.org/)

**Core Concepts**:
- Force-directed graph layout (connected nodes attract, unconnected repel)
- Node sizing by centrality (who's most connected/influential?)
- Edge weight = relationship strength (trust vs. suspicion)
- Community detection algorithms (auto-identify alliances)
- Temporal network evolution (how does the graph change day-to-day?)

**Key Metrics for TraitorSim**:
- **Betweenness centrality**: Who's the bridge between factions? (Traitor Angel strategy)
- **Degree centrality**: Who has the most relationships?
- **PageRank**: Who's the most influential in the voting network?
- **Clustering coefficient**: How tight are alliances?

**Visual Encoding**:
- Node color: Faithful (blue) vs. Traitor (red) vs. Unknown (gray)
- Node size: Influence/centrality score
- Edge color: Trust (green gradient) to Suspicion (red gradient)
- Edge thickness: Relationship strength (amount of interaction)
- Dotted edges: Suspected relationship vs. actual alliance

**Animation Pattern**:
- Smooth transitions between day states (not instant jumps)
- Highlight nodes involved in current event (murder, accusation)
- Pulse effect on newly suspicious relationships
- Fade out eliminated players (but keep as ghost nodes for history)

**Source**: [Gephi - The Open Graph Viz Platform](https://gephi.org/), [SocNetV - Social Network Analysis and Visualization Software](https://socnetv.org/), [Exploring Trust Dynamics in Online Social Networks](https://www.mdpi.com/2297-8747/29/3/37)

#### Game-Specific Relationship Visualizations

**Game of Thrones Force-Directed Network**:
- Character nodes linked by relationships
- Solid gray = family, dashed blue = marriage, black arrow = killed by
- Interactive hover for relationship details
- Filter by relationship type

**Lessons for TraitorSim**:
- Multiple relationship types need visual distinction
- Directional relationships (A suspects B ≠ B suspects A)
- Hover/click reveals detailed suspicion score and evidence
- Filtering essential with 22 players (show only high-suspicion edges)

**Source**: [32 Game of Thrones Data Visualizations](https://medium.com/@jeffrey.lancaster/32-game-of-thrones-data-visualizations-f4ab6bc978d8)

### 2.2 Player Psychology Visualization (Poker Tracker Pattern)

#### Hand2Note / PokerTracker HUD Patterns

**Core Features**:
- Real-time overlay on player positions showing stats
- Player type classification (LAG, TAG, Fish, Shark)
- Color-coded tendencies (aggressive=red, passive=blue)
- Historical trend graphs (is behavior shifting?)
- Range visualization (what actions are they likely to take?)

**Adaptation for TraitorSim**:

**Player HUD Overlay** (when hovering over a player):
```
┌─────────────────────────────┐
│ PLAYER 7: Marcus Chen       │
│ Status: Alive | Role: ???   │
├─────────────────────────────┤
│ Personality Profile:        │
│ ████████░░ Openness (80%)   │
│ ███░░░░░░░ Neuroticism (30%)│
│ ██████░░░░ Extraversion (60%)│
├─────────────────────────────┤
│ Behavioral Patterns:        │
│ • Votes with majority (87%) │
│ • Defends accused (23%)     │
│ • Mission success (92%)     │
│ • Breakfast order: 14.2 avg │
├─────────────────────────────┤
│ Suspicion Score: 0.34       │
│ Suspected by: 8 players     │
│ Trusts most: Player 3, 12   │
└─────────────────────────────┘
```

**Player Type Profiles** (auto-classification):
- Traitor Angel (Perfect Faithful performance + defensive voting)
- Paranoid Hunter (High accusation rate, erratic voting)
- Silent Follower (Low Round Table participation, majority voting)
- Strategic Leader (High influence, coalition building)
- Chaos Agent (Unpredictable voting, mission sabotage)

**Visual Indicators**:
- Player portraits with colored borders (green=trusted, red=suspected, gold=influential)
- Small icon badges (shield, dagger, magnifying glass for role clues)
- Stress level as portrait overlay (screen shake, red tint when high paranoia)

**Source**: [10 Best Poker Software Every Player Must Know in 2025](https://www.hudstore.poker/8-best-poker-software-every-player-must-know), [Hand2Note - Poker HUD Statistical Software](https://hand2note3.hand2note.com), [PokerTracker 4](https://www.pokertracker.com/products/PT4/)

---

## 3. Timeline & Narrative UX

### 3.1 Scrollytelling Techniques

#### Core Pattern
**Definition**: Interactive storytelling that unfolds as you scroll, with fixed/updating visuals triggered by scroll position.

**Types Relevant to TraitorSim**:

1. **Step-by-Step Slideshow** (Best for Day Recap)
   - Each scroll "step" = one game event
   - Visual updates to show consequence (trust network changes)
   - Navigation breadcrumbs show progress through day

2. **Continuous Flow** (Best for Trust Matrix Evolution)
   - Smooth scrolling through entire season
   - Trust network continuously morphs
   - User controls pacing (pause on interesting moments)

3. **Scroll-Triggered Actions** (Best for Dramatic Moments)
   - Scroll to murder reveal → animation plays
   - Scroll to banishment → voting results appear sequentially
   - Scroll to recruitment → role card flips

**Example Structure for TraitorSim**:
```
┌──────────────────────────────────────┐
│  DAY 1: THE BREAKFAST REVEAL        │  ← Fixed header
├──────────────────────────────────────┤
│                                      │
│   [Murder victim fades out]          │  ← Animation triggered at 20% scroll
│                                      │
│   "Sarah was murdered by the         │  ← Text appears at 40%
│    Traitors during the night..."     │
│                                      │
│   [Trust network updates]            │  ← Graph morphs at 60%
│                                      │
│   [Breakfast order visualization]    │  ← Chart appears at 80%
│                                      │
└──────────────────────────────────────┘
```

**Notable Examples to Study**:
- NYT "Snow Fall" (pioneering scrollytelling article)
- "The Road Was Long: A Voice From Ukraine" (IDMC) - emotional narrative with illustrations
- Apple Watch Ultra page - technical specs with 3D model interactions
- COVID exponential growth explainers (ABC News) - data viz education

**Source**: [Scrollytelling: introduction](https://data.europa.eu/apps/data-visualisation-guide/scrollytelling-introduction), [12 engaging scrollytelling examples](https://shorthand.com/the-craft/scrollytelling-examples/index.html), [The Past, Present, and Future of Scrollytelling](https://nightingaledvs.com/the-past-present-and-future-of-scrollytelling/)

### 3.2 Sports Replay Timeline Scrubbing

#### Spiideo Replay / Professional Sports Patterns

**Core Features**:
- Looping critical moments (watch murder reveal 3x)
- Frame-by-frame scrubbing with jog dial
- Variable playback speed (0.5x for dramatic moments, 2x for filler)
- Jump to event markers (all murders, all Round Tables)
- Multi-camera switching (trust network view vs. individual player POV)

**Timeline UI Components**:

```
Event Markers:
    M = Murder
    R = Round Table voting
    S = Shield selection
    T = Turret (murder selection)
    ! = Dramatic moment (tie vote, recruitment, bus throw)

Timeline:
|━━━━M━━━━━━━━R━━━━S━━━━T━━!━━M━━━━━━━━R━━━━T━━━━|
Day 1 ────────────────┘            └──── Day 2 ────────

Playback Controls:
[◄◄] [◄] [▶] [▶▶]  [⟳ Loop]  Speed: [0.5x|1x|2x]
```

**Timestamping Pattern**:
- All cameras (player POVs) synced to game clock
- Switching views maintains timeline position
- Bookmark system for "I want to come back to this moment"

**Source**: [Spiideo Replay](https://www.spiideo.com/spiideo-replay/), [Introducing Spiideo REPLAY Pro](https://www.spiideo.com/news/introducing-spiideo-replay-pro-game-changing-instant-replays/)

### 3.3 True Crime Documentary Structure

#### Narrative Beats for TraitorSim

**Three-Act Structure Adapted**:

**Act 1: Setup (Days 1-3)**
- Introduce all 22 players with personality profiles
- Show initial Traitor selection and their reactions
- First murder establishes stakes
- Alliances begin forming (trust network from scratch)

**Act 2: Rising Tension (Days 4-10)**
- Red herrings and false accusations
- Traitor bus throws or recruitments
- Mission failures create paranoia
- Voting blocs solidify and shift
- "Aliveness" through present-tense investigation

**Act 3: Resolution (Days 11-15)**
- Final Faithful vs. Traitor showdown
- Vote to End or Traitor's Dilemma
- Winner reveal and retrospective "how we missed it"

**Progressive Reveal Techniques**:
- Start with Faithful POV (no role information)
- Unlock "Traitor Vision" after first banishment
- Final episode reveals ALL hidden information (diary entries, Traitor chat logs)
- Timeline replay with annotations ("Notice how Marcus avoided voting here...")

**Interactive Elements**:
- "Pause and predict" prompts before votes
- "Spot the tell" minigames (find the breakfast order anomaly)
- Choose your information layer (Trust Matrix, Voting History, Personality Profiles)

**Source**: [The story behind the cinematic true crime documentary](https://www.tandfonline.com/doi/full/10.1080/17503280.2024.2425132), [How to Write a True Crime Movie](https://industrialscripts.com/write-a-true-crime-movie/), [Unveiling the Artistry Behind True Crime Documentaries](https://www.factualamerica.com/filmmaking/the-art-of-the-true-crime-documentary)

---

## 4. Real-time vs Replay Considerations

### 4.1 Viewing Modes

#### Mode 1: Live Simulation Viewing
**Use Case**: Watching a season unfold in real-time (potentially hours-long)

**Features**:
- Real-time trust network updates as agents make decisions
- Live chat for viewers to discuss theories
- Prediction locks before each phase (can't change murder guess after Turret starts)
- Pause/resume simulation (but not rewind during live)
- "Catch up" mode: 2x speed until you reach live edge

**Technical Requirement**: WebSocket connection to simulation server

#### Mode 2: Replay/On-Demand
**Use Case**: Watching a completed season at your own pace

**Features**:
- Full timeline scrubbing (jump to any moment)
- Spoiler-free mode toggle (hide final winner, role reveals)
- Speed control (0.5x - 4x playback)
- Chapter markers for each day
- "Just the Round Tables" quick view
- Downloadable season summary PDF

**Spoiler-Free Patterns**:
- Blur role indicators until revealed in-game
- "Faithful POV" mode (only see what a Faithful would know)
- Progressive disclosure: unlock Traitor chat logs only after watching to that point
- Separate "Post-Game Analysis" tab with full spoilers

#### Mode 3: Highlights/Clips
**Use Case**: Sharing best moments on social media

**Features**:
- Auto-generated highlight reels (all murders, all tie votes, recruitment scenes)
- Clip creation tool (select start/end, add title card)
- Shareable links with embedded player
- "Moment of the season" voting

**Source**: [User Experience (UX) Design for Streaming Apps](https://www.forasoft.com/blog/article/streaming-app-ux-best-practices), [Top 13 Live Streaming Platforms](https://www.vdocipher.com/blog/live-streaming-platforms/)

### 4.2 Optimal Viewing Speed

**Recommendation Matrix**:

| Phase | Real-time Duration | Optimal Replay Speed | Rationale |
|-------|-------------------|---------------------|-----------|
| Breakfast | 2-3 min | 1x | Fast-paced, key info |
| Mission | 5-10 min | 1.5x | Action, but verbose |
| Social Hour | 10-15 min | 2x or skip | Filler unless key alliances |
| Round Table | 8-12 min | 0.75x | Drama! Savor it |
| Turret | 3-5 min | 1x | Suspenseful, high stakes |

**Auto-Speed Feature**:
- AI detects "filler" dialogue (generic small talk) → auto 2x
- Detects accusations, defenses, vote reveals → auto 1x or 0.75x
- User can override any time

---

## 5. Technical Implementation

### 5.1 D3.js Force-Directed Graph (Trust Network)

#### Why D3.js?
- Industry standard for custom data viz
- Full control over physics simulation
- Massive community and examples
- Integrates with React (our likely frontend framework)

#### Key APIs:
```javascript
// d3-force simulation
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide().radius(30));

// Update on each tick
simulation.on("tick", () => {
  // Update node and link positions
});
```

#### Advanced Features:
- **Drag interaction**: Click-drag nodes to explore
- **Zoom/pan**: Mouse wheel or pinch to navigate large networks
- **Tooltip hover**: Show suspicion score, evidence summary
- **Time scrubbing**: Interpolate between day N and day N+1 network states
- **Highlighted paths**: Trace voting coalitions, alliance chains

**Alternatives Considered**:
- **react-force-graph**: Higher-level wrapper, less customization
- **Reagraph**: WebGL-based, better performance for 1000+ nodes (overkill for 22)
- **Cytoscape.js**: More features, steeper learning curve

**Recommendation**: Start with **react-force-graph** for rapid prototyping, switch to raw D3 if we need custom layouts.

**Source**: [d3-force | D3 by Observable](https://d3js.org/d3-force), [Force-directed graph component](https://observablehq.com/@d3/force-directed-graph-component), [react-force-graph](https://github.com/vasturiano/react-force-graph)

### 5.2 Three.js / WebGL for Dramatic Effects

#### Use Cases for 3D Graphics

**Primary**: 3D Trust Network (optional view)
- Nodes in 3D space with Z-axis = time (day 1 at bottom, day 15 at top)
- Camera orbits around network cylinder
- Dramatic for marketing/trailers, possibly gimmicky for analysis

**Secondary**: Visual Effects
- Particle effects for murder reveals (fade to ash)
- Spotlight effects for Round Table accusations
- 3D role card flips (Traitor recruitment)
- Camera shake for high-stress moments

**3d-force-graph Library**:
- Drop-in replacement for 2D version
- VR/AR support (future: watch in VR?)
- Post-processing effects (bloom, depth of field for cinematic look)

**Performance Consideration**:
- 3D is heavier; offer toggle to 2D for low-end devices
- Use 3D primarily for desktop, 2D for mobile

**Source**: [GitHub - vasturiano/3d-force-graph](https://github.com/vasturiano/3d-force-graph), [Visualizing Graphs in 3D with WebGL](https://neo4j.com/blog/developer/visualizing-graphs-in-3d-with-webgl/)

### 5.3 React Component Architecture

**Proposed Tech Stack**:
- **Frontend**: React + TypeScript
- **Styling**: Tailwind CSS + Headless UI
- **Data Viz**: D3.js (low-level) + react-force-graph (high-level)
- **3D**: Three.js via react-three-fiber
- **State Management**: Zustand (lightweight) or Redux Toolkit
- **Routing**: React Router (multi-page: Home, Season Viewer, Season Archive)
- **Animation**: Framer Motion (page transitions, UI animations)
- **Real-time**: Socket.io or Pusher for live simulation updates
- **Backend API**: FastAPI (Python, integrates with game engine)
- **Database**: PostgreSQL (season storage) + Redis (real-time state)

**Component Hierarchy**:
```
<App>
  <SeasonViewer seasonId={123}>
    <Header /> (season title, progress bar)
    <TimelineControls /> (play/pause, speed, scrubber)
    <MainView>
      <TrustNetworkGraph /> (force-directed D3)
      <PlayerGrid /> (thumbnail portraits with status)
      <EventFeed /> (scrolling text log of actions)
    </MainView>
    <SidePanel>
      <PlayerProfile /> (selected player deep dive)
      <VotingHistory /> (table/chart of votes)
      <MissionResults /> (success/fail tracking)
    </SidePanel>
    <PhaseNavigator /> (jump to Breakfast, Mission, Round Table, etc.)
  </SeasonViewer>
</App>
```

**Source**: [React.js Graph Visualization](https://blog.tomsawyer.com/react-js-graph-visualization), [Ten React graph visualization libraries](https://dev.to/ably/top-react-graph-visualization-libraries-3gmn)

### 5.4 Data Pipeline

**Flow**:
```
Game Engine (Python)
  ↓ WebSocket / REST API
Game State JSON
  ↓ FastAPI endpoints
Frontend State Store
  ↓ React rendering
UI Components
```

**Key Data Structures**:

```typescript
interface GameState {
  day: number;
  phase: "breakfast" | "mission" | "social" | "roundtable" | "turret";
  players: Player[];
  events: Event[];
  trustMatrix: TrustMatrix;
  votingHistory: Vote[];
}

interface Player {
  id: number;
  name: string;
  role: "traitor" | "faithful" | "unknown";
  status: "alive" | "murdered" | "banished";
  personality: PersonalityTraits;
  suspicionScore: number; // Global average
  eliminatedDay?: number;
}

interface TrustMatrix {
  // M[i][j] = player i's suspicion of player j
  matrix: number[][]; // 0.0 (trust) to 1.0 (certain traitor)
  lastUpdated: string; // ISO timestamp
}

interface Event {
  id: string;
  timestamp: string;
  type: "murder" | "banishment" | "accusation" | "defense" | "shield" | "recruitment";
  actors: number[]; // player IDs involved
  description: string;
  impactedRelationships: RelationshipDelta[];
}
```

---

## 6. Feature Ideas (Ranked by Impact/Effort)

### High Impact / Low Effort (MVP Features)

1. **Trust Network Graph (2D Force-Directed)**
   - Effort: 2 weeks (using react-force-graph)
   - Impact: 9/10 - Core differentiator, makes social dynamics visible
   - Tech: D3.js + React

2. **Player Profile Cards**
   - Effort: 1 week
   - Impact: 8/10 - Essential for 22-player cast
   - Design: Poker tracker HUD pattern

3. **Timeline Scrubber with Event Markers**
   - Effort: 1 week
   - Impact: 9/10 - Navigation is critical
   - Pattern: Sports replay UI

4. **Voting History Table**
   - Effort: 3 days
   - Impact: 7/10 - Easy to spot patterns (who voted with Traitors?)
   - Display: Heatmap with color-coded votes

5. **Phase Navigator (Jump to Breakfast/RT/Turret)**
   - Effort: 2 days
   - Impact: 8/10 - Skip filler, watch drama
   - UX: Tab bar or dropdown

### High Impact / Medium Effort (Phase 2)

6. **Scrollytelling Day Recaps**
   - Effort: 3 weeks (content + animation engineering)
   - Impact: 9/10 - Transforms data into story
   - Tech: Intersection Observer API + Framer Motion

7. **Auto-Generated Highlights**
   - Effort: 2 weeks (ML to detect dramatic moments + video editing)
   - Impact: 8/10 - Shareable content, virality
   - Algorithm: Detect sudden trust matrix changes, tie votes, accusations

8. **Player Type Classification (LAG/TAG from poker)**
   - Effort: 2 weeks (clustering algorithm on behavior data)
   - Impact: 7/10 - Helps viewers understand strategies
   - Display: Badge on player card

9. **Breakfast Order Tell Visualization**
   - Effort: 1 week
   - Impact: 6/10 - Book fans will love it, casuals may not care
   - Chart: Line graph showing entry order by day, highlight anomalies

10. **Mission Performance Breakdown**
    - Effort: 1 week
    - Impact: 6/10 - Detective work (sabotage vs. clumsiness)
    - Display: Skill check log with probability analysis

### Medium Impact / Low Effort (Nice-to-Haves)

11. **Dark Mode**
    - Effort: 2 days
    - Impact: 5/10 - User preference, accessibility
    - Tech: CSS variables + toggle

12. **Speed Control (0.5x - 4x)**
    - Effort: 1 day
    - Impact: 6/10 - User autonomy
    - UI: Dropdown or slider

13. **Clip Sharing**
    - Effort: 3 days (generate shareable URL with start/end times)
    - Impact: 7/10 - Marketing/virality
    - Tech: URL params + Open Graph tags

14. **Keyboard Shortcuts**
    - Effort: 2 days
    - Impact: 5/10 - Power users
    - Examples: Space=play/pause, J/L=rewind/forward, 1-5=speed

### High Impact / High Effort (Future Roadmap)

15. **3D Trust Network (WebGL)**
    - Effort: 4 weeks
    - Impact: 7/10 - Looks amazing, questionable UX benefit
    - Tech: Three.js + react-three-fiber

16. **Live Prediction Game (BBC Traitors pattern)**
    - Effort: 6 weeks (backend for user accounts, scoring, leaderboards)
    - Impact: 9/10 - Engagement, retention, community
    - Backend: User auth + real-time updates

17. **"Faithful POV" / "Traitor POV" Toggles**
    - Effort: 3 weeks (data model for information hiding)
    - Impact: 8/10 - Replay value, spoiler control
    - Logic: Filter events/trust updates by knowledge access

18. **AI Narrator (Text-to-Speech for Events)**
    - Effort: 2 weeks (integrate TTS API, script generation)
    - Impact: 6/10 - Accessibility, cinematic feel
    - Voice: British accent (Claudia Winkleman vibes?)

19. **VR Viewing Mode**
    - Effort: 8 weeks
    - Impact: 4/10 - Gimmick unless VR adoption increases
    - Tech: WebXR + A-Frame

20. **Social Features (Comments, Reactions)**
    - Effort: 4 weeks (moderation, spam prevention)
    - Impact: 7/10 - Community building
    - Examples: Timestamp comments like YouTube, emoji reactions

### Low Impact / High Effort (Avoid for Now)

21. **Fully Custom Animation for Each Event**
    - Effort: 12 weeks (animator required)
    - Impact: 6/10 - Looks great, but text/data works fine
    - Risk: Not scalable across 100s of seasons

22. **AR Mobile App**
    - Effort: 10 weeks
    - Impact: 3/10 - No clear use case
    - Skip unless we have a killer idea

---

## 7. Wireframe Descriptions

### 7.1 Main Viewing Interface (Desktop)

```
┌────────────────────────────────────────────────────────────────────┐
│ TraitorSim | Season 1: "The Betrayal Begins"        [Settings] [?] │
├────────────────────────────────────────────────────────────────────┤
│ Day 3 | Round Table Phase                          🔴 LIVE         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────┐  ┌─────────────────────┐ │
│  │                                     │  │  PLAYER 7: Marcus   │ │
│  │     TRUST NETWORK GRAPH             │  │  ────────────────── │ │
│  │                                     │  │  [Portrait]          │ │
│  │        ●─────●                      │  │  Status: Alive      │ │
│  │       ╱│╲   ╱ ╲                     │  │  Role: Unknown      │ │
│  │      ● │ ● ●  ●                     │  │                     │ │
│  │       ╲│╱│╱│╲╱                      │  │  Personality:       │ │
│  │        ●─●─●                        │  │  Open  ████████░░   │ │
│  │                                     │  │  Neuro ███░░░░░░░   │ │
│  │   [Zoom] [Filter] [3D Mode]        │  │                     │ │
│  └─────────────────────────────────────┘  │  Suspicion: 0.34    │ │
│                                            │  Suspected by: 8    │ │
│  ┌──────────────────────────────────────┐ │                     │ │
│  │ EVENT FEED                           │ │  [View Full Profile]│ │
│  │ ─────────────────────────────────    │ └─────────────────────┘ │
│  │ 15:32 Marcus accuses Sarah           │                         │
│  │ 15:30 Sarah defends herself          │ ┌─────────────────────┐ │
│  │ 15:28 Voting begins                  │ │  VOTING HISTORY     │ │
│  │ 15:25 [MURDER] Emma killed           │ │  ────────────────── │ │
│  │ ...                                  │ │  Day 3 Round Table  │ │
│  └──────────────────────────────────────┘ │  Sarah  ████████░░  │ │
│                                            │  Marcus ██████░░░░  │ │
├────────────────────────────────────────────┤  Emma   ████░░░░░░  │ │
│ ◄◄ ◄ ▶ ▶▶  [1x ▼]  [⟳]                   │  ...                │ │
│ |━M━━━R━━S━━T━━!━━M━●━━R━━T━━━━━|         │                     │ │
│ Day 1          Day 2     ^Day 3           └─────────────────────┘ │
│ [Breakfast] [Mission] [Social] [RoundTable] [Turret]              │
└────────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- **Top Bar**: Season title, live indicator, settings
- **Phase Indicator**: Current day and phase
- **Main View**: Trust network graph (largest element)
- **Player Detail Panel**: Right sidebar, shows selected player
- **Event Feed**: Scrolling log (like a chat window)
- **Voting History**: Mini heatmap (who voted for whom)
- **Playback Controls**: Bottom bar with scrubber and phase navigator

### 7.2 Scrollytelling Day Recap

```
┌────────────────────────────────────────────────────────────────────┐
│                         DAY 3 RECAP                                 │
│                     "The Accusation"                                │
└────────────────────────────────────────────────────────────────────┘
                              ↓ Scroll ↓
┌────────────────────────────────────────────────────────────────────┐
│                      [BREAKFAST - 7:30 AM]                          │
│                                                                     │
│              [Emma's portrait fades to grayscale]                   │
│                                                                     │
│        "Emma was murdered by the Traitors during the night."        │
│                                                                     │
│             The group enters the breakfast room in shock.           │
└────────────────────────────────────────────────────────────────────┘
                              ↓ Scroll ↓
┌────────────────────────────────────────────────────────────────────┐
│                  [BREAKFAST ORDER ANALYSIS]                         │
│                                                                     │
│   Day 1    Day 2    Day 3                                           │
│   ┌────────────────────────┐                                       │
│  1│ Sarah   Marcus  Sarah                                          │
│  2│ Marcus  Sarah   John                                           │
│  3│ John    Lisa    Lisa                                           │
│   ...                                                               │
│ 20│ Lisa    John    Marcus  ← Entered last again!                  │
│   └────────────────────────┘                                       │
│                                                                     │
│   Marcus has entered last 2/3 days. Coincidence?                   │
└────────────────────────────────────────────────────────────────────┘
                              ↓ Scroll ↓
┌────────────────────────────────────────────────────────────────────┐
│                     [MISSION: Laser Heist]                          │
│                                                                     │
│   Mission Failed: 3 sabotages detected                             │
│                                                                     │
│   [Bar chart showing each player's skill check results]            │
│   Sarah   ████████ Success                                         │
│   Marcus  ████████ Success                                         │
│   John    ██░░░░░░ Failed (Dexterity roll: 0.23)                   │
│   Lisa    ████████ Success                                         │
│   ...                                                               │
│                                                                     │
│   Three players failed. Were they sabotaging, or just unlucky?     │
└────────────────────────────────────────────────────────────────────┘
                              ↓ Scroll ↓
┌────────────────────────────────────────────────────────────────────┐
│                   [ROUND TABLE - 8:00 PM]                           │
│                                                                     │
│   Sarah (standing): "I think Marcus is a Traitor."                 │
│                                                                     │
│   [Trust network animates: Sarah → Marcus edge turns red]          │
│                                                                     │
│   Marcus (defensive): "That's ridiculous! I've been—"              │
│                                                                     │
│   [Other players' suspicion scores update in real-time]            │
│                                                                     │
│   Voting Results:                                                  │
│   Sarah:  ████████████ 12 votes                                    │
│   Marcus: ████░░░░░░░░  4 votes                                    │
│                                                                     │
│   Sarah has been banished. She was... a Faithful.                  │
└────────────────────────────────────────────────────────────────────┘
                              ↓ Scroll ↓
┌────────────────────────────────────────────────────────────────────┐
│                    [TRUST NETWORK EVOLUTION]                        │
│                                                                     │
│   Day 1              Day 2              Day 3                       │
│   ●───●              ●───●              ●   ●  (Sarah eliminated)   │
│   │╲ ╱│              │╲ ╱│              │╲ ╱                        │
│   │ ● │     →        │ ● │     →        │ ●                        │
│   │╱ ╲│              │╱ ╲│              │╱ ╲                        │
│   ●───●              ●───●              ●───●                       │
│                                                                     │
│   Alliances are fracturing. Who will be next?                      │
└────────────────────────────────────────────────────────────────────┘
```

**Animation Triggers**:
- Player portrait fade (CSS opacity transition)
- Chart reveals (stagger animation)
- Trust network morphing (D3 force simulation transition)
- Text typewriter effect (optional, may be too slow)

### 7.3 Mobile-First Player Grid

```
┌─────────────────────┐
│  TraitorSim S1      │
│  Day 3 | Round Table│
├─────────────────────┤
│ ┌────┐ ┌────┐ ┌────┐│
│ │ S1 │ │ S2 │ │ S3 ││  Player Grid (3 cols)
│ │ ✓  │ │ ✓  │ │ ☠  ││  ✓=alive, ☠=dead, ⚠=suspected
│ └────┘ └────┘ └────┘│
│ ┌────┐ ┌────┐ ┌────┐│
│ │ S4 │ │ S5 │ │ S6 ││
│ │ ✓  │ │ ⚠  │ │ ✓  ││
│ └────┘ └────┘ └────┘│
│        ...           │
├─────────────────────┤
│ [Trust] [Votes] [Feed] │  Tab Navigation
├─────────────────────┤
│  TRUST NETWORK      │  (Swipeable views)
│  (Simplified 2D)    │
│       ●─────●       │
│      ╱ ╲   ╱ ╲      │
│     ●───●─●───●     │
│      ╲ ╱   ╲ ╱      │
│       ●─────●       │
│  [Tap to expand]    │
├─────────────────────┤
│ [◄] [▶] [1x▼] [⟳]  │  Playback Controls
│ |━━━━━●━━━━━━━|     │  Timeline Scrubber
└─────────────────────┘
```

**Mobile Adaptations**:
- Grid instead of network graph (too small on mobile)
- Tab navigation instead of multiple panels
- Touch gestures: swipe left/right to change days, pinch to zoom on graph
- Fullscreen mode for network graph (rotate to landscape)

---

## 8. Technology Recommendations

### 8.1 Frontend Stack (Final Recommendation)

**Core**:
- React 18+ (with Suspense for lazy loading)
- TypeScript (type safety for complex game state)
- Vite (fast build tool)

**Styling**:
- Tailwind CSS (utility-first, rapid prototyping)
- Radix UI or Headless UI (accessible components)
- Framer Motion (animations)

**Data Visualization**:
- D3.js v7 (low-level control)
- react-force-graph (high-level network graphs)
- Recharts or Visx (charts/tables)

**3D Graphics** (Phase 2):
- Three.js
- react-three-fiber (React bindings)

**State Management**:
- Zustand (lightweight, recommended for most state)
- TanStack Query (formerly React Query) for API data caching

**Routing**:
- React Router v6

**Real-time** (if live viewing):
- Socket.io client

### 8.2 Backend Stack

**API**:
- FastAPI (Python, async, auto-generated docs)
- Pydantic for data validation
- CORS middleware for frontend access

**Database**:
- PostgreSQL (relational data: players, events, voting history)
- Redis (optional: real-time simulation state, caching)

**Storage**:
- S3-compatible object storage for season archives (JSON files)

**Deployment**:
- Docker + Docker Compose (local dev)
- Frontend: Vercel or Netlify (static hosting)
- Backend: Railway, Render, or AWS ECS

### 8.3 Development Roadmap

**Phase 1: MVP (8-10 weeks)**
1. Week 1-2: Project setup, basic React app, API integration
2. Week 3-4: Player grid, profile cards, voting table
3. Week 5-6: Trust network graph (2D, basic interactions)
4. Week 7-8: Timeline scrubber, phase navigator
5. Week 9-10: Event feed, styling, responsive design

**Phase 2: Enhanced Viewing (6-8 weeks)**
6. Week 11-12: Scrollytelling day recaps
7. Week 13-14: Auto-generated highlights
8. Week 15-16: Player type classification, advanced stats
9. Week 17-18: Polish, performance optimization, testing

**Phase 3: Community & Engagement (8 weeks)**
10. Week 19-22: Live prediction game (backend + frontend)
11. Week 23-24: Clip sharing, social features
12. Week 25-26: Mobile app optimization, PWA features

**Phase 4: Advanced Features (Ongoing)**
- 3D trust network
- VR mode
- AI narrator
- Multi-season comparison tools

---

## 9. Key Inspirations & References

### Must-Study Examples

1. **Blood on the Clocktower Online** - Role-based game state visualization
   - [clocktower.online](https://clocktower.online/)
   - [GitHub - bra1n/townsquare](https://github.com/bra1n/townsquare)

2. **BBC The Traitors Prediction Game** - Viewer engagement model
   - [BBC launches The Traitors online game](https://www.televisual.com/news/bbc-launches-the-traitors-online-game/)

3. **PokerTracker / Hand2Note** - Player psychology HUDs
   - [10 Best Poker Software](https://www.hudstore.poker/8-best-poker-software-every-player-must-know)
   - [Hand2Note](https://hand2note3.hand2note.com)

4. **NYT Scrollytelling Articles** - Narrative data viz
   - [Scrollytelling examples](https://shorthand.com/the-craft/scrollytelling-examples/index.html)

5. **Gephi Network Graphs** - Trust network patterns
   - [Gephi](https://gephi.org/)
   - [Game of Thrones visualizations](https://medium.com/@jeffrey.lancaster/32-game-of-thrones-data-visualizations-f4ab6bc978d8)

6. **Spiideo Replay** - Sports timeline scrubbing
   - [Spiideo Replay](https://www.spiideo.com/spiideo-replay/)

7. **League of Legends Spectator Mode** - Esports observer UI
   - [Spectator Mode Wiki](https://wiki.leagueoflegends.com/en-us/Spectator_Mode)
   - [Best tools for LoL spectating](https://lhm.gg/post/best-tools-for-league-of-legends-spectating-observing-and-hud-management)

8. **react-force-graph** - Technical implementation
   - [GitHub - vasturiano/react-force-graph](https://github.com/vasturiano/react-force-graph)
   - [Graph Data Visualization With GraphQL & react-force-graph](https://lyonwj.com/blog/graph-visualization-with-graphql-react-force-graph)

---

## 10. Open Questions & Next Steps

### Questions to Resolve

1. **Target Audience**:
   - Casual viewers (need simple UI) vs. strategy nerds (want all the data)?
   - Recommendation: Start casual, add "Advanced Stats" toggle for nerds

2. **Monetization**:
   - Free with ads? Subscription? One-time purchase?
   - Affects feature prioritization (free tier vs. premium)

3. **Season Length**:
   - How long should one season take to watch? (30 min? 2 hours? 8 hours?)
   - Determines pacing, auto-speed settings

4. **Replayability**:
   - Do we expect users to watch the same season multiple times?
   - If yes, invest in "Traitor POV" toggle, commentary tracks

5. **Platform Priority**:
   - Desktop-first or mobile-first?
   - Recommendation: Desktop for initial dev (easier for complex UI), mobile-optimize in Phase 2

### Immediate Next Steps

1. **Design Mockups** (Week 1-2):
   - Figma wireframes based on section 7
   - User flow diagrams (how do you start watching a season?)
   - Branding (logo, color palette, typography)

2. **Technical Proof-of-Concept** (Week 3-4):
   - Build minimal React app
   - Load sample game state JSON
   - Render basic trust network graph with react-force-graph
   - Prove we can animate between day N and day N+1

3. **User Testing** (Week 5):
   - Show mockups + POC to 5-10 potential users
   - Questions: "What would you click first?" "What's confusing?" "What's most exciting?"
   - Iterate based on feedback

4. **Production Planning**:
   - Finalize MVP scope (which features from section 6?)
   - Create Jira/Linear tickets
   - Assign engineering resources
   - Set launch date target

---

## Appendix: Full Source List

### Social Deduction Game Tools
- [GitHub - Smertig/among-us-replay-mod](https://github.com/Smertig/among-us-replay-mod)
- [GitHub - Smertig/among-us-replayer](https://github.com/Smertig/among-us-replayer)
- [Blood on the Clocktower Town Square](https://clocktower.online/)
- [GitHub - bra1n/townsquare](https://github.com/bra1n/townsquare)
- [Blood on the Clocktower Online](https://botc.app/)
- [Werewolf Game Online](https://gidd.io/games/werewolf/)
- [Wolftown on Steam](https://store.steampowered.com/app/3948350)

### Reality TV & Companion Tools
- [BrantSteele Big Brother Simulator](https://brantsteele.com/bigbrother/)
- [Big Brother Game - Tengaged](https://tengaged.com/)
- [BBC launches The Traitors online game](https://www.televisual.com/news/bbc-launches-the-traitors-online-game/)
- [RHAP: Survivor, Big Brother, Reality TV](https://robhasawebsite.com/)

### Network Visualization
- [Gephi - The Open Graph Viz Platform](https://gephi.org/)
- [SocNetV - Social Network Analysis and Visualization Software](https://socnetv.org/)
- [Exploring Trust Dynamics in Online Social Networks](https://www.mdpi.com/2297-8747/29/3/37)
- [Interactive and Dynamic Social Network Visualization in R](http://curleylab.psych.columbia.edu/netviz/netviz1.html)
- [Social Network Graphs: Concepts, Metrics & Tools](https://www.puppygraph.com/blog/social-network-graphs)
- [Cambridge Intelligence - Social Network Visualization](https://cambridge-intelligence.com/use-cases/social-networks/)
- [Make interactive network graphs without coding | Flourish](https://flourish.studio/visualisations/network-charts/)

### Game UI/UX Patterns
- [32 Game of Thrones Data Visualizations](https://medium.com/@jeffrey.lancaster/32-game-of-thrones-data-visualizations-f4ab6bc978d8)
- [10 Best Poker Software Every Player Must Know in 2025](https://www.hudstore.poker/8-best-poker-software-every-player-must-know)
- [DriveHUD - Poker HUD](https://drivehud.com/)
- [PokerTracker 4](https://www.pokertracker.com/products/PT4/)
- [Hand2Note - Poker HUD Statistical Software](https://hand2note3.hand2note.com)
- [Poker Copilot](https://pokercopilot.com/)

### Timeline & Replay Interfaces
- [Spiideo Replay](https://www.spiideo.com/spiideo-replay/)
- [Introducing Spiideo REPLAY Pro](https://www.spiideo.com/news/introducing-spiideo-replay-pro-game-changing-instant-replays/)
- [Sports Production Instant Replay](https://ptzoptics.com/sports-production-instant-replay-live-annotations/)
- [Spectator Mode | League of Legends Wiki](https://wiki.leagueoflegends.com/en-us/Spectator_Mode)
- [A Better Lens: Refining Esports Spectator Modes](https://static1.squarespace.com/static/5b18aa0955b02c1de94e4412/t/5c00582f032be444791e4635/1543526448989/SHER_KEMPE-COOK_CORDOVA_A+Better+Lens.pdf)
- [In-game observers are the greatest unsung heroes in esports](https://www.oneesports.gg/valorant/in-game-observers-esports-job/)
- [Best tools for League of Legends spectating](https://lhm.gg/post/best-tools-for-league-of-legends-spectating-observing-and-hud-management)

### Narrative & Storytelling
- [Scrollytelling: introduction](https://data.europa.eu/apps/data-visualisation-guide/scrollytelling-introduction)
- [12 engaging scrollytelling examples](https://shorthand.com/the-craft/scrollytelling-examples/index.html)
- [The Past, Present, and Future of Scrollytelling](https://nightingaledvs.com/the-past-present-and-future-of-scrollytelling/)
- [Data Visualization Scrolling Examples](https://vallandingham.me/scroll_talk/examples/)
- [The story behind the cinematic true crime documentary](https://www.tandfonline.com/doi/full/10.1080/17503280.2024.2425132)
- [Unveiling the Artistry Behind True Crime Documentaries](https://www.factualamerica.com/filmmaking/the-art-of-the-true-crime-documentary)
- [How to Write a True Crime Movie](https://industrialscripts.com/write-a-true-crime-movie/)

### Streaming UX
- [User Experience (UX) Design for Streaming Apps](https://www.forasoft.com/blog/article/streaming-app-ux-best-practices)
- [Top 13 Live Streaming Platforms](https://www.vdocipher.com/blog/live-streaming-platforms/)
- [6 UX Guidelines for Video Streaming Platforms](https://medium.com/design-bootcamp/6-ux-guidelines-for-streaming-platforms-d315396a3178)
- [UX Design Principles for Video Streaming Apps: Netflix Case Study](https://www.netsolutions.com/insights/video-streaming-apps-ux-design/)

### Technical Implementation
- [d3-force | D3 by Observable](https://d3js.org/d3-force)
- [Force-directed graph component](https://observablehq.com/@d3/force-directed-graph-component)
- [GitHub - vasturiano/react-force-graph](https://github.com/vasturiano/react-force-graph)
- [Graph Data Visualization With GraphQL & react-force-graph](https://lyonwj.com/blog/graph-visualization-with-graphql-react-force-graph)
- [GitHub - reaviz/reagraph](https://github.com/reaviz/reagraph)
- [React.js Graph Visualization](https://blog.tomsawyer.com/react-js-graph-visualization)
- [Ten React graph visualization libraries](https://dev.to/ably/top-react-graph-visualization-libraries-3gmn)
- [GitHub - vasturiano/3d-force-graph](https://github.com/vasturiano/3d-force-graph)
- [Visualizing Graphs in 3D with WebGL](https://neo4j.com/blog/developer/visualizing-graphs-in-3d-with-webgl/)
- [GitHub - davidpiegza/Graph-Visualization](https://github.com/davidpiegza/Graph-Visualization)

### Data Visualization Patterns
- [270toWin - 2028 Presidential Election Interactive Map](https://www.270towin.com/)
- [Visualize elections | Flourish](https://flourish.studio/resources/elections/)
- [16 ways to visualize US elections data](https://flourish.studio/blog/report-on-elections-with-flourish/)
- [Visualizing the Polarized States of America](https://www.datawrapper.de/blog/weekly-chart-presidential-elections)
- [from dashboard to story — storytelling with data](https://www.storytellingwithdata.com/blog/from-dashboard-to-story)
- [Susie Lu - Storytelling in Dashboards](https://susielu.com/data-viz/storytelling-in-dashboards)
- [What is Data Storytelling | Microsoft Power BI](https://www.microsoft.com/en-us/power-platform/products/power-bi/topics/data-storytelling)

### Character Relationship Visualization
- [Telling Stories through Multi-User Dialogue by Modeling Character Relations](https://arxiv.org/abs/2105.15054)
- [How to Draw Character Relationship Diagrams](https://boardmix.com/articles/making-character-relationship-diagram/)
- [Character Relationship Analysis | Devpost](https://devpost.com/software/character-relationship-analysis)
- [Conversation as Gameplay – Emily Short's Interactive Storytelling](https://emshort.blog/2019/01/20/conversation-as-gameplay-talk/)

### Detective/Mystery Game UI
- [Detective and game ui ideas - Pinterest](https://www.pinterest.com/toshibarandy/ui-detective/)
- [Franziska Huebner - Detective Game](https://fhuebner.artstation.com/projects/e0kLaX)
- [Murder Mystery Kit with Cinematic Video](https://murderinprague.com/)
- [Unsolved Case Files & Murder Mystery Games Online](https://coldcaseinc.com/)
- [Murder Experience - The First Realistic Investigation Game](https://murderexperience.com/)

---

## Final Recommendations Summary

**MVP Priorities (Launch in 3 months)**:
1. 2D Trust Network Graph (force-directed, D3.js)
2. Player Profile Cards (poker tracker style)
3. Timeline Scrubber with Phase Navigation
4. Voting History Heatmap
5. Event Feed
6. Responsive Design (desktop + mobile)

**Tech Stack**:
- Frontend: React + TypeScript + Tailwind + react-force-graph
- Backend: FastAPI + PostgreSQL
- Deployment: Vercel (frontend) + Railway (backend)

**Differentiation**:
- Trust Matrix Visualization (no other Traitors tool has this)
- Scrollytelling Day Recaps (makes data into story)
- Prediction Game (BBC pattern, drives engagement)

**Long-term Vision**:
- Community platform for sharing seasons
- Season creator (upload your own AI simulations)
- Tournaments and leaderboards
- Educational mode (teach game theory, Bayesian reasoning)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Author**: Claude (Research Agent)
**Status**: Ready for Design Team Review
