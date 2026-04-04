# CEO Dashboard Walkthrough — Presentation Script

**Project:** Carnegie ROI Dashboard for Central Washington University (CWU)
**Presenter:** Matheus Abrantes, Data Visualization Specialist
**Audience:** Gary (CEO), executives
**Duration:** 30 minutes
**Date:** Prepared April 2026

---

## Pre-Meeting Checklist

- [ ] Dashboard is live and loaded in browser — no login screens during demo
- [ ] Open each page once beforehand so data is cached and loads fast
- [ ] Browser zoom set to 100%, fullscreen mode ready (F11)
- [ ] Second monitor or notes app open with this script (not visible to audience)
- [ ] Water nearby
- [ ] Slack/Teams/notifications OFF
- [ ] Screen sharing tested in the meeting tool
- [ ] Bookmark or tab order matches walkthrough order (7 tabs)
- [ ] Know the latest numbers: current Net Deposits, biggest YoY change, top-performing creative
- [ ] Backup plan: if dashboard is down, have 3-4 screenshots ready in a slide deck

---

## 1. Opening (2 minutes)

### Hook — Start with the value (30 seconds)

"Good morning everyone. Gary, thank you for making time for this.

Here is the core idea. Right now, when a partner like CWU asks 'How is our enrollment marketing performing?' — the answer lives in five different reports, three different tools, and it takes days to pull together. This dashboard puts that answer in one place, in real time, with no waiting."

*[Pause 2 seconds]*

### Context — What this is (30 seconds)

"What you are about to see is a working prototype of a DIY ROI Dashboard built for CWU. It connects directly to our data in BigQuery and updates automatically. The partner would see this in their browser — no PDFs, no static slides."

### Roadmap — What they will see (30 seconds)

"I will walk you through three things today. First, the enrollment funnel — where CWU stands from inquiry to deposit. Second, digital performance — how campaigns are driving those results month over month. And third, a few additional views that give geographic and creative detail. The whole walkthrough will take about twenty minutes, and then I want to hear your questions."

*[Pause. Make eye contact. Then share screen.]*

---

## 2. Dashboard Walkthrough (20 minutes)

---

### Page 1 — ROI Overview (3 minutes)

**What to show:** KPI strip across the top (Inquiries through Net Deposits), YoY comparison cards, funnel visual.

**Script:**

"This is the first thing a partner sees when they open the dashboard. Across the top, you have six numbers that tell the full enrollment story — from Inquiries all the way to Net Deposits.

Each card shows the current count and the year-over-year change. So right away, without clicking anything, a VP of Enrollment can see whether they are ahead or behind last year.

Let me point out Net Deposits here on the right — this is the number that matters most to the partner. Everything else in the dashboard supports this number."

*[Pause. Let them absorb the layout.]*

"Below the KPIs, you can see the funnel trending over time. The filters on the left let you slice by term, program level, or student type. I will not go deep into filters right now — just know they are consistent across every page."

**Transition:**

"So that is the big picture. Now let me show you what happens when a partner asks: 'Which programs are driving these numbers?'"

---

### Page 2 — Funnel Deep Dive: Program Breakdown (3 minutes)

**What to show:** Program-level table or chart with trending lines vs goals.

**Script:**

"This page breaks the funnel down by program. Each row shows a specific program — for example, Graduate Education or Undergraduate Business — with its own inquiry-to-deposit numbers.

The key feature here is the goal comparison. The partner sets enrollment goals by program, and this view shows them exactly where each program stands against that goal. Green means on track, red means behind.

This is the kind of detail that used to require a custom report request. Now the partner has it on demand."

*[Pause.]*

"One thing I want to highlight — this is the same data, same filters, just a different lens. We are not switching tools. We are not opening a spreadsheet. Everything stays connected."

**Transition:**

"So we have covered the enrollment side. Now I want to shift to the marketing side — how are digital campaigns actually performing?"

---

### Page 3 — Digital Performance: Overview MoM (3 minutes)

**What to show:** Monthly trend lines for key digital metrics, cost per interaction, interaction volume.

**Script:**

"This is where we connect marketing activity to enrollment outcomes. You are looking at month-over-month trends for digital campaign performance.

The top row shows volume — impressions, clicks, key interactions. The bottom row shows efficiency — cost per click, cost per interaction. The partner can see both at the same time.

