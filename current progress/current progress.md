# FinCluster Research Dossier — Current Progress

**What we built, what broke, and what it means**
*A complete account of the FinCluster project — every decision, and the reason behind it.*

| | |
|---|---|
| **Period** | 2026-07-21 → 2026-09-07 |
| **Repository** | Hackathon-project-research @ `1b762b3` |
| **Researcher** | solo |
| **Status** | framing under revision |
| **Published version** | https://claude.ai/code/artifact/080bb147-1082-4172-aaf4-1f0a7018d2ce |

> Every figure in this document is drawn from a file in the research repository. No number here is an estimate.

---

## 01 · Jul 2026 — It started as a hackathon build `SHIPPED`

### English

FinCluster began as an MVP for a hackathon: a Mobile Financial Services transaction simulator. It classified each transaction as Heavy or Light, routed it across simulated nodes of differing capacity, and compared that against plain Round Robin. A Next.js dashboard showed live telemetry, node health, thermal failures, an operator review queue, and controlled retraining.

It worked. The hackathon ended. That code is still in the repository, and none of the research described below replaces it.

**Why this matters later:** The MVP is application history, not evidence. Every scientific claim in this dossier comes from work done afterwards — the hackathon demo proves nothing about the research questions.

### বাংলা

FinCluster প্রথমে একটা হ্যাকাথনের MVP হিসেবে তৈরি হয়েছিল — Mobile Financial Services (MFS) লেনদেনের একটা সিমুলেটর। এটি প্রতিটি ট্রানজেকশনকে Heavy বা Light হিসেবে ভাগ করত, আলাদা ক্ষমতার সিমুলেটেড নোডে পাঠাত, এবং সাধারণ Round Robin-এর সাথে তুলনা করত। Next.js ড্যাশবোর্ডে লাইভ টেলিমেট্রি, নোডের অবস্থা, থার্মাল ফেইলিওর, অপারেটর রিভিউ কিউ এবং নিয়ন্ত্রিত রিট্রেনিং দেখানো হতো।

এটা কাজ করেছিল। হ্যাকাথন শেষ হলো। সেই কোড এখনো রিপোজিটরিতে আছে, এবং নিচে বর্ণিত গবেষণা সেটার বিকল্প নয়।

**পরে কেন গুরুত্বপূর্ণ:** MVP হলো অ্যাপ্লিকেশনের ইতিহাস, প্রমাণ নয়। এই ডসিয়ারের প্রতিটি বৈজ্ঞানিক দাবি পরবর্তী কাজ থেকে এসেছে — হ্যাকাথন ডেমো গবেষণা-প্রশ্নের ব্যাপারে কিছুই প্রমাণ করে না।

---

## 02 · Aug 6 — A teacher asked whether it could go further `DECIDED`

### English

After the hackathon, a teacher suggested checking whether the project could be improved or turned into a paper. The first instinct was the natural one: make the classifier more accurate.

That instinct was abandoned within a day, for a reason that turned out to shape everything after it.

**Why accuracy was the wrong goal:** The Heavy/Light label was hand-written from transaction features — and then predicted from those same features. The model was being graded on its ability to rediscover a rule we had authored. High accuracy would have meant nothing. This is circularity, and no amount of tuning fixes it.

### বাংলা

হ্যাকাথনের পর একজন শিক্ষক পরামর্শ দিলেন — দেখা যাক প্রজেক্টটা আরও উন্নত করা যায় কিনা, বা এটা দিয়ে একটা পেপার লেখা যায় কিনা। প্রথম চিন্তাটা স্বাভাবিকই ছিল: ক্লাসিফায়ারের অ্যাকুরেসি বাড়ানো।

কিন্তু একদিনের মধ্যেই সেই পরিকল্পনা বাদ দেওয়া হলো, এবং কারণটা পরবর্তী সবকিছুকে নির্ধারণ করে দিয়েছে।

