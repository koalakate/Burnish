# Plan: Burnish Phase 7 — Analytics & Org Intelligence (Maya's Dashboard)

> **Goal:** Maya checks the analytics dashboard on Monday to see how the org is doing.
>
> **Exit criteria:** Maya logs in Monday, sees a dashboard with DQS trend, top violations, and per-team breakdown. She can identify that "Sales West" averages 62 DQS and needs training.
>
> **Ref:** Product Roadmap Phase 7
>
> **Depends on:** Sufficient check data accumulated (can be built independently after Phase 2)
>
> **Key decisions:** Analytics are read-derived (materialized from check_run data, not a separate event system). No real-time streaming — batch refresh on page load + manual refresh.

## Validation Commands
- `ruff check services/ packages/`
- `mypy services/ packages/ --ignore-missing-imports`
- `pytest packages/ services/ tests/ -x --tb=short`
- `cd apps/web && npm run lint && npm run build`

### Task 1: Analytics data models + materialization
- [ ] Create `services/db/models/analytics.py` with models: `OrgDQSSummary` (org_id, period_start, period_end, avg_dqs, total_checks, total_corrections_accepted), `TeamDQSSummary` (team_id, same fields), `ViolationLeaderboard` (org_id, evaluator, violation_type, count, period)
- [ ] Create `services/analytics/__init__.py` and `services/analytics/materializer.py`
- [ ] Implement `materialize_org_summary(org_id, period) -> OrgDQSSummary` — aggregate check_run data for the org over a time period (week, month)
- [ ] Implement `materialize_team_summaries(org_id, period) -> List[TeamDQSSummary]` — aggregate by team (derived from user → team mapping via Clerk org metadata)
- [ ] Implement `materialize_violation_leaderboard(org_id, period) -> List[ViolationLeaderboard]` — top 10 most common violation types across the org
- [ ] Store materialized summaries in DB, refresh on demand (not real-time)
- [ ] Write tests: insert sample check_run data → materialize → verify correct aggregations

### Task 2: Analytics API routes
- [ ] Implement `GET /api/analytics/org/dqs` in new `services/api/routers/analytics.py` — org-wide DQS trend over time. Query params: `period` (week/month), `range` (last 4 weeks, last 6 months, etc.)
- [ ] Implement `GET /api/analytics/teams/dqs` — per-team DQS breakdown for the selected period
- [ ] Implement `GET /api/analytics/violations` — top violations leaderboard for the org
- [ ] Implement `GET /api/analytics/users/{user_id}/history` — per-user check history (requires org admin permission)
- [ ] Implement `GET /api/analytics/volume` — check volume metrics: decks checked per period, corrections accepted vs dismissed ratio
- [ ] All analytics routes require org admin role (enforce via middleware)
- [ ] Implement `POST /api/analytics/refresh` — manually trigger re-materialization of analytics data
- [ ] Write API tests: verify data returned, admin permission enforcement, period filtering

### Task 3: Analytics dashboard UI — DQS trends
- [ ] Create analytics dashboard page at `(dashboard)/analytics/page.tsx` — Maya's primary view
- [ ] Create `apps/web/src/components/dqs-trend-chart.tsx` — line chart showing org-wide DQS over time (use Recharts or similar lightweight charting library)
- [ ] Chart features: weekly data points, trend line, hover tooltip with exact DQS value and date, configurable time range (4 weeks, 3 months, 6 months, 1 year)
- [ ] Show DQS change indicator: "+5 pts vs last week" with green/red arrow
- [ ] Card above chart: current org DQS (large number), total decks checked this period, improvement trend

### Task 4: Analytics dashboard UI — team breakdown + violations
- [ ] Create `apps/web/src/components/team-dqs-table.tsx` — table of teams sorted by DQS (worst first): team name, avg DQS, total checks, DQS trend arrow, "View Details" link
- [ ] Maya can click a team to see their individual check history and top violations
- [ ] Create `apps/web/src/components/violation-leaderboard.tsx` — bar chart or ranked list of top 10 most common violations: violation type (e.g. "Off-brand color", "Font not approved"), count, affected decks count
- [ ] Clicking a violation type shows a drill-down: list of decks with that specific violation
- [ ] Dashboard layout: DQS trend (top), team breakdown (bottom-left), violation leaderboard (bottom-right)

### Task 5: Per-user check history
- [ ] Create `(dashboard)/analytics/users/[userId]/page.tsx` — per-user check history page (org admin only)
- [ ] Show: user's average DQS over time, list of their checked decks with individual DQS scores, most common personal violations
- [ ] Anonymization toggle in org settings: when enabled, user names are replaced with "User A", "User B" etc. in analytics (privacy mode)
- [ ] Write tests: verify anonymization toggle works, admin-only access enforced

### Task 6: Check volume metrics
- [ ] Create `apps/web/src/components/volume-metrics.tsx` — summary cards showing: decks checked this week/month, corrections accepted vs dismissed (pie chart), average time from upload to download
- [ ] Add volume metrics section to analytics dashboard (below DQS trend)
- [ ] Show adoption trend: new users checking decks over time (line chart)

### Task 7: Weekly email digest
- [ ] Create `services/analytics/digest.py`
- [ ] Implement `generate_digest(org_id) -> DigestContent` — compile weekly summary: org DQS, DQS change, top 3 violations, teams needing attention (DQS < 70), check volume
- [ ] Implement email sending via a transactional email service (SendGrid, Postmark, or AWS SES)
- [ ] Create email template: branded HTML email with DQS badge, trend sparkline, violation summary, "View Dashboard" CTA
- [ ] Add digest settings in org settings: enable/disable, recipients list (org admins by default), delivery day (default Monday 9am)
- [ ] Create `services/workers/digest_worker.py` — scheduled job that runs weekly, generates and sends digest for each org with digest enabled
- [ ] Write tests: generate digest content → verify correct summary, email template rendering

### Task 8: Analytics integration test
- [ ] Seed test database with 30 days of realistic check_run data across 3 teams, 10 users, varying DQS scores and violation types
- [ ] Materialize analytics → verify all summaries are correct
- [ ] Load dashboard → verify all charts render with correct data
- [ ] Test time range filtering: switching from "4 weeks" to "3 months" shows different data
- [ ] Test team drill-down and violation drill-down navigation
- [ ] Verify admin-only access: non-admin user gets 403 on analytics routes
