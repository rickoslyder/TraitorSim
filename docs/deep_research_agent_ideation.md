Use Gemini Deep Research as a **grounding engine** that builds realistic context packs (places, jobs, subcultures, life paths), and then use a normal model call to turn those packs into individual backstories for your houseguests. [1][2][3]

## What Deep Research is Good At Here
Gemini Deep Research is an agent optimized for long‑running, multi-step research and synthesis, pulling from hundreds of web pages and your own data to produce detailed, cited reports. [1][2][4][5] It is explicitly tuned to minimize hallucinations and navigate complex information landscapes, acting like a fact‑driven researcher rather than a pure storyteller. [4][3][6]

For your simulator, that means you can use it to:
- Research **realistic socio-economic / cultural context** for “29‑year‑old Mancunian nurse”, “retired firefighter from Glasgow”, “second‑gen British-Bangladeshi software engineer in London”, etc. [1][7]
- Generate reports on typical **life trajectories, family structures, work schedules, slang, local attitudes, and housing situations** for those profiles, with citations you can later audit. [1][3][8]

## Recommended Pipeline for Backstories

### 1. Define the skeleton persona
From your casting / archetype layer (which you already have in mind), generate a “skeleton” per agent:

- Demographics: age, gender, location, education, job, family status.  
- Psychometrics: OCEAN vector + game archetype (“superfan strategist”, “lad culture party guy”, “older mum,” etc.). [9][10][11]

This skeleton is your input spec; it stays synthetic and doesn’t name real individuals.

### 2. Call Deep Research to build a context pack
For each skeleton, kick off a **background Deep Research job** via the API (with `background=true` as required). [2][12]

Prompt style (conceptually):

> “Research the typical life of a 29‑year‑old NHS nurse living in Manchester, UK, renting with flatmates, lower‑middle income.  
>  Provide:  
>  – Common career paths and daily routines  
>  – Typical financial situation and stresses  
>  – Typical family background and living situation  
>  – Common hobbies / social life patterns  
>  – Neighbourhood examples and local culture  
>  – Language, slang, and attitudes that are characteristic but non‑stereotypical  
>  Output as a structured report with sections and citations.”

Deep Research will plan, browse, and synthesize into a structured, cited report over several minutes. [1][2][3][8]

### 3. Turn the research pack into a backstory
Once you have the Deep Research report, feed it into a **standard Gemini / Claude generation call** (or your Agent SDK) to create a single-person narrative:

- Input:  
  - Persona skeleton (demographics + OCEAN + archetype). [9][11]
  - The Deep Research report as “ground truth context” that the model must not contradict. [2][3]
- Output:  
  - A first‑person or third‑person backstory with specific but **plausible** events, tied back to researched neighbourhoods, job realities, and cultural details.

You can also ask for **structured fields** (childhood summary, education path, key relationships, major trauma, political leanings, religious background, etc.) to plug directly into your agent’s long‑term memory. [13][14]

## Integrating Into Your Agent Architecture

### Pre‑season offline generation
Deep Research jobs are relatively heavy (5–15+ minutes, 100+ sources), so run this **offline as a build step** rather than at game time. [2][3][7]

- Pre‑season script:
  - Generate, say, 50–200 candidate skeletons according to a population‑aligned distribution (e.g., UK census‑aligned or custom for your “universe”). [10][11]
  - Batch Deep Research calls (with retries and caching). [2][12]
  - For each report, generate a narrative backstory and store it as `persona_card.json` or `persona_card.md` attached to the agent.

### Use in Claude / Gemini agents
At runtime:

- Load the persona card into the agent’s **system / memory context** so it “remembers” its upbringing, job realities, and attitudes. [9][15]
- Optionally maintain a shorter “working memory” version that summarizes the backstory into a few key identity anchors (“working‑class, hates authority, very family‑oriented, debt‑stressed”), which then biases dialogue and decisions. [9][16]

## Guardrails and Bias Considerations
Because you’re grounding in real socio‑cultural data, you need some minimal guardrails:

- Steer prompts away from **individuals** and keep them at population or archetype level to avoid recreating real people. [1][2]
- Explicitly request **non‑stereotypical** depictions and use Deep Research’s cited output to spot and manually correct any biased patterns across your generated cast. [3][17]

Used this way, Gemini Deep Research becomes your “casting researcher”: it gives each houseguest a socio‑economic and cultural substrate that feels authentic, and then your normal LLM agent stack sits on top to roleplay that person inside the house.