**অ্যাকুরেসি কেন ভুল লক্ষ্য ছিল:** Heavy/Light লেবেলটা আমরা নিজেরাই ট্রানজেকশন ফিচার থেকে হাতে বানিয়েছিলাম — তারপর সেই একই ফিচার দিয়েই সেটা প্রেডিক্ট করছিলাম। অর্থাৎ মডেলকে পরীক্ষা করা হচ্ছিল আমাদেরই লেখা নিয়ম আবার খুঁজে বের করার ক্ষমতা দিয়ে। বেশি অ্যাকুরেসির কোনো মানে থাকত না। একে বলে circularity, এবং যত টিউনিংই করা হোক, এটা ঠিক হয় না।

---

## 03 · Aug 7–10 — The target changed to something we could measure `PIVOT`

### English

Instead of predicting a label we invented, the project switched to predicting `service_time_ms` — the actual measured time a transaction takes to process on a controlled node. Real PaySim transaction attributes go in; a measured millisecond figure comes out.

PaySim provided the transaction distribution: 6,362,620 rows, 11 columns, five transaction types, zero missing values. But PaySim contains no processing time, so the ground truth had to be produced by running the transactions through a reference processor we control.

**Why measurement beats labelling:** A measured millisecond is observed, not authored. It can disagree with our expectations — and a target that can disagree with you is the minimum requirement for an honest experiment.

### বাংলা

নিজেদের বানানো লেবেল প্রেডিক্ট করার বদলে প্রজেক্ট এখন প্রেডিক্ট করবে `service_time_ms` — অর্থাৎ একটা নিয়ন্ত্রিত নোডে একটা ট্রানজেকশন প্রসেস হতে বাস্তবে যত সময় লাগে। ইনপুট হিসেবে যাবে আসল PaySim ট্রানজেকশনের বৈশিষ্ট্য; আউটপুট আসবে মাপা মিলিসেকেন্ড।

PaySim থেকে পাওয়া গেল ট্রানজেকশনের ডিস্ট্রিবিউশন: ৬৩,৬২,৬২০ সারি, ১১টি কলাম, পাঁচ ধরনের ট্রানজেকশন, কোনো মিসিং ভ্যালু নেই। কিন্তু PaySim-এ প্রসেসিং টাইম নেই, তাই ground truth তৈরি করতে হয়েছে আমাদের নিয়ন্ত্রণে থাকা একটা reference processor দিয়ে ট্রানজেকশনগুলো চালিয়ে।

**লেবেলের চেয়ে মাপা কেন ভালো:** মাপা মিলিসেকেন্ড পর্যবেক্ষণ করা হয়, বানানো হয় না। এটা আমাদের প্রত্যাশার সাথে দ্বিমত করতে পারে — আর যে টার্গেট আপনার সাথে দ্বিমত করতে পারে, সেটাই সৎ পরীক্ষার সর্বনিম্ন শর্ত।

---

## 04 · Aug 16 — Then measurement itself became the problem `REJECTED`

### English

The plan was to collect data and start modelling. Instead, the measurements refused to repeat. A full 100-transaction collection ran perfectly — 1,500 successful timings, 300 aggregate rows, no failures — and was still thrown away.

**v0.3 stability audit — repeated-run variation per node**

| Node | Median CV | Max CV | Pairs above 10% |
|---|---:|---:|---:|
| High | 1.67% | 20.79% | 12 / 100 |
| Low | 28.28% | 53.63% | 86 / 100 |
| Medium | 49.62% | 71.43% | 100 / 100 |

The same transaction on the same node produced wildly different times run to run. Medium was bimodal — clustering around 20 ms and again around 70–80 ms for identical work.

**Why a complete dataset was discarded:** A run that finishes without errors is not a valid dataset. If the target moves this much for identical inputs, any model trained on it learns scheduler noise, not transaction behaviour. Structural completeness and scientific validity are different tests, and this passed only the first.

### বাংলা

পরিকল্পনা ছিল ডেটা সংগ্রহ করে মডেলিং শুরু করা। কিন্তু মাপগুলো বারবার একই ফল দিচ্ছিল না। ১০০ ট্রানজেকশনের একটা পূর্ণ সংগ্রহ নিখুঁতভাবে চলল — ১,৫০০টি সফল টাইমিং, ৩০০টি অ্যাগ্রিগেট সারি, কোনো ব্যর্থতা নেই — তবুও সেটা বাতিল করা হলো।

