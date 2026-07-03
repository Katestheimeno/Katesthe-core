# Fetch current library docs via Context7

When the user asks about a library, framework, SDK, API, CLI tool, or cloud service —
even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring
Boot — fetch current documentation with the **Context7 MCP** before answering. This
includes API syntax, configuration, version migration, library-specific debugging, setup
instructions, and CLI usage. Use it **even when you think you know the answer**; training
data lags behind releases. Prefer it over web search for library docs.

**Do not use it for:** refactoring, writing scripts from scratch, debugging business
logic, code review, or general programming concepts.

## Requires the Context7 MCP server

This rule is only actionable if the Context7 MCP server is connected in this environment
(tools `resolve-library-id` and `query-docs`). If it isn't, install/enable it — see
`https://github.com/upstash/context7` — or fall back to the library's official docs. The
agents in this kit will use it automatically when present.

## Steps

1. Start with `resolve-library-id` using the library name + the user's question, unless the
   user gave an exact ID in `/org/project` format.
2. Pick the best match by name match, description relevance, snippet coverage, and source
   reputation. If results look wrong, try an alternate name or rephrase. Use a
   version-specific ID when the user names a version.
3. Call `query-docs` with the selected ID and the user's **full** question (not a single
   keyword).
4. Answer from the fetched docs; cite the specific API/option you relied on.