Sources
[1] Gemini Deep Research — your personal research assistant https://gemini.google/overview/deep-research/
[2] Gemini Deep Research Agent - Google AI for Developers https://ai.google.dev/gemini-api/docs/deep-research
[3] Google Gemini Deep Research: Complete Guide 2025 https://www.digitalapplied.com/blog/google-gemini-deep-research-guide
[4] Build with Gemini Deep Research https://blog.google/technology/developers/deep-research-agent-gemini-api/
[5] Create detailed reports with Deep Research | Google Workspace Blog https://workspace.google.com/blog/ai-and-machine-learning/meet-deep-research-your-new-ai-research-assistant
[6] Google Launches Upgraded Deep Research Agent ... https://www.techloy.com/google-launches-upgraded-deep-research-agent-powered-by-gemini-3-pro/
[7] The smarter way to research with Google Gemini Deep Research https://www.revolgy.com/insights/blog/smarter-way-to-research-with-google-gemini-deep-research
[8] The latest updates for Deep Research in Gemini https://workspaceupdates.googleblog.com/2025/05/deep-research-updates-gemini-io-2025.html
[9] Designing AI-Agents with Personalities: A Psychometric ... https://arxiv.org/html/2410.19238v3
[10] Population-Aligned Persona Generation for LLM-based Social ... https://arxiv.org/html/2509.10127v1
[11] Population-Aligned Persona Generation for LLM-based Social Simulation https://arxiv.org/pdf/2509.10127.pdf
[12] Data Points: Gemini makes Deep Research available via API https://www.deeplearning.ai/the-batch/gemini-makes-deep-research-available-via-api/
[13] Generative Agent Simulations of 1000 People https://huggingface.co/blog/mikelabs/generative-agent-simulations-1000-people
[14] AI Agents Simulate 1052 Individuals' Personalities with ... https://hai.stanford.edu/news/ai-agents-simulate-1052-individuals-personalities-with-impressive-accuracy
[15] [PDF] Revisiting the Impact of Personas on LLM-Synthesized Emotional ... https://aclanthology.org/2025.emnlp-main.277.pdf
[16] Dynamic Personality in LLM Agents https://aclanthology.org/2025.findings-acl.1185.pdf
[17] I ran 200+ Deep Research queries on Gemini. Here are 12 ... https://www.reddit.com/r/GeminiAI/comments/1owfpr7/i_ran_200_deep_research_queries_on_gemini_here/
[18] Gemini 3 Pro + Deep Research is absolutely insane. I think ... https://www.reddit.com/r/Bard/comments/1pows8p/gemini_3_pro_deep_research_is_absolutely_insane_i/
[19] How To Use Deep Research in Gemini https://www.youtube.com/watch?v=v8KQm8fhJfo
[20] Gemini 3 Pro Image (Nano Banana Pro) https://deepmind.google/models/gemini-image/pro/
[21] Exploring the context of online images with Backstory https://deepmind.google/blog/exploring-the-context-of-online-images-with-backstory/
[22] Google Gemini https://gemini.google.com
[23] Using Gemini Deep Research for content design desk research: Part 1 https://hippodigital.co.uk/insights/using-gemini-deep-research-for-content-design-desk-research-part-1-the-experiment/
[24] Building a Research Agent with Gemini 3 + Deep Agents https://www.youtube.com/watch?v=39mZvpN0k-Q
[25] Introducing Gemini 2.5 Flash Image, our state-of-the-art ... https://developers.googleblog.com/introducing-gemini-2-5-flash-image/
[26] Get reports with Deep Research | Gemini Enterprise https://docs.cloud.google.com/gemini/enterprise/docs/research-assistant

When using **Gemini Deep Research** via the Interactions API or Vertex AI, your data limitations are split between physical file size, total project storage, and the active reasoning context. [1][2]

### File and Storage Limits
For your lore documents and data packs, the following hardware-level limits apply:

- **Per-File Size**: Individual files uploaded via the File API or Vertex AI can be up to **2 GB**. [1][3] However, for non-video documents, a safer functional limit for consistent processing is **100 MB** to **500 MB** per file. [1][2]
- **Total Project Storage**: You can maintain a "Search Corpus" or project-wide storage of up to **20 GB**. [1][2]
- **Document Count**: You can include up to **3,000 files** in a single retrieval-grounded request. [2] Each PDF can contain up to **1,000 pages**. [2]
- **Retention**: Files uploaded through the standard File API are typically retained for **48 hours** before automatic deletion. [1][2]

### Active Reasoning (Token) Limits
Even if you upload 20 GB of lore, the agent can only "think" about a specific amount of information at once during a single turn of the simulation. [2]

- **Context Window**: Most versions of the Gemini model (including those powering Deep Research) support a context window of **1 million to 2 million tokens**. [2][4][5]
- **Token Density**: 1 million tokens roughly translates to **~1,500 pages** of text or **~30,000 lines of code**. [2]
- **Retrieval Logic (RAG)**: Deep Research uses **Retrieval-Augmented Generation (RAG)**. [2] It does not load your entire 20 GB of lore into memory; instead, it identifies relevant "fragments" that match your query and injects only those into the active token window. [2][6]