একই নোডে একই ট্রানজেকশন প্রতিবার ভিন্ন ভিন্ন সময় নিচ্ছিল। Medium নোডে ফলাফল ছিল দ্বি-শিখর — একই কাজের জন্য কখনো প্রায় ২০ ms, কখনো ৭০–৮০ ms।

**সম্পূর্ণ ডেটাসেট কেন বাতিল করা হলো:** ত্রুটি ছাড়া শেষ হওয়া মানেই বৈধ ডেটাসেট নয়। একই ইনপুটে টার্গেট যদি এতটা নড়ে, তাহলে সেই ডেটায় ট্রেন করা মডেল ট্রানজেকশনের আচরণ শেখে না — শেখে শিডিউলারের নয়েজ। কাঠামোগত সম্পূর্ণতা আর বৈজ্ঞানিক বৈধতা আলাদা পরীক্ষা, আর এটা কেবল প্রথমটায় পাস করেছিল।

---

## 05 · Aug 17 — Finding out why the clock was lying `DIAGNOSED`

### English

Three weeks went into diagnosis. Shortening the CPU period from 100 ms to 10 ms helped but did not fix it. Node profiles were shifted from 25/50/100% CPU to 50/75/100%. Batches became internally stable — and then drifted *between* batches: the High node repeated a full run with all ten transactions slower, a systematic 11.24% shift.

Instrumenting the container with `cpu.stat` caught the mechanism in the act. During one High run, throttled periods rose from 1 to 136 — **135 of 341 observed periods, about 39.6%, were throttled** despite a nominal full-CPU quota. A follow-up check found the process could be scheduled across all 8 logical CPUs while holding only one CPU's worth of time budget.

**Why internal stability was not enough:** A batch can be tight within itself and still sit at the wrong absolute level. Measuring variation inside one batch cannot detect that; only comparing two independent batches can. This is the single most transferable lesson of the project.

### বাংলা

তিন সপ্তাহ গেল কারণ নির্ণয়ে। CPU period ১০০ ms থেকে ১০ ms করায় উন্নতি হলো, কিন্তু সমস্যা মিটল না। নোড প্রোফাইল ২৫/৫০/১০০% CPU থেকে বদলে ৫০/৭৫/১০০% করা হলো। ব্যাচগুলো ভেতর থেকে স্থিতিশীল হলো — কিন্তু এক ব্যাচ থেকে আরেক ব্যাচে সরে যেতে লাগল: High নোডে পুনরায় চালানো ব্যাচে দশটি ট্রানজেকশনই ধীর হলো, পদ্ধতিগতভাবে ১১.২৪% সরে গেল।

`cpu.stat` দিয়ে কনটেইনার পর্যবেক্ষণ করে কারণটা হাতেনাতে ধরা পড়ল। একটি High রানে throttled period ১ থেকে বেড়ে ১৩৬ হলো — **৩৪১টি পর্যবেক্ষিত পিরিয়ডের মধ্যে ১৩৫টি, প্রায় ৩৯.৬%, throttle হয়েছে**, যদিও কাগজে-কলমে পুরো একটি CPU বরাদ্দ ছিল। পরের পরীক্ষায় দেখা গেল, প্রসেসটি আটটি লজিক্যাল CPU-তেই চলতে পারছে, অথচ সময়ের বাজেট মাত্র একটি CPU-র সমান।

**ভেতরের স্থিতিশীলতা কেন যথেষ্ট ছিল না:** একটা ব্যাচ নিজের ভেতরে খুব সুসংহত হয়েও ভুল absolute লেভেলে বসে থাকতে পারে। এক ব্যাচের ভেতরের হেরফের মেপে সেটা ধরা যায় না; ধরতে হলে দুটি স্বাধীন ব্যাচ তুলনা করতে হয়। এটাই এই প্রজেক্টের সবচেয়ে হস্তান্তরযোগ্য শিক্ষা।

