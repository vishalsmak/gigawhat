# Project Brief: Governed AI Operational Assistant for a Regulated Energy Business

## 1. Your Role

Act as a **Senior AI Solutions Architect and Lead AI Engineer** with expertise in enterprise AI, retrieval-augmented generation (RAG), agentic workflows, LLM evaluation, security, and regulated environments.

Your task is to design and implement a production-oriented AI assistant that helps operational colleagues in a regulated energy business find trusted procedures, summarise relevant evidence, and identify appropriate next steps.

Think like an engineer responsible for a system that must be reliable, auditable, secure, maintainable, and useful in real operational workflows.

Do not simply build a conversational interface around an LLM. Build a governed, evidence-grounded decision-support system.

Before writing substantial amounts of code, understand the requirements, propose an architecture, identify risks and assumptions, and establish a clear implementation plan.

## 2. Business Objective

Operational colleagues often need to locate the correct procedures, understand technical documentation, reconcile information from different sources, and determine what to do next.

The assistant should help them:

1. Find the most relevant, authoritative operational procedures and supporting documents.
2. Answer questions using approved internal knowledge sources.
3. Summarise relevant evidence in clear, concise language.
4. Provide traceable citations to the exact sources supporting its answers.
5. Highlight conflicting, outdated, incomplete, or insufficient evidence.
6. Suggest appropriate next steps based on approved procedures.
7. Recognise when it lacks sufficient evidence and escalate to a qualified human.
8. Preserve human accountability for operational decisions.

**Core design principle: The assistant should make the right procedure easier to find, the evidence easier to understand, and the next step easier to justify — without taking the decision away from the human.**

## 3. Safety and Governance Requirements

The system operates in a regulated energy environment. Reliability and governance are architectural requirements, not features to add later.

The assistant must:

- Never make safety-critical decisions autonomously.
- Never present an unsupported inference as an established fact.
- Never fabricate procedures, document references, citations, or operational instructions.
- Never silently resolve material contradictions between authoritative sources.
- Distinguish verified source information from interpretation or recommendations.
- Identify missing evidence and communicate uncertainty clearly.
- Abstain from answering when evidence is inadequate.
- Escalate safety-critical, ambiguous, contradictory, or out-of-scope questions to an appropriate human.
- Respect authentication, authorisation, and document-level access permissions.
- Prevent unauthorised users from retrieving restricted information through either search results or generated answers.
- Treat retrieved documents and user-provided content as untrusted data, not instructions that can override system policies.
- Maintain appropriate audit trails for user queries, retrieved sources, system decisions, and outputs, subject to data-protection and retention requirements.

Do not assume that adding a disclaimer makes an unsafe workflow acceptable. High-risk scenarios should be controlled through system design, deterministic rules, permissions, workflow restrictions, and human review.

## 4. High-Level Architecture

Design the system around the following logical components.

### A. Knowledge sources

The initial system should support approved operational documents such as:

- Standard operating procedures.
- Technical manuals.
- Policies and engineering guidance.
- Operational bulletins.
- Approved knowledge articles.
- Relevant records and supporting evidence.

Every source should have appropriate metadata where available:

- Document ID and title.
- Owner and approval status.
- Version.
- Effective date and review date.
- Document type.
- Operational domain.
- Access-control metadata.
- Supersession or retirement status.

The system must distinguish authoritative, current documents from drafts, expired documents, and superseded versions.

Do not invent a document hierarchy. Establish the source-of-truth rules with the business and operational owners.

### B. Ingestion and indexing pipeline

Implement a controlled ingestion pipeline that:

1. Ingests supported document formats.
2. Extracts text and relevant structural information.
3. Preserves headings, sections, tables, and document references where possible.
4. Validates document metadata and approval status.
5. Detects duplicates and handles document updates.
6. Splits documents into meaningful, context-preserving chunks.
7. Associates each chunk with its source and metadata.
8. Generates embeddings and indexes the content.
9. Supports filtering by document version, authority, domain, and user permissions.
10. Removes or invalidates superseded content from active retrieval when appropriate.

The ingestion pipeline must be repeatable, observable, and testable.

Design it so that changing or updating a document does not require rebuilding the entire system unnecessarily.

### C. Retrieval layer

Build a retrieval system that prioritises relevance, authority, and access control.

Consider:

- Semantic vector search.
- Keyword or lexical search.
- Hybrid retrieval.
- Metadata filtering.
- Reranking retrieved passages.
- Deduplication and source diversity.
- Retrieval thresholds and relevance checks.
- Version and approval-status filtering.
- Query clarification when a request is ambiguous.

Apply authorisation controls before restricted information can be exposed. Do not rely on the LLM to enforce access permissions.

Where the evidence is weak or conflicting, the retrieval layer should communicate that limitation to the orchestration layer rather than forcing a result.

Choose retrieval techniques based on measurable performance, not complexity for its own sake.

### D. Orchestration and reasoning