### Optimization Thresholds
To prevent the agent from "drifting" or missing lore details, follow these best practices:

| Data Type | Optimal Limit | Rationale |
| :--- | :--- | :--- |
| **Combined PDFs** | **25–30 MB** | Merging small files into mid-sized documents reduces fragmentation in the retrieval index. [1] |
| **Output Window** | **65,000 Tokens** | While the input window is massive, the maximum length for a single response is significantly smaller. [2] |
| **Search Queries** | **5,000/day** | Standard grounding requests with Google Search have daily caps that apply even if you are using custom data. [7] |

For your *The Traitors* lore, a **50–100 page "World Bible"** is well within the "perfect recall" zone of the context window, meaning the agent should be able to reference your specific constraints without any information loss. [2]

Sources
[1] Google Gemini file upload size limits, supported types, and ... https://www.datastudios.org/post/google-gemini-file-upload-size-limits-supported-types-and-advanced-document-processing
[2] Google Gemini context window: token limits, memory policy ... https://www.datastudios.org/post/google-gemini-context-window-token-limits-memory-policy-and-2025-rules
[3] Google AI Studio — File Upload and Reading: formats, limits ... https://www.datastudios.org/post/google-ai-studio-file-upload-and-reading-formats-limits-structured-output-and-long-context-wor
[4] Long context | Gemini API - Google AI for Developers https://ai.google.dev/gemini-api/docs/long-context
[5] Gemini 1.5 Pro 2M context window, code execution ... https://developers.googleblog.com/en/new-features-for-the-gemini-api-and-google-ai-studio/
[6] RAG | Vector Search | Vertex AI Search | Grounding https://discuss.google.dev/t/rag-vector-search-vertex-ai-search-grounding/180411/2
[7] Grounding with Google Search | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search
[8] Use Deep Research in Gemini... https://support.google.com/gemini/answer/15719111?hl=en
[9] Question - Does Gemini Ultra increase File Upload Limit for Deep Research? https://www.reddit.com/r/GoogleGeminiAI/comments/1mlup17/question_does_gemini_ultra_increase_file_upload/
[10] Google Gemini: File Upload, Document Reading, Limits, and ... https://www.datastudios.org/post/google-gemini-file-upload-document-reading-limits-and-how-it-actually-works
[11] Upload & analyze files in Gemini Apps - Android https://support.google.com/gemini/answer/14903178?hl=en&co=GENIE.Platform%3DAndroid
[12] Files API | Gemini API - Google AI for Developers https://ai.google.dev/gemini-api/docs/files
[13] Gemini CLI Context Window Issues after reaching 50% of its capacity https://www.reddit.com/r/GeminiAI/comments/1netsfr/gemini_cli_context_window_issues_after_reaching/
[14] Gemini's Limitations: No More 100MB File Analysis, Even with Google Drive https://www.reddit.com/r/Bard/comments/1fodak5/geminis_limitations_no_more_100mb_file_analysis/
[15] What use is Gemini 2m context window when you can't upload anything of use to it? https://www.reddit.com/r/Bard/comments/1djn80r/what_use_is_gemini_2m_context_window_when_you/
[16] Rate limits | Gemini API - Google AI for Developers https://ai.google.dev/gemini-api/docs/rate-limits
[17] Grounding with Vertex AI Search https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search
[18] Google Today Introduced Hard Limits to Gemini: Here's Why https://hostbor.com/google-introduced-hard-limits-gemini/
[19] Vertex AI Pricing https://cloud.google.com/vertex-ai/generative-ai/pricing
[20] Document upload limits for deep research? Using Deep research as data analyst instead of researcher https://www.reddit.com/r/ChatGPTPro/comments/1ilbkjc/document_upload_limits_for_deep_research_using/

To feed your game lore and constraints into **Gemini Deep Research**, you should use a combination of **File Search grounding** for the lore and **Structured Prompting** for the research constraints. Because Deep Research operates via the **Interactions API**, you can attach your own datasets (lore docs) as a "File Search" tool that the agent must prioritize alongside its web search. [1][2]

### Feeding Game Lore via File Search
Instead of pasting thousands of words of lore into a prompt, you can upload your world-building documents (PDFs, Markdown, or JSON) to a Google Cloud Storage bucket and connect them to the agent. [3]

- **The File Search Tool**: When creating the `Interaction`, you must explicitly enable the `file_search` tool in the `agent_config`. [1]
- **Lore Grounding**: Store your "House History," "Game Rules," and "Character Archetype Guides" in these files. [3] The agent will then use these as a "Source of Truth" to cross-reference with its external web research. [1][4]

