# AI Music Producer Assistant 

> **Status:** Active Development (Academic Research Project - ISEL 2026)

## Overview
A web-based music production assistant that leverages Generative AI and Large Language Models (LLMs) to overcome creative blocks. The platform allows users to upload a base audio track, provide text prompts (e.g., "generate a jazz piano solo"), and receive complementary musical arrangements in both audio and structured notation (sheet music/tabs).

## System Architecture 
The system is built on a modular, service-oriented architecture designed to handle computationally heavy, asynchronous AI generation tasks without blocking the user interface.

* **Frontend:** Single Page Application (SPA) built with **React** for seamless user interaction and real-time status updates on asynchronous generation.
* **Backend:** RESTful API built in **Python**, handling business logic, audio processing, and system orchestration.
* **AI Orchestration:** Utilizing **LangChain** to route and manage multiple LLMs dynamically based on user context, ensuring adherence to strict music theory rules (harmony, rhythm).
* **Database & Storage:** **PostgreSQL** for relational data persistence (users, project metadata) and **AWS S3** for scalable cloud storage of `.wav` and synthesized audio files.

## Core Features 
1. **Context & Feature Extraction:** Automated analysis of uploaded audio files to extract musical characteristics (BPM, scale, key) using signal processing libraries.
2. **Generative Composition:** Integration with symbolic music models (e.g., Midi-LLM) guided by text prompts and the extracted harmonic context.
3. **Multi-Format Output:** Translates generated compositions into both synthesized audio and standard musical notation (sheet music/tabs).
4. **Asynchronous Processing:** Ensures UI responsiveness while the backend handles heavy audio synthesis and AI model inference.

## Roadmap (2026) 
- [x] Initial Research & System Architecture Setup (March)
- [ ] Backend API Development & AI Engine Prototyping (April)
- [ ] Frontend SPA Development & Integration (May)
- [ ] Full System Integration & Audio/Notation Synthesis (June)
- [ ] Beta Release & Final Optimization (July)

---
*Developed by Paulo Nascimento as part of the Computer Engineering degree at ISEL.*