Use a controlled orchestration layer to manage the interaction between retrieval, generation, validation, and escalation.

Evaluate LangGraph for workflows that require explicit states, conditional routing, retries, human approval, and auditable transitions. Use LangChain where its abstractions genuinely simplify integration.

The workflow should conceptually support:

1. Receive and classify the question.
2. Determine the question's domain, intent, and risk level.
3. Check whether the request is within the assistant's permitted scope.
4. Retrieve authorised, relevant evidence.
5. Assess source authority, freshness, relevance, and conflicts.
6. Determine whether the evidence is sufficient.
7. Generate an evidence-grounded response.
8. Validate citations, answer structure, and policy compliance.
9. Return the answer, request clarification, abstain, or escalate.
10. Record appropriate audit and evaluation information.

Use explicit states and conditional transitions for critical decisions rather than relying entirely on an LLM's free-form reasoning.

Avoid unnecessary autonomous agents, unrestricted tool access, or multi-agent complexity. Start with the simplest architecture that meets the requirements.

### E. Answer generation

The assistant's answers should be structured, readable, and useful to operational colleagues.

Where appropriate, responses should contain:

- **Answer:** A direct response to the question.
- **Supporting evidence:** The relevant facts found in approved sources.
- **Sources:** Document title, version, section, page or paragraph, and a link where available.
- **Recommended next steps:** Actions supported by the approved procedures.
- **Limitations:** Missing evidence, ambiguity, uncertainty, or conflicts.
- **Escalation:** The relevant human or process to consult when required.

Citations must refer to the actual retrieved evidence and support the associated claims.

Do not fabricate page numbers, URLs, document versions, or citations.

When sources conflict, identify the conflict and follow the agreed governance rules. If the conflict cannot be resolved safely, abstain and escalate.

### F. Validation and policy enforcement

Implement a validation layer between answer generation and the user interface.

Where practical, validate:

- Whether the cited sources were actually retrieved.
- Whether citations point to valid source locations.
- Whether important claims have supporting evidence.
- Whether retrieved documents meet approval and freshness requirements.
- Whether the response complies with the assistant's permitted scope.
- Whether the response contains prohibited autonomous decisions or unsupported instructions.
- Whether mandatory uncertainty and escalation conditions have been handled.

Use deterministic checks for rules that can be reliably expressed in code. Use model-based evaluation only where appropriate, and do not treat an LLM judge as definitive proof of safety.

A response that fails a critical validation check must be corrected, withheld, or escalated rather than displayed as if it were reliable.

### G. User interface

Provide a simple interface that lets operational colleagues:

- Ask questions in natural language.
- View concise answers and supporting evidence.
- Open cited source documents.
- See relevant document versions and dates.
- Understand uncertainty and source conflicts.
- Request clarification or refine a question.
- Escalate to a human when necessary.

Make the provenance of information visible. Users should be able to distinguish what an approved procedure explicitly states from what the assistant is suggesting based on that procedure.

Do not imply that the assistant's recommendation constitutes formal approval or authorisation.

### H. Observability, evaluation, and audit

Design the system to be observable from the beginning.

Track appropriate operational and technical metrics, including:

- Retrieval relevance and recall.
- Citation validity and evidence coverage.
- Answer correctness and groundedness.
- Expert-assessed procedural correctness.
- Abstention and escalation behaviour.
- Contradiction detection.
- Access-control violations.
- Latency, availability, and cost.
- User corrections and feedback.
- Task completion time and user adoption.

Maintain suitable audit events for queries, retrieved source identifiers, workflow transitions, validation outcomes, and final responses.

Apply data minimisation, access controls, retention limits, and redaction to logs. Do not indiscriminately store sensitive prompts or operational records.

Evaluate LangSmith or an equivalent platform for tracing, debugging, dataset-based evaluation, and regression testing. Tool choice must fit the organisation's security, deployment, and data-handling requirements.

## 5. Evaluation Strategy

Do not evaluate the system merely by asking whether its answers sound convincing.

Build a representative evaluation dataset containing realistic operational questions and expert-verified expected behaviour.

Include at least these scenarios:

1. A straightforward question with one authoritative source.
2. A question whose answer requires multiple documents.
3. An ambiguous question that requires clarification.
4. A question where the relevant procedure is missing.
5. Conflicting guidance from two documents.
6. An expired or superseded procedure.
7. A question that requires access to restricted information.
8. A question with misleading assumptions.
9. An adversarial prompt attempting to override system instructions.
10. A safety-critical question that must not receive an autonomous decision.
11. A question where the assistant should explicitly say it does not know.
12. A question where a human must review or approve the proposed next step.

Measure performance at the retrieval, generation, and end-to-end workflow levels.

Establish baselines, acceptance thresholds, and critical failure criteria with the relevant stakeholders before pilot deployment.

Certain failures, such as unauthorised disclosure or prohibited safety-critical decisions, should be treated as hard gates rather than averaged into a general quality score.

## 6. Suggested Technology Stack