What makes this valuable is the time dimension. A single month can be misleading. But when you see three, six, nine months of trend data, you can spot whether performance is improving or declining — and you can act on it before the term ends."

*[Pause.]*

"Notice the layout. We kept it clean on purpose. No clutter. The partner should be able to glance at this page in ten seconds and know if things are moving in the right direction."

**Transition:**

"Month-over-month is great for recent trends. But partners also want to know: 'How does this year compare to last year?' That is the next page."

---

### Page 4 — Digital Performance: Overview YoY (2 minutes)

**What to show:** Year-over-year comparison of the same digital metrics.

**Script:**

"Same metrics, different time frame. This page puts the current year side by side with the previous year so the partner can see longer-term momentum.

This is especially useful in enrollment marketing because there are natural seasonal patterns. August looks different from February. The YoY view accounts for that by comparing the same months across years.

I will keep moving — the structure is the same as the previous page, just with a year-over-year lens."

**Transition:**

"Now let me go one level deeper into the interactions themselves."

---

### Page 5 — Digital Performance: Interactions (3 minutes)

**What to show:** Interaction categories broken down by funnel stage, volume by type.

**Script:**

"This page answers the question: 'What are prospective students actually doing when they engage with our campaigns?'

We break interactions into categories — things like form submissions, content views, video plays — and we map them to the enrollment funnel stage. So you can see which interactions happen at the top of the funnel versus which ones happen closer to application or deposit.

This matters because not all interactions are equal. A video play is awareness. A form submission is intent. This view helps the partner — and our own strategists — understand the quality of engagement, not just the quantity."

*[Pause.]*

**Transition:**

"The last digital page I want to show you is about the creative itself — what are the actual ads that are running, and how are they performing?"

---

### Page 6 — Digital Performance: Creative (3 minutes)

**What to show:** Creative performance table, search term data, ad preview images.

**Script:**

"This is one of my favorite pages. On the left, you see performance data for each creative asset — click-through rate, cost, interactions. On the right, you see the actual ad preview.

This is powerful for two reasons. First, the partner can see exactly what is running in market without logging into an ad platform. Second, our own strategists can spot patterns — which headlines work, which images perform, which formats drive the most engagement.

You will also notice a search terms section. This shows what prospective students are actually searching for when they find CWU ads. That is direct insight into student intent."

*[Pause. Give them a moment to look at the creative previews.]*

**Transition:**

"Those are the core pages. Let me quickly mention three more views that round out the dashboard."

---

### Page 7 — Quick Mention of Remaining Pages (3 minutes)

**What to show:** Click through Geography, Insights, and Lead Source pages briefly. Do not go deep.

**Script:**

"There are three additional pages I want you to know about, and I will keep this brief.

First — Geography. This page shows where inquiries and applications are coming from on a map. CWU can see which states and regions are producing the most interest. This is useful for territory planning and for understanding where digital spend is having the most reach.

Second — Insights. This is a summary page that pulls out key takeaways automatically. Think of it as the executive summary the partner can share with their cabinet without needing to open the full dashboard.

Third — Lead Source. This breaks down where students are coming from — organic search, paid campaigns, direct, referral. It helps the partner understand which channels are doing the heavy lifting.

I am not going deeper into these today, but they are built and functional. Happy to walk through any of them in detail if you are interested."

---

## 3. Wrap-Up (3 minutes)

**Script:**

"Let me step back and summarize what you just saw.

This dashboard does three things for our partners.

One — it gives them real-time visibility into enrollment performance, from inquiry to deposit, without waiting for a report.

Two — it connects marketing activity to enrollment outcomes in one place, so they can see the return on their investment with Carnegie.

Three — it is self-service. The partner can filter, explore, and share this on their own. That saves our team time and gives the partner more confidence in our work.

This is a working product, built on real CWU data. The next step is to get feedback from the CWU team, refine based on what they need most, and then evaluate how this model could scale to other partners.

I will be doing a deeper walkthrough with Mish and Alexa right after this, so any technical or strategic feedback you have — I would love to hear it now or pass it along through them."

*[Pause. Open posture. Wait for response.]*

"Thank you for your time today. I am happy to take any questions."

---

## 4. Anticipated Questions and Suggested Answers

### "How long did this take to build?"