---

## 06 · Aug 29 — A rule written before the results arrived `GATE PASSED`

### English

Before running anything, a pass/fail rule was fixed in writing: two independent batches per node, median difference between them no more than 5%, and at most 2 of 10 transaction pairs differing by more than 10%. Then containers were pinned to a single logical CPU and thread limits set to 1.

**v0.6 decision gate — declared before the batches ran**

| Profile | Median A/B difference | Pairs above 10% | Verdict |
|---|---:|---:|---|
| Low 50% CPU | 6.18% | 2 | **Fail** |
| Low 60% CPU | 2.08% | 0 | Pass |
| Medium 75% CPU | 1.98% | 0 | Pass |
| High 100% CPU | 1.52% | 0 | Pass |

Low at 50% failed the rule and was not argued with — it was replaced by a 60% profile, which passed. The gate was then closed and the final collection began: 1,000 transactions, 15,000 raw timings, 3,000 transaction-node rows, split 700/150/150 by transaction with zero leakage, hashed and frozen with a snapshot of the code that produced it.

**Why the rule came first:** A threshold chosen after seeing results is not a threshold, it is a justification. Fixing the rule beforehand is what converts "the numbers looked acceptable" into evidence someone else can check.

### বাংলা

কিছু চালানোর আগেই একটা pass/fail নিয়ম লিখে ঠিক করা হলো: প্রতি নোডে দুটি স্বাধীন ব্যাচ, তাদের মধ্যকার median পার্থক্য ৫%-এর বেশি নয়, এবং ১০টি ট্রানজেকশন জোড়ার মধ্যে সর্বোচ্চ ২টিতে ১০%-এর বেশি পার্থক্য। এরপর কনটেইনারগুলোকে একটিমাত্র লজিক্যাল CPU-তে পিন করা হলো এবং থ্রেড লিমিট ১ করা হলো।

Low ৫০%-এ নিয়মটা ফেল করল, এবং সেটা নিয়ে তর্ক করা হয়নি — বদলে ৬০% প্রোফাইল নেওয়া হলো, যেটা পাস করল। এরপর গেট বন্ধ করে চূড়ান্ত সংগ্রহ শুরু হলো: ১,০০০ ট্রানজেকশন, ১৫,০০০ কাঁচা টাইমিং, ৩,০০০ ট্রানজেকশন-নোড সারি, ট্রানজেকশন অনুযায়ী ৭০০/১৫০/১৫০ ভাগ, কোনো leakage ছাড়া, হ্যাশসহ ফ্রিজ করা এবং যে কোড দিয়ে তৈরি তার স্ন্যাপশটসহ সংরক্ষিত।

**নিয়মটা কেন আগে লেখা হলো:** ফলাফল দেখার পর বেছে নেওয়া থ্রেশহোল্ড আসলে থ্রেশহোল্ড নয়, সেটা একটা সাফাই। আগে থেকে নিয়ম ঠিক করাই "সংখ্যাগুলো গ্রহণযোগ্য মনে হলো"-কে এমন প্রমাণে রূপান্তর করে যা অন্য কেউ যাচাই করতে পারে।

---

## 07 · Aug 30 — The models trained, and the result was hollow `DEGENERATE`

### English

With a defensible dataset in hand, regression screening finally ran. It produced a clean, high-scoring, and deeply uncomfortable answer.

**Validation screening — best model per feature set**

| Features | Best model | MAE (ms) | R² |
|---|---|---:|---:|
| type + node | RandomForest | **0.922** | 0.984 |
| + amount, balances, step | HistGradientBoosting | 0.997 | 0.981 |
| node alone | RandomForest | 5.735 | 0.528 |
| type + node *(no ML — lookup table)* | Median lookup | **0.898** | 0.984 |

Adding amount and balances made predictions *worse*. And a plain lookup table — no learning at all — beat every trained model.

The reason is visible the moment the training medians are laid out as a grid. Service time is a clean product of transaction type and node, and the type axis tracks the processor's workflow-module count exactly.