### Injecting Constraints and Rules
Deep Research is highly sensitive to **Instruction-level constraints** provided in the initial `input` or `system_instruction` block. [1][5]

- **Constraint Prompting**: Use the `input` string to define how the agent should treat the lore vs. the real world.
  - *Example*: "Research the typical lifestyle of a 24-year-old student from Leeds. **Constraint**: All generated backstories must adhere to the 'Techno-Dystopian' timeline found in the attached `Lore_Bible.pdf`. If a real-world detail conflicts with the lore, the lore takes precedence." [1]
- **Negative Constraints**: You can explicitly tell the agent what to avoid, such as "Do not include any references to real-world social media platforms; use the in-game 'ZingNet' platform described in the lore documents." [1][6]

### Optimal API Implementation
When using the Python SDK for the Interactions API, your configuration would look like this:

| Config Section | Parameter | Use Case |
| :--- | :--- | :--- |
| **Input** | `input="Research [X]..."` | The primary research task with high-level constraints. [1] |
| **Agent** | `agent="deep-research-pro-..."` | Calls the specialized Deep Research model. [1] |
| **Tools** | `file_search` | Bridges your local Lore docs to the agent's context. [1][3] |
| **Prompting** | `system_instruction` | Defines the agent's persona (e.g., "You are the Lead World-Builder"). [5] |

### The "Lore-Grounding" Workflow
1.  **Prepare Lore Data**: Put your unstructured lore documents into a Cloud Storage bucket or upload them via the File API. [3]
2.  **Initialize Interaction**: Start a background job (`background=True`) so the agent can take the 10–20 minutes needed to synthesize the lore with web data. [1][7]
3.  **Cross-Verification**: In the prompt, instruct the agent to "Cite the specific section of the lore document whenever it influences a research finding." This ensures the output isn't just generic web data but is genuinely "flavored" by your game universe. [1][8]

Sources
[1] Gemini Deep Research Agent - Google AI for Developers https://ai.google.dev/gemini-api/docs/deep-research
[2] Build with Gemini Deep Research https://blog.google/technology/developers/deep-research-agent-gemini-api/
[3] Prepare data for custom data sources | Gemini Enterprise https://docs.cloud.google.com/gemini/enterprise/docs/prepare-data
[4] Grounding overview | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview
[5] Use system instructions | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions
[6] How OpenAI, Gemini, and Claude Use Agents to Power ... https://blog.bytebytego.com/p/how-openai-gemini-and-claude-use
[7] Data Points: Gemini makes Deep Research available via API https://www.deeplearning.ai/the-batch/gemini-makes-deep-research-available-via-api/
[8] Grounding with Google Search | Gemini API https://ai.google.dev/gemini-api/docs/google-search
[9] Gemini Deep Research — your personal research assistant https://gemini.google/overview/deep-research/
[10] Gemini 3 Pro Search functionality and Deep Research is ... https://www.reddit.com/r/Bard/comments/1p3zapz/gemini_3_pro_search_functionality_and_deep/
[11] Grounding with your search API | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-your-search-api
[12] How to Build a Multi-Round Deep Research Agent with ... https://www.marktechpost.com/2025/08/28/how-to-build-a-multi-round-deep-research-agent-with-gemini-duckduckgo-api-and-automated-reporting/
[13] Ragha02's Deep Research Gemini: An AI Engineer's ... https://skywork.ai/skypage/en/gemini-ai-engineer-guide/1977921823993417728
[14] How to Build AI Agents with Gemini 3 in 10 Minutes https://www.codecademy.com/article/how-to-build-ai-agents-with-gemini-3
[15] google-gemini/cookbook: Examples and guides for using ... https://github.com/google-gemini/cookbook
[16] Grounding with Google Search now in Google AI Studio ... https://www.youtube.com/watch?v=1Ba0HQW2WP0
[17] Google Opens Gemini Deep Research to Developers https://www.unifiedaihub.com/ai-news/google-opens-gemini-deep-research-to-developers-game-changer-for-ai-powered-research-applications
[18] Gemini Deep Research and the New Era of Google ... https://dev.to/alifar/gemini-deep-research-and-the-new-era-of-google-workspace-ai-workflows-30ge
[19] Grounding for Google Maps now available in the Gemini API https://blog.google/technology/developers/grounding-google-maps-gemini-api/
[20] Interactions API | Gemini API - Google AI for Developers https://ai.google.dev/gemini-api/docs/interactions
[21] Google Gemini Deep Research: Complete Guide 2025 https://www.digitalapplied.com/blog/google-gemini-deep-research-guide