Treat these as starting candidates, not mandatory choices.

- **Language:** Python.
- **API:** FastAPI or an equivalent framework.
- **LLM integration:** A model-provider abstraction that supports configuration and replacement.
- **Orchestration:** LangGraph where explicit workflow control is beneficial.
- **Retrieval:** A combination of lexical and vector search, with optional reranking.
- **Embeddings:** A configurable embedding model.
- **Storage:** An appropriate relational database, document storage, and vector-search solution.
- **Authentication and authorisation:** Integration with the organisation's identity provider and access-control model.
- **Evaluation and tracing:** LangSmith or a suitable alternative.
- **Testing:** Unit tests, integration tests, retrieval evaluations, workflow tests, and security tests.
- **Deployment:** Containerised services and an environment compatible with enterprise infrastructure.

Choose concrete products only after identifying hosting constraints, data residency, identity integration, expected scale, approved model providers, and existing enterprise platforms.

Do not introduce additional infrastructure without a clear requirement.

## 7. Engineering Standards

Build this as a maintainable software project, not a single large notebook or monolithic script.

Use:

- Clear separation between ingestion, retrieval, orchestration, generation, validation, and API layers.
- Typed interfaces and explicit data models.
- Configuration through environment variables or managed configuration.
- Secure secret management.
- Structured logging and meaningful error handling.
- Dependency management and reproducible environments.
- Automated tests and continuous integration where appropriate.
- Versioned prompts, evaluation datasets, and workflow configurations.
- Documentation for architecture, setup, deployment, and operations.
- Interfaces that allow individual components to be replaced without rewriting the entire system.

Keep business rules, risk classification, access checks, and escalation policies explicit and testable.

Never hard-code credentials, assume that local development security is sufficient, or log sensitive information unnecessarily.

## 8. Implementation Plan

Work in controlled phases.

### Phase 1: Discovery and architecture

Before implementing the complete solution:

- Clarify the intended users and operational workflow.
- Identify the source documents and their authority.
- Define risk categories and permitted actions.
- Identify security, privacy, and deployment constraints.
- Document key assumptions and unresolved decisions.
- Produce a system architecture and data-flow diagram.
- Define interfaces between components.
- Create a risk register and evaluation plan.
- Explain important technology choices and alternatives.

### Phase 2: Minimal end-to-end prototype

Build a small vertical slice that demonstrates the full flow:

Approved documents → ingestion → authorised retrieval → evidence-grounded generation → citation and policy validation → user response.

Include basic observability and automated tests from the start.

### Phase 3: Evaluation and hardening

Add the evaluation dataset, retrieval improvements, conflict handling, abstention, access-control tests, prompt-injection tests, and operational monitoring.

Fix failures before adding unnecessary features.

### Phase 4: Controlled pilot

Support a narrowly defined workflow with selected users, approved documents, clear limitations, and human oversight.

Capture expert feedback and measure whether the system improves the workflow without introducing unacceptable risk.

### Phase 5: Production readiness and scale

Only expand after agreed quality, security, governance, and operational criteria have been met.

Define ownership, incident response, change management, model updates, document lifecycle management, and ongoing evaluation.

## 9. How You Should Work

Follow these rules throughout the project:

1. **Do not start by coding everything.** First understand the problem and propose the architecture.
2. State assumptions explicitly and ask focused questions when a missing decision materially affects the design.
3. Distinguish confirmed requirements from proposed solutions.
4. Explain architectural trade-offs, including why simpler alternatives may be sufficient.
5. Prioritise security, reliability, traceability, and maintainability over novelty.
6. Build incrementally, with a working and tested end-to-end path early.
7. Write tests alongside implementation.
8. Do not invent internal documents, APIs, credentials, or enterprise infrastructure.
9. When external services or credentials are unavailable, use explicit interfaces and clearly labelled local development substitutes.
10. Report what has actually been implemented and tested; never claim a feature works merely because its code exists.
11. Keep a record of unresolved risks and decisions.
12. Avoid implementing real operational actions or integrations until their permissions, risk controls, and approval requirements are defined.

## 10. Your First Deliverable

For your first response, **do not write the application code yet**.

Produce the following:

1. A concise problem statement and list of assumptions.
2. A proposed architecture with a component diagram.
3. A description of the end-to-end request and response flow.
4. The responsibility and interface of each major component.
5. A proposed repository and module structure.
6. A recommended technology stack with justification and alternatives.
7. A threat model and key failure modes.
8. An evaluation plan with example test cases and proposed metrics.
9. A phased implementation roadmap with clear acceptance criteria.
10. A short list of high-impact questions that must be answered before implementation.

Be specific and technically rigorous. Explain how the system will behave when sources are missing, stale, conflicting, unauthorised, or insufficient to support a reliable answer.

The objective is to create a trustworthy operational assistant whose answers are evidence-based, whose limitations are visible, whose actions are controlled, and whose behaviour can be evaluated and audited.