**The whole target — 15 cells, median ms (train split)**

| Type | Workflow modules | High | Medium | Low |
|---|---:|---:|---:|---:|
| CASH_IN | 2 | 21.17 | 27.79 | 34.94 |
| PAYMENT | 3 | 24.60 | 31.61 | 39.84 |
| CASH_OUT | 4 | 28.01 | 36.89 | 46.27 |
| DEBIT | 5 | 31.74 | 40.53 | 51.48 |
| TRANSFER | 6 | 35.41 | 45.82 | 57.83 |

> **THE CORE FINDING**
>
> The reference processor sets workload from transaction type alone: 80,000 shared PBKDF2 iterations plus 20,000 per workflow module — 2 for CASH_IN rising to 6 for TRANSFER. The transaction *amount* never touches compute cost.
>
> So `service_time_ms` is a 5 × 3 lookup **by construction**. The prediction task was decided by the design of the workload generator, not by anything a model could discover. RQ1 — "which model predicts service time best" — cannot be meaningfully answered on this data.

**Why this is worth reporting rather than hiding:** The failure is precise, mechanically explained, and supported by an ablation and a non-ML baseline. That is a stronger scientific object than a leaderboard of near-identical R² scores would have been.

### বাংলা

নির্ভরযোগ্য ডেটাসেট হাতে নিয়ে অবশেষে regression screening চালানো হলো। ফলাফল এল পরিষ্কার, উঁচু স্কোরের, এবং গভীরভাবে অস্বস্তিকর।

amount আর balance যোগ করায় প্রেডিকশন বরং *খারাপ* হলো। আর একটা সাধারণ lookup table — কোনো লার্নিং ছাড়াই — সব ট্রেইনড মডেলকে হারিয়ে দিল।

ট্রেনিং median-গুলো গ্রিড আকারে সাজালেই কারণটা চোখে পড়ে। service time হলো ট্রানজেকশন টাইপ আর নোডের একটা পরিচ্ছন্ন গুণফল, আর টাইপ-অক্ষটা হুবহু প্রসেসরের workflow module সংখ্যা অনুসরণ করে।

> **মূল আবিষ্কার**
>
> Reference processor কেবল ট্রানজেকশন টাইপ থেকেই কাজের পরিমাণ ঠিক করে: ৮০,০০০ সাধারণ PBKDF2 iteration, আর প্রতি workflow module-এ ২০,০০০ — CASH_IN-এ ২টি থেকে TRANSFER-এ ৬টি। ট্রানজেকশনের *amount* কম্পিউট খরচে কোনো প্রভাবই ফেলে না।
>
> ফলে `service_time_ms` আসলে একটা ৫ × ৩ lookup — **গঠনগতভাবেই**। প্রেডিকশনের কাজটা নির্ধারিত হয়ে গিয়েছিল workload generator-এর ডিজাইন দিয়ে, মডেলের আবিষ্কার করার মতো কিছু দিয়ে নয়। RQ1 — "কোন মডেল service time সবচেয়ে ভালো প্রেডিক্ট করে" — এই ডেটায় অর্থপূর্ণভাবে উত্তর দেওয়া যায় না।

**এটা লুকানোর বদলে প্রকাশ করা কেন জরুরি:** ব্যর্থতাটা সুনির্দিষ্ট, যান্ত্রিকভাবে ব্যাখ্যাযোগ্য, এবং একটা ablation ও একটা non-ML baseline দিয়ে সমর্থিত। প্রায় একই রকম R² স্কোরের তালিকার চেয়ে এটা অনেক শক্তিশালী বৈজ্ঞানিক বস্তু।

---

## 08 · Aug 30 — Adding queue state put the problem back `PRELIMINARY`

### English

If the workload generator makes service time trivial, the fix is to predict something the generator does not fully determine. The `queue_aware_v1` experiment changed the target to `completion_time_ms` — queue wait plus service time — and gave the model two things a router can actually observe before routing: active workers and queue length.

**Queue-aware screening — validation**

