# Burnish — User Personas & Customer Journey Maps

> This document is the reference for all design, frontend, and UX decisions.
> Agents building UI must read this before writing any component code.

---

## Persona 1: Maya Chen — Brand Manager at a Mid-Size SaaS Company

### Demographics
- **Age:** 32
- **Role:** Brand & Communications Manager at a B2B SaaS company (200 employees)
- **Reports to:** VP Marketing
- **Team:** 3 designers, 2 content writers, 12 "slide creators" across Sales/CS/Product
- **Tech comfort:** High — uses Figma, Notion, Slack daily. Not a developer.

### Context
Maya owns the brand guidelines. She created a 47-page PDF in Figma and published it to Notion. But nobody reads it. Every week she finds decks going to clients with wrong fonts, off-palette colors, stretched logos, and walls of text. She spends 4-6 hours/week manually reviewing decks that people Slack her "for a quick look."

### Goals
- Stop being the bottleneck for slide review
- Ensure every client-facing deck meets brand standards without her touching it
- Track which teams consistently produce off-brand work (so she can target training)
- Reduce the "just check this real quick" Slack messages to zero

### Frustrations
- "I wrote the guidelines. Nobody follows them. I'm not a slide police officer."
- Reviewing decks is the worst part of her week — tedious, repetitive, thankless
- She catches the same mistakes over and over (wrong blue, Comic Sans in footers, 8pt text)
- No visibility into how many off-brand decks leave the org without her seeing them

### What "magic" looks like
Maya connects her Notion brand guide. Burnish extracts the rules automatically. She reviews and approves them once. From now on, anyone in the org can upload a deck and get instant feedback — without Maya. She checks the analytics dashboard on Mondays to see the org's DQS trend going up.

### Key behaviors
- Uploads brand guidelines (PDF/Notion) during onboarding
- Reviews extracted rules, tweaks tolerances
- Checks analytics weekly
- Rarely uploads decks herself — her team does

---

## Persona 2: Jake Torres — Enterprise Sales Account Executive

### Demographics
- **Age:** 28
- **Role:** Account Executive, Enterprise Sales
- **Company:** Same SaaS company as Maya, or similar
- **Tech comfort:** Medium — lives in Google Slides, Salesforce, Slack. Knows nothing about design.

### Context
Jake builds 3-5 custom pitch decks per week by copy-pasting from the "master deck" and customizing for each prospect. He works fast, under deadline pressure. He knows the slides don't look great — he's seen Maya's corrections — but he doesn't know *what* specifically is wrong or how to fix it. He just needs the deck to not embarrass him in the meeting tomorrow.

### Goals
- Get a "clean" deck in under 10 minutes, not 2 hours
- Stop getting pinged by Maya about font sizes and colors
- Look polished and professional in front of enterprise buyers
- Never think about design rules — just have them applied automatically

### Frustrations
- "I don't know what WCAG contrast means and I don't care. Just fix it."
- Copy-pasting between decks breaks formatting and he can't figure out why
- He wastes 30 minutes trying to match colors by eyeballing hex codes
- Maya's corrections arrive too late — after the meeting already happened

### What "magic" looks like
Jake uploads his deck. Burnish shows him red/yellow dots on the slides that have problems. He clicks "Fix All." Downloads the corrected PPTX. Done in 90 seconds. He never learns what Delta-E means. He doesn't need to.

### Key behaviors
- Uploads 3-5 decks per week
- Always clicks "Accept All Corrections" — never reviews individually
- Cares about speed above everything
- Will abandon the tool if it takes more than 2 minutes

---

## Persona 3: Priya Mehta — Freelance Presentation Designer

### Demographics
- **Age:** 36
- **Role:** Independent presentation design consultant
- **Clients:** 4-8 active clients, each with different brand guidelines
- **Tech comfort:** Very high — PowerPoint power user, knows Figma, some HTML/CSS

### Context
Priya designs presentations for multiple clients. Each has different brand colors, fonts, and layout preferences. She's meticulous about quality but switching between brand contexts is error-prone. She once sent a deck to Client A with Client B's color palette. Nightmare.

### Goals
- Switch between client brand rulesets instantly
- Catch her own mistakes before the client does
- Use the tool as a final QA pass before delivery
- Generate compliant starter decks for new projects (future: generation engine)