"The core dashboard took about [X weeks] of focused development. The data pipeline was the biggest piece — connecting to BigQuery, cleaning the data, and making sure the numbers match what our teams already report. The front end was built in Shiny for Python, which lets us move fast and iterate quickly."

### "Can this scale to other partners?"

"Yes, that is the goal. The data structure is designed to be reusable. Once we have the data pipeline for a new partner, the dashboard layers on top of it. The layout, the pages, the filters — those stay consistent. What changes is the data underneath."

### "How does this compare to what we give partners today?"

"Today, partners get static reports — usually PDFs or slide decks — delivered on a schedule. This dashboard is live, interactive, and always current. It does not replace the strategic narrative our teams provide, but it gives the partner a way to check in on their own between those conversations."

### "What does the partner actually see? Is this the same view?"

"Yes. What I showed you is the partner-facing view. There is no separate internal version. The idea is that we and the partner are looking at the same numbers, which builds trust and reduces back-and-forth."

### "What about data accuracy? How do we know these numbers are right?"

"The dashboard pulls directly from our BigQuery data warehouse, which is the same source our analytics team uses for reporting. We validate the numbers against existing reports during setup. If there is ever a discrepancy, we can trace it back to the source query."

### "What technology is this built on?"

"It is built in Shiny for Python, an open-source framework from Posit. The data layer connects to BigQuery. It runs in a browser — no installs needed. If we need to, we can host it on our own infrastructure or on a cloud service."

### "What is the cost to maintain this?"

"The ongoing cost is mostly data infrastructure — BigQuery compute and hosting. The dashboard code itself does not require licensing fees. Maintenance is about keeping the data pipeline healthy and updating the dashboard when partners request new features."

---

## 5. Presenter Notes

### Pacing

- Speak slower than you think you need to. Executives process while you talk.
- After each page transition, pause for 3 seconds before speaking. Let them read the screen first.
- Target roughly 1 page every 3 minutes. If you are ahead of schedule, that is fine — use the extra time for Q&A.
- If you fall behind, skip the deep detail on Pages 4 and 5. Mention them briefly and move to Creative (Page 6), which has the most visual impact.

### Delivery

- Use short sentences. One idea per sentence.
- Avoid filler words: "basically," "actually," "kind of," "sort of." Replace with a pause.
- When you do not know an answer, say: "That is a great question. I want to give you an accurate answer, so let me follow up on that after this meeting."
- Do not apologize for your English. You will sound more confident without it.
- Use "you" and "your" when talking about what the partner or Gary's team gets. It keeps the language personal.

### Confidence

- You built this. You know it better than anyone in the room.
- Gary is here to see the product, not to test you. This is a demo, not a defense.
- If something breaks during the demo, stay calm. Say: "Let me refresh that — live demos always keep you honest." Then move on.
- Stand by your design decisions. If someone suggests a change, say: "That is a good idea — I will look into that." Do not redesign on the spot.

### Body Language (if on camera)

- Sit up straight. Hands visible.
- Look at the camera when speaking, at the screen when showing.
- Nod when someone asks a question — it shows you are listening.
- Smile at the opening and closing. It sets the tone.

### Pronunciation Prep

Practice these words out loud before the meeting:

- "Inquiries" (in-KWIR-eez)
- "Deposits" (deh-PAH-zits)
- "Funnel" (FUH-nuhl)
- "Creative" (kree-AY-tiv)
- "Scalable" (SKAY-luh-buhl)
- "Discrepancy" (dis-KREP-uhn-see)
- "Infrastructure" (IN-fruh-struk-chur)
- "Visibility" (viz-uh-BIL-ih-tee)

### Timing Guide

| Section | Duration | Cumulative |
|---|---|---|
| Opening | 2 min | 2 min |
| Page 1 — ROI Overview | 3 min | 5 min |
| Page 2 — Program Breakdown | 3 min | 8 min |
| Page 3 — Digital MoM | 3 min | 11 min |
| Page 4 — Digital YoY | 2 min | 13 min |
| Page 5 — Interactions | 3 min | 16 min |
| Page 6 — Creative | 3 min | 19 min |
| Page 7 — Remaining Pages | 3 min | 22 min |
| Wrap-Up | 3 min | 25 min |
| Q&A Buffer | 5 min | 30 min |

---

*Last updated: April 4, 2026*