| Features | MAE (ms) | R² |
|---|---:|---:|
| type + node + workers + queue length | **2.343** | 0.987 |
| type + node | 22.183 | 0.135 |

Queue state carries roughly ten times the predictive weight. More importantly for routing: the High node is **not** the best choice 31.9% of the time. The routing decision stops being a constant.

**Why this is promising but not yet a result:** The queue simulator is driven by service times drawn from our own training split, so the model is partly predicting its own generator. That must be stated openly — it is a milder version of the circularity the project escaped in step 02, and a reviewer will look for it.

### বাংলা

Workload generator যদি service time-কে তুচ্ছ করে দেয়, তাহলে সমাধান হলো এমন কিছু প্রেডিক্ট করা যা generator পুরোপুরি নির্ধারণ করে না। `queue_aware_v1` পরীক্ষায় টার্গেট বদলে করা হলো `completion_time_ms` — queue wait যোগ service time — এবং মডেলকে দেওয়া হলো এমন দুটি তথ্য যা রাউটার রাউটিংয়ের আগেই দেখতে পায়: active worker সংখ্যা আর queue length।

Queue state প্রায় দশ গুণ বেশি ভবিষ্যদ্বাণী-ক্ষমতা বহন করে। রাউটিংয়ের জন্য আরও গুরুত্বপূর্ণ: ৩১.৯% ক্ষেত্রে High নোড সেরা পছন্দ **নয়**। রাউটিং সিদ্ধান্তটা আর ধ্রুবক থাকে না।

**এটা আশাব্যঞ্জক কিন্তু এখনো ফলাফল নয় কেন:** Queue simulator চালানো হয়েছে আমাদের নিজেদের ট্রেনিং স্প্লিট থেকে নেওয়া service time দিয়ে, ফলে মডেল আংশিকভাবে নিজের generator-কেই প্রেডিক্ট করছে। এটা খোলাখুলি বলতে হবে — ধাপ ০২-এ যে circularity থেকে প্রজেক্ট বেরিয়ে এসেছিল, এটা তারই একটা মৃদু সংস্করণ, এবং রিভিউয়ার এটা খুঁজবেন।

---

## 09 · Sep 7 — What a first literature check says `CURRENT`

### English

No thorough literature review has been done — that is the current gap, and the immediate next task. A preliminary search returns three signals worth acting on.

**Container CPU throttling is thoroughly documented already.** Including the specific mitigation of shortening the CFS period, which cost days of independent diagnosis in August. That work was verification, not discovery, and cannot be presented as novel.

**The degeneracy pattern has a name but not this application.** Shortcut learning is well studied, and at least one recent paper reports synthetic benchmarks whose answers were recoverable by trivial baselines — but in a different domain. No prior work was found showing this for container-based transaction service-time measurement with the mechanism traced to the workload generator.

**ML for payment routing exists, but targets different quantities** — provider success rates and settlement time, not compute service time across heterogeneous nodes.

**Why this changes the paper's shape:** The measurement protocol cannot be the contribution; that ground is taken. The protocol becomes the apparatus that makes a finding trustworthy, and the degeneracy result becomes the claim.

*Caveat: this was a preliminary web search, not a literature review. It is enough to say the direction is not obviously dead — not enough to defend a novelty statement.*

### বাংলা

এখনো পূর্ণাঙ্গ literature review করা হয়নি — এটাই বর্তমান ঘাটতি এবং পরবর্তী তাৎক্ষণিক কাজ। প্রাথমিক অনুসন্ধানে তিনটি ইঙ্গিত পাওয়া গেছে যেগুলোর ভিত্তিতে কাজ করা দরকার।

**Container CPU throttling নিয়ে ইতিমধ্যেই বিস্তারিত কাজ আছে।** এর মধ্যে CFS period ছোট করার নির্দিষ্ট সমাধানটিও আছে, যেটা বের করতে আগস্টে কয়েকদিন লেগেছিল। সেই কাজটা ছিল যাচাই, আবিষ্কার নয় — তাই একে নতুন বলে দাবি করা যাবে না।

