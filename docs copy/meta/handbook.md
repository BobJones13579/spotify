# MetaDocs Handbook

**TL;DR** — Universal template for AI-generated project documentation that assumes intelligence and prioritizes conciseness.

## Principles

### Simplicity is Law
All documentation must prioritize clarity and simplicity over comprehensive coverage. Complex systems require simple documentation interfaces that can be understood and maintained by both AI agents and human operators.

### Assume AI Intelligence
Cursor knows common concepts; only document what's unique to your project. Skip obvious explanations of universal programming concepts, standard framework features, and common best practices.

### Be Concise
Every sentence must add value. Document project-specific business logic, custom implementations, integration patterns unique to your system, and domain-specific terminology.

### Deterministic Hierarchy
All documentation follows a predictable structure that enables automated processing and reliable navigation by AI agents.

### TL;DR Required
Every document must begin with a one-sentence summary of its purpose.

## Folder Map

### /docs/product/
- **vision.md** — Product goals, users, success criteria
- **overview.md** — Module summary, tech stack, known gaps
- **backlog.md** — In Progress / Next / Bugs tracking
- **current_task.md** — Active feature brief with acceptance criteria

### /docs/engineering/
- **architecture.md** — System structure and technical decisions
- **changelog.md** — Version history and feature releases
- **bugs.md** — Open and resolved issue tracking
- **decisions.md** — Architectural decision log with rationales

### /docs/meta/
- **handbook.md** — This file (meta-level standards)
- **glossary.md** — Domain-specific terminology
- **templates/** — Reusable document blueprints

## Template Rules

1. **Start with TL;DR** — One-sentence summary at the top
2. **Follow AI Standards** — Assume intelligence, be concise
3. **Include Last Updated** — YYYY-MM-DD at bottom
4. **Use Plain Markdown** — #, ##, ### headers only
5. **Keep Under 300 Lines** — Focus on essential information

## AI Prompting Notes

When using this template system:

1. **Copy entire /docs structure** into new project
2. **Replace placeholders** with project-specific content
3. **Follow handbook principles** for all generated docs
4. **Update templates** as project evolves
5. **Maintain consistency** across all documentation

## Maintenance Cadence

### Weekly
- Update current_task.md with progress
- Review and close completed bugs
- Update changelog with new features

### Monthly
- Review and update vision.md
- Clean up resolved items in backlog.md
- Update architecture.md with system changes
- Review decisions.md for outdated entries

## Development Workflow

### Pre-Development
- Backup verification
- Staging deployment
- Rollback plan documentation

### During Development
- Incremental changes
- Error handling and logging
- Security review

### Before Committing
- Build verification
- Test execution
- Functionality and integration testing

### Commit & Push
- Conventional commit format
- Immediate GitHub push
- Documentation updates

### Emergency Response
- Immediate impact assessment
- Rollback vs fix-forward decision
- Data protection protocols

## AI Behavior Protocols

### Core Principles
1. **Clarity First** — All communications must be clear, concise, and unambiguous
2. **Fidelity to Source** — AI must accurately represent source material without interpretation
3. **Explicit Assumptions** — State all assumptions and constraints clearly
4. **Speech-to-Text Awareness** — AI must account for potential speech-to-text misinterpretations, especially with proper nouns and technical terms
5. **Assume AI Intelligence** — Cursor knows common concepts; only document what's unique to the project
6. **Be Concise** — Every sentence must add value; skip obvious explanations

### Safety Protocols
1. **Destructive Operation Prevention** — AI must NEVER delete files, databases, or data without explicit human confirmation
2. **Dev Server Confirmation** — AI must NEVER start development servers without explicit human confirmation
3. **Incremental Changes** — AI must prefer small, incremental changes over large, sweeping modifications
4. **Backup Before Changes** — AI must recommend creating backups before any significant modifications

### Error Handling
1. **Uncertainty Flagging** — When information is incomplete or ambiguous, AI must flag uncertainty
2. **Human Escalation** — AI must defer to human input when encountering conflicting requirements
3. **Validation Requirements** — All generated content must pass conformance checks before delivery

### Template Compliance
1. **Framework Compliance** — All outputs must conform to meta framework definitions
2. **Template Adherence** — All generated content must instantiate approved templates
3. **Cross-Reference Integrity** — Maintain all existing cross-references when updating documents

### Development Protocols
1. **Buy-vs-Build Enforcement** — AI must search for existing libraries/APIs before building custom solutions
2. **Testing Requirements** — AI must run unit tests and linting before committing changes
3. **Session Documentation** — AI must update changelog with significant changes made during the session

## Risk Management

### Development Safety
- **Incremental Changes** — Make small, testable changes rather than large modifications
- **Comprehensive Testing** — Run unit tests, integration tests, and manual verification
- **Security Review** — Verify security implications of all changes

### Production Deployment
- **Staging Validation** — Ensure all changes work in staging environment
- **Rollback Procedures** — Document and test rollback procedures
- **Monitoring** — Verify monitoring and alerting systems are functional

### Emergency Response
- **Immediate Assessment** — Quickly assess scope and impact of issues
- **Rollback Decision** — Decide whether to rollback or fix forward
- **Data Protection** — Ensure no data loss during incident response

## Task Management

### Task Breakdown Structure
- **Clear Objectives** — Define what needs to be accomplished
- **Dependencies** — Identify what must be completed first
- **Validation Criteria** — Define how to verify completion
- **Build & Test** — Include build verification and testing in each step
- **Commit & Push** — Commit with descriptive messages and push immediately

### AI Task Execution Protocol
1. **Understand Requirements** — Clarify objectives and constraints
2. **Plan Approach** — Break down into manageable steps
3. **Execute Systematically** — Follow plan step-by-step
4. **Validate Each Step** — Verify completion before proceeding
5. **Document Changes** — Update relevant documentation

### Conventional Commit Format
- **feat:** — New features
- **fix:** — Bug fixes
- **docs:** — Documentation changes
- **style:** — Code style changes
- **refactor:** — Code refactoring
- **test:** — Adding or updating tests
- **chore:** — Maintenance tasks

Last Updated: 2024-12-19
