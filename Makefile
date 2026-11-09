.PHONY: deploy-routines

# Reprovisions the ai-news-digest scheduled cloud routine ("AI Radar (archive)")
# from the versioned spec in the repo. Useful after a Claude account migration,
# when the routine itself (account-side, not versioned) is gone.
# Needs the `claude` CLI on PATH and a logged-in Claude Code session.
deploy-routines:
	claude "Reprovision the ai-news-digest routine named 'AI Radar (archive)'. \
Load the schedule skill or use the RemoteTrigger tool directly (list first, \
to check whether it already exists; if it does, update it instead of creating \
a duplicate). Build the routine from: \
.claude/skills/ai-news-digest/references/routine-prompt.md for the exact prompt \
(the fenced code block under '## The prompt'), \
.claude/skills/ai-news-digest/references/scheduling.md for the schedule \
(weekdays 08:00 America/Sao_Paulo -> cron 0 11 * * 1-5) and the required tools \
(Bash, Read, Write, Edit, Glob, Grep, WebFetch), \
.claude/settings.json for the pinned model, and the repo \
https://github.com/werner-denzin/claude-labs as the only source. \
Pick the environment named Default unless told otherwise, and set \
clear_mcp_connections: true since this routine needs no connectors. \
Creating/updating/running a routine needs your live approval when the tool \
prompts for it - that is expected, approve it there. After creating or \
updating, call RemoteTrigger get to confirm the stored prompt and schedule \
match the file, then report: the routine's claude.ai link, whether GitHub is \
connected for cloud cloning (if not, point at claude.ai/customize -> \
Connectors -> Yours -> GitHub Integration), and whether the chosen \
environment's Network access is Full or Custom-with-allowlist (if it is the \
default Trusted setting, every news source will 403 and the newsletter will \
come out empty -- say so plainly, do not guess or claim it is fine without \
checking)." --allowed-tools "RemoteTrigger,Read,Bash"
	@echo ""
	@echo "=== Manual steps still required (see README Getting Started) ==="
	@echo "1. GitHub connected? claude.ai/customize -> Connectors -> Yours ->"
	@echo "   GitHub Integration (without it, the routine cannot clone the repo)"
	@echo "2. Environment Network access set to Full, or Custom with the"
	@echo "   allowlist in .claude/skills/ai-news-digest/references/scheduling.md"
	@echo "   (the default Trusted setting 403s every news source)"
	@echo ""
	@echo "Once both are done: run 'make deploy-routines' again, or trigger the"
	@echo "routine manually at https://claude.ai/code/routines, and check that"
	@echo "reports/ gets a new file and 'sources_disabled'/failures in it look sane."