**Degeneracy প্যাটার্নটির নাম আছে, কিন্তু এই প্রয়োগে নয়।** Shortcut learning নিয়ে ভালো গবেষণা আছে, এবং সাম্প্রতিক অন্তত একটি পেপারে এমন synthetic benchmark-এর কথা আছে যেগুলোর উত্তর তুচ্ছ baseline দিয়েই বের করা যেত — তবে ভিন্ন ক্ষেত্রে। কনটেইনার-ভিত্তিক ট্রানজেকশন service-time মাপার ক্ষেত্রে, যেখানে কারণটা workload generator পর্যন্ত চিহ্নিত করা হয়েছে — এমন পূর্ববর্তী কাজ পাওয়া যায়নি।

**পেমেন্ট রাউটিংয়ে ML আছে, কিন্তু লক্ষ্য ভিন্ন** — প্রোভাইডারের success rate ও settlement time, ভিন্ন ক্ষমতার নোডে compute service time নয়।

**এতে পেপারের আকার কেন বদলায়:** Measurement protocol-টা মূল অবদান হতে পারবে না; সেই জায়গা আগেই দখল হয়ে আছে। Protocol হবে সেই যন্ত্র যা আবিষ্কারটিকে বিশ্বাসযোগ্য করে, আর degeneracy-র ফলাফলটাই হবে দাবি।

*সতর্কতা: এটা ছিল প্রাথমিক ওয়েব সার্চ, পূর্ণাঙ্গ literature review নয়। এটুকু বলা যায় যে দিকটা স্পষ্টভাবে মৃত নয় — কিন্তু novelty-র দাবি রক্ষা করার জন্য যথেষ্ট নয়।*

---

## 10 · Next — Three papers are hiding in this work `DECISION`

### English

Given a solo researcher with under two months and open-access literature only, these are the options and the honest verdict on each.

| | Framing | Verdict |
|---|---|---|
| **A** | Which model predicts service time best? *(the original RQ1)* | Already answered, and the answer is a lookup table. Fixing it means redesigning the processor and re-collecting 15,000 measurements — three weeks that do not exist. |
| **B** | **The degeneracy result, with the protocol as apparatus** | **RECOMMENDED.** Every experiment is finished and hash-verified. Nothing left but writing and positioning. The one candidate that fits the timeline. |
| **C** | Queue-aware completion-time routing | The better science, and the natural home for the routing questions. But it needs simulator validation, three routing baselines and system-level evaluation. Too large for now — it becomes the future-work section. |

**Working framing for Option B:** *a controlled measurement study showing that node-aware transaction service-time prediction becomes degenerate when the reference workload is generated from the transaction category.*

**Why the negative result is the strongest asset:** It is the only part of this project that is both finished and not already in the literature. Everything else is either well-trodden ground or unfinished work.

### বাংলা

একজন একক গবেষক, দুই মাসের কম সময়, এবং কেবল open-access সাহিত্য — এই বাস্তবতায় বিকল্পগুলো এবং প্রতিটির সৎ মূল্যায়ন নিচে।

**বিকল্প A — কোন মডেল service time সবচেয়ে ভালো প্রেডিক্ট করে?** মূল RQ1। উত্তর ইতিমধ্যেই পাওয়া গেছে, আর উত্তরটা হলো একটা lookup table। ঠিক করতে হলে প্রসেসর নতুন করে ডিজাইন করে ১৫,০০০ মাপ আবার নিতে হবে — সেই তিন সপ্তাহ হাতে নেই।

**বিকল্প B — প্রস্তাবিত।** Degeneracy-র ফলাফল, আর protocol থাকবে যন্ত্র হিসেবে। সব পরীক্ষা শেষ ও hash দিয়ে যাচাই করা। বাকি আছে কেবল লেখা আর অবস্থান নির্ধারণ। সময়সীমার মধ্যে একমাত্র সম্ভব বিকল্প।