### Frustrations
- Managing 6+ brand guides in her head simultaneously
- Small mistakes that slip through manual review (a #333333 that should be #2D2D2D)
- Clients who change their brand guidelines and don't tell her
- No tool exists that understands *multiple* brands — everything assumes one org = one brand

### What "magic" looks like
Priya has a different brand ruleset for each client. She uploads a deck, selects "Acme Corp" from the ruleset dropdown. Burnish checks it against Acme's specific rules. She switches to "Globex" for the next deck. The correction view shows her exactly what's off — she reviews each one because she's a perfectionist. She accepts most, edits a few manually.

### Key behaviors
- Creates and manages multiple brand rulesets
- Uses the correction view in detail — reviews each issue individually
- Cares deeply about the DQS score (professional pride)
- Uploads finished decks for QA, not rough drafts

---

## Customer Journey Maps

### CJM 1: Maya — First-Time Brand Setup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE        │ AWARENESS      │ ONBOARDING        │ BRAND SETUP       │ ONGOING │
├─────────────────────────────────────────────────────────────────────────────────┤
│              │                │                   │                   │         │
│ ACTIONS      │ Sees Burnish   │ Signs up with     │ Uploads brand PDF │ Checks  │
│              │ on LinkedIn    │ Google SSO        │ Reviews extracted │ weekly  │
│              │ "AI slide      │ Creates org       │ rules in table    │ analytics│
│              │ checker"       │ Invites 2 people  │ Adjusts color     │ dashboard│
│              │                │ to test           │ tolerances        │         │
│              │                │                   │ Publishes ruleset │         │
│              │                │                   │                   │         │
│ THINKING     │ "Could this    │ "Let me see if it │ "Wow it actually  │ "DQS is │
│              │ actually save  │ understands our   │ found our brand   │ trending│
│              │ me 5 hrs/wk?"  │ brand"            │ colors from the   │ up. The │
│              │                │                   │ PDF. Some are     │ team is │
│              │                │                   │ wrong though"     │ learning"│
│              │                │                   │                   │         │
│ FEELING      │ Hopeful but    │ Cautiously        │ Impressed by      │ Relieved│
│              │ skeptical      │ optimistic        │ extraction,       │ and     │
│              │                │                   │ slightly nervous  │ validated│
│              │                │                   │ about accuracy    │         │
│              │                │                   │                   │         │
│ PAIN POINTS  │ "Will it work  │ "What if it       │ "3 of 12 colors   │ "Wish I │
│              │ with our       │ doesn't under-    │ are wrong. But    │ could   │
│              │ messy brand    │ stand complex     │ 9 are perfect —   │ see per-│
│              │ PDF?"          │ guidelines?"      │ faster than       │ person  │
│              │                │                   │ manual entry"     │ stats"  │
│              │                │                   │                   │         │
│ KEY MOMENTS  │ Clicks         │ First org         │ Reviews rules     │ First   │
│ OF TRUTH     │ "Try Free"     │ created in        │ — confidence      │ Monday  │
│              │                │ < 60 seconds      │ scores help her   │ with no │
│              │                │                   │ trust/distrust    │ Slack   │
│              │                │                   │ each extraction   │ review  │
│              │                │                   │                   │ requests│
│              │                │                   │                   │         │
│ BURNISH      │ Landing page   │ Clerk SSO         │ Brand rule review │Analytics│
│ TOUCHPOINTS  │                │ Onboarding wizard │ UI with source    │dashboard│
│              │                │                   │ snippets          │         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Critical Design Implications (Maya)
- **Rule review UI must show confidence scores** — Maya needs to trust the extraction
- **Source snippets are essential** — she needs to see WHERE in the PDF a rule came from
- **Bulk actions** — "Accept all high-confidence" saves her time
- **Analytics must be visible from the dashboard** — not buried in settings

---

### CJM 2: Jake — Upload, Check, Fix, Download

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE        │ UPLOAD          │ WAITING       │ REVIEW          │ FIX & EXIT  │
├─────────────────────────────────────────────────────────────────────────────────┤
│              │                 │               │                 │             │
│ ACTIONS      │ Drags .pptx     │ Sees progress │ Scans slide     │ Clicks      │
│              │ onto upload     │ bar           │ strip for red   │ "Fix All"   │
│              │ zone            │               │ dots            │ Downloads   │
│              │                 │               │ Clicks worst    │ corrected   │
│              │                 │               │ slide to see    │ .pptx       │
│              │                 │               │ what's wrong    │             │
│              │                 │               │                 │             │
│ THINKING     │ "Please be      │ "How long     │ "OK 3 slides    │ "That was   │
│              │ fast"           │ is this going │ have issues.    │ way faster  │
│              │                 │ to take?"     │ Let me see      │ than asking │
│              │                 │               │ the worst one"  │ Maya"       │
│              │                 │               │                 │             │
│ FEELING      │ Impatient but   │ Anxious       │ Curious, then   │ Satisfied,  │
│              │ hopeful         │               │ relieved ("oh   │ slightly    │
│              │                 │               │ that's all?")   │ impressed   │
│              │                 │               │                 │             │
│ PAIN POINTS  │ "Don't make me  │ "If this takes│ "I don't        │ "Will the   │
│              │ fill out a      │ more than 30  │ understand      │ formatting  │
│              │ form first"     │ seconds I'm   │ 'Delta-E 12.3'  │ still look  │
│              │                 │ closing the   │ — just tell me   │ right when  │
│              │                 │ tab"          │ what to fix"    │ I open it?" │
│              │                 │               │                 │             │
│ KEY MOMENTS  │ Drop zone       │ < 10 second   │ "Fix All"       │ Opens PPTX  │
│ OF TRUTH     │ accepts file    │ wait or he    │ button is       │ — it looks  │
│              │ instantly       │ bounces       │ prominent and   │ right       │
│              │                 │               │ one-click       │             │
│              │                 │               │                 │             │
│ DESIGN       │ ZERO friction   │ Real-time     │ Issues in PLAIN │ Download    │
│ MANDATES     │ upload. No      │ progress.     │ ENGLISH not     │ starts      │
│              │ forms, no       │ Skeleton      │ jargon. Visual  │ immediately.│
│              │ config.         │ loading       │ before/after.   │ No email.   │
│              │ Drop = go.      │ states.       │ "Fix All" is    │ No account  │
│              │                 │               │ the hero CTA.   │ required to │
│              │                 │               │                 │ download.   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Critical Design Implications (Jake)
- **Upload must be instant** — drag, drop, done. No form fields, no ruleset selection (use org default)
- **Progress must feel fast** — skeleton states, not spinners. Show slides appearing one by one.
- **Issues in plain English** — "This blue is wrong. Should be this blue." Not "Delta-E 12.3 exceeds tolerance."
- **"Fix All" is the primary CTA** — bigger than everything else on the results page
- **Download is one click** — corrected PPTX, no intermediary steps

---

### CJM 3: Priya — Multi-Brand QA Pass

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE        │ SELECT BRAND   │ UPLOAD        │ DETAILED REVIEW  │ EXPORT      │
├─────────────────────────────────────────────────────────────────────────────────┤
│              │                │               │                  │             │
│ ACTIONS      │ Switches to    │ Uploads       │ Reviews each     │ Accepts 8/10│
│              │ "Acme Corp"    │ finished      │ issue one by one │ corrections │
│              │ ruleset from   │ deck for QA   │ Zooms into slide │ Edits 2     │
│              │ dropdown       │               │ to check details │ manually    │
│              │                │               │ Compares original│ Downloads   │
│              │                │               │ vs corrected     │ final PPTX  │
│              │                │               │                  │             │
│ THINKING     │ "Let me make   │ "This should  │ "The color swap  │ "92 DQS.   │
│              │ sure I'm       │ be clean but  │ is right but the │ That's my   │
│              │ checking       │ let's verify" │ font correction  │ standard."  │
│              │ against the    │               │ changed the      │             │
│              │ right brand"   │               │ hierarchy — I'll │             │
│              │                │               │ edit that one"   │             │
│              │                │               │                  │             │
│ FEELING      │ Focused,       │ Confident     │ Engaged,         │ Professional│
│              │ professional   │               │ critical-eye     │ pride       │
│              │                │               │ mode             │             │
│              │                │               │                  │             │
│ PAIN POINTS  │ "If switching  │ "I need to    │ "The correction  │ "I want to  │
│              │ brands is      │ know this is  │ preview must be  │ save this   │
│              │ slow, I'll     │ checking the  │ pixel-accurate   │ as a new    │
│              │ just use one"  │ RIGHT rules"  │ or I can't       │ version,    │
│              │                │               │ trust it"        │ not replace │
│              │                │               │                  │ the orig."  │
│              │                │               │                  │             │
│ DESIGN       │ Brand switcher │ Active brand  │ Side-by-side     │ "Save as    │
│ MANDATES     │ is persistent, │ shown clearly │ must be precise. │ new version"│
│              │ always visible │ during upload │ Per-issue accept │ option.     │
│              │ in nav or      │ and check     │ /edit/dismiss.   │ DQS badge   │
│              │ header.        │               │ Zoom to element. │ on export.  │
│              │                │               │ Edit-in-place.   │             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Critical Design Implications (Priya)
- **Brand switcher must be fast and always visible** — not buried in settings
- **Active brand must be shown during check** — she needs to know which rules are active
- **Correction view must support per-issue granularity** — accept/edit/dismiss per issue, not just "Fix All"
- **Edit-in-place for corrections** — she wants to tweak the AI's suggestion, not start over
- **Version awareness** — downloading should offer "new version" vs "replace original"
- **DQS score is a badge of honor** — show it prominently, she'll screenshot it for clients

---

## Design Principles (Derived from Personas)

1. **Speed is respect.** Jake will leave if anything takes more than 10 seconds. Design every flow for the impatient user first, then add depth for Priya.

2. **Plain English, always.** "This blue is wrong" not "Delta-E 12.3 exceeds configured tolerance threshold." Technical details available on hover/expand for Priya, hidden by default for Jake.

3. **The correction is the product.** The check results page is not the destination — the side-by-side correction view is. That's where the magic happens. That's where Jake clicks "Fix All" and Priya reviews each change.

4. **Trust through transparency.** Maya needs confidence scores and source references. Priya needs pixel-accurate previews. Jake needs the corrected PPTX to look right when he opens it in PowerPoint. Different trust mechanisms, same principle: show your work.

5. **Multi-brand is first-class.** Priya's workflow is not an edge case — it's the power user workflow. Brand switching must be fast, visible, and foolproof.
