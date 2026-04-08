# Audio Quality Checker — Decisions Log

All decisions made during planning and building, with rationale.

---

## Planning Phase Decisions (April 8, 2026)

### D1: Target Audience
**Decision:** Public lead generation tool (anyone can use)  
**Rationale:** Brings traffic to usergy.ai, captures potential clients/contributors  
**Alternatives considered:** Internal-only tool, paid tool  
**Made by:** Swaroop  

### D2: Authentication
**Decision:** Anonymous (no login required for v1)  
**Rationale:** Lower friction = more users, faster to build  
**Alternatives considered:** Required signup, optional signup  
**Made by:** Swaroop  
**Note:** Can add accounts in v2/v3 if needed

### D3: File Size Limit
**Decision:** Up to 1 GB (1000 MB)  
**Rationale:** Generous limit covers most use cases including long recordings  
**Alternatives considered:** 100MB (too restrictive), unlimited (risky)  
**Made by:** Swaroop  

### D4: Branding
**Decision:** Follow UsergyAI Brand Bible  
**Details:**
- Primary: Deep Indigo (#1B2845)
- Accent: Electric Teal (#00BFA6)
- Warm: Saffron (#F5A623)
- Neutral: Slate Gray (#64748B)
- Fonts: Space Grotesk (headlines), Inter (body), JetBrains Mono (code/stats)
**Made by:** Swaroop  

### D5: Initial Hosting
**Decision:** Build on existing AWS EC2 server (dev/test), deploy to Azure later  
**Rationale:** 
- AWS server has plenty of resources (16GB RAM, 32GB free disk)
- Zero setup time, Python/ffmpeg already installed
- Azure $5K credits available for production deployment
**Made by:** Swaroop + Jarvis recommendation  

### D6: Tech Stack — Backend
**Decision:** Python + FastAPI  
**Rationale:** Best ecosystem for audio processing (librosa, torch, etc.), FastAPI is modern & fast  
**Alternatives considered:** Node.js (weaker audio libs), Go (limited ML support)  
**Made by:** Jarvis recommendation, Swaroop approved  

### D7: Tech Stack — AI Models
**Decision:** Whisper tiny + Silero VAD + pyannote-audio community  
**Rationale:** All MIT licensed, free, work on CPU, good enough quality  
**Alternatives considered:** 
- Whisper large (too slow on CPU, needs GPU)
- AssemblyAI API (costs money, external dependency)
- Paid pyannote (unnecessary for v1)
**Made by:** Jarvis recommendation  

### D8: Tech Stack — Frontend
**Decision:** React/Next.js or plain HTML + Tailwind (decide during build)  
**Rationale:** Both work, pick based on what integrates better with usergy.ai later  
**Made by:** Jarvis, final choice during Phase 6  

### D9: Logo
**Decision:** Create simple "Usergy[AI]" text logo for now  
**Rationale:** Don't have logo files, can update later  
**Made by:** Swaroop  

### D10: Development Approach
**Decision:** Step-by-step with checkpoints, task-state tracking  
**Rationale:** Allows interruption recovery, no lost work  
**Made by:** Swaroop request, Jarvis implementation  

---

## Build Phase Decisions

*(To be added during build)*

---

## Post-Launch Decisions

*(To be added post-launch)*