**বিকল্প C — Queue-aware completion-time রাউটিং।** বিজ্ঞান হিসেবে বেশি ভালো, এবং রাউটিং প্রশ্নগুলোর স্বাভাবিক ঠিকানা। কিন্তু এর জন্য দরকার simulator যাচাই, তিনটি রাউটিং baseline এবং system-level মূল্যায়ন। এখনকার জন্য অনেক বড় — এটা future work অংশে যাবে।

**নেতিবাচক ফলাফলই কেন সবচেয়ে বড় সম্পদ:** এই প্রজেক্টে এটাই একমাত্র অংশ যা একইসাথে সম্পূর্ণ এবং সাহিত্যে এখনো অনুপস্থিত। বাকি সবকিছু হয় বহু-চর্চিত জমি, নয়তো অসমাপ্ত কাজ।

---

## 11 · Standing rules — What must not happen next

### English

Four constraints hold regardless of which option is chosen.

1. **The test set stays sealed.** 150 transactions, 450 rows, never loaded. It is used once, at the end, after the research questions are frozen — not for tuning, not for checking whether results look better.
2. **The frozen dataset is not modified.** Including the 48 outlier-flagged rows, which stay in. Removing inconvenient rows after seeing results is the same error as choosing a threshold after seeing results.
3. **The split is not reshuffled.** Not if model numbers disappoint.
4. **Diagnostic evidence is preserved.** All v0.3, v0.4 and v0.5 data stays in the archive. The failures are part of the record, and in Option B they are part of the argument.

### বাংলা

কোন বিকল্প বেছে নেওয়া হোক না কেন, চারটি শর্ত বহাল থাকবে।

১. **Test set সিল করা থাকবে।** ১৫০ ট্রানজেকশন, ৪৫০ সারি, কখনো লোড করা হয়নি। গবেষণা-প্রশ্ন চূড়ান্ত হওয়ার পর, একেবারে শেষে, একবারই ব্যবহার হবে — টিউনিংয়ের জন্য নয়, ফলাফল ভালো দেখাচ্ছে কিনা দেখার জন্যও নয়।
২. **Frozen ডেটাসেট বদলানো হবে না।** outlier চিহ্নিত ৪৮টি সারিসহ, যেগুলো থেকে যাবে। ফলাফল দেখার পর অসুবিধাজনক সারি বাদ দেওয়া আর ফলাফল দেখার পর থ্রেশহোল্ড বাছাই — একই ভুল।
৩. **Split আবার এলোমেলো করা হবে না।** মডেলের সংখ্যা হতাশ করলেও নয়।
৪. **Diagnostic প্রমাণ সংরক্ষিত থাকবে।** v0.3, v0.4 ও v0.5-এর সব ডেটা আর্কাইভে থাকবে। ব্যর্থতাগুলো রেকর্ডের অংশ, আর বিকল্প B-তে সেগুলো যুক্তিরও অংশ।

---

## Evidence index

Every figure above traces to a file in this repository.

| Claim | File |
|---|---|
| v0.3 stability audit | `archive/2026-08-17_pre_validation_v05/` |
| Throttling instrumentation | `results/instrumented_high_v05/` |
| v0.6 gate results | `results/v06_pinned_analysis/v06_reproducibility_summary.csv` |
| Low 60% gate pass | `results/v06_low60_analysis/low60_reproducibility_summary.csv` |
| Frozen dataset and split | `data/final_training_data_v1/FREEZE_REPORT.txt` |
| Regression screening | `results/regression_v1/ablation_best_per_feature_set.csv` |
| 15-cell grid and lookup baseline | `results/regression_v1/type_node_diagnostic/` |
| Queue-aware screening | `results/queue_aware_v1/` |
| Processor workload design | `scripts/reference_processor.py` |
| Candidate framing analysis | `notes/contribution_inventory_v0.1.md` |

---

**Next action:** a targeted literature review across container performance variability, execution-time prediction, benchmark degeneracy, and payment routing — producing `literature/literature_review.csv` and a synthesis with a defensible gap statement.

*Dossier v0.1 · compiled 2026-09-07 from repository evidence at commit `1b762b3`*
