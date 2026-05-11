---
name: Example reference memory — external resource pointer
description: How reference memories capture pointers to external systems (URLs, dashboards, third-party tools)
type: reference
last_verified: 2026-01-01
triggers: [example, reference, template, external, resource]
index_entry:
  section: "🔗 External references"
  order: 1
  label: "Example: external resource"
  hook: "Pattern for tracking external tools and dashboards"
---

# Example external resource

The team's primary observability dashboard lives at `https://grafana.example.com/d/api-latency`.

**When to use:** any time you're investigating production latency or touching
request-handling code, check this dashboard first — it's the one that pages oncall.

---

This is an example template memory. Reference memories track pointers to systems
outside the current project — URLs, dashboards, third-party APIs, vendor docs.

The point is to remember **where to look**, not to duplicate the external content.
