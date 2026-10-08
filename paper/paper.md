# Building System 1: How Language Agents Construct and Use Classifiers Under an Information Budget

*Anonymous ACL submission*

## Abstract

Agentic systems often use a reasoning model both as the controller and as
the worker that performs repeatable judgements, spending its compute on
work a fast classifier could do. We argue that such classifiers should act
as the agent's System 1, with the agent as System 2 that builds, monitors
and updates them. A fine-tuned classifier could fill this role, but its
decision rule is hidden in its weights, and changing it means relabelling
and retraining. A natural-language (NL) classifier, composed of questions
put to a small judgement model such as Jev, can be read and edited by the
agent and its user. We first ask whether agent-built NL classifiers are as
effective as fine-tuned ones: given the same training labels, an Opus
builder matches or beats RoBERTa fine-tuned on them on all six of our
tasks, and its classifiers keep their scores, unchanged, when three other
System 1 models answer their questions, including one forty times as
expensive. We then study the more common case for an agent, where no labelled
data exists: the agent receives a brief description and unlabelled data,
and spends a budget of a simulated user's time on labels and on questions
about the definition. With 100 points, about 50 labels, it beats zero-shot
wherever the user has something to teach, and on two tasks it beats an
encoder fine-tuned on twenty times as many labels. The best strategy
depends on where the missing knowledge lies: following the classifier's
uncertainty works when the definition is in the text, and fails when it is
a private policy that must be probed directly. A small builder gains
nothing from plentiful labels, suggesting that acting on evidence, more
than access to it, limits what an agent can build.

## 1 Introduction

The field of Natural Language Processing has been driven by the rise of ever more capable models, and intelligent agentic systems that communicate in natural language are becoming a reality [Yao et al. 2023; Schick et al. 2023; Wang et al. 2024]. In these systems a highly capable model that can reason serves as the controller: it plans, calls tools, and decides what to do next. Often, however, the same model also serves as the worker, performing repeatable, well-understood tasks such as routing a message, checking whether a record matches a filter, or deciding whether an email needs a reply, one input at a time. Each such call spends the compute and latency of a reasoning model, which results in a waste of compute and of intelligence.

Human cognition offers a parallel in its two modes of thinking
[Kahneman 2011]: System 1, fast and automatic, and System 2, slow and
deliberate. A new task first takes the effort of System 2; with practice,
System 1 learns to do it, while System 2 monitors it and steps in when it
errs. The distinction has been proposed as a template for AI [Bengio 2019;
Booch et al. 2021], but most agentic systems never make the hand-off: the
reasoning model performs every judgement itself, however often it recurs.

The recent resurgence of classification models such as Jev [TypeSafe 2026] offers an interesting option for the role of System 1 in an agentic system. They answer a precisely stated question about an input, a choice among options or a yes/no judgement, with a typed answer and a probability, quickly, cheaply and consistently. Encoding a classifier in natural language rather than in parameters, as traditional classifiers fine-tuned from encoders such as BERT and RoBERTa do [Devlin et al. 2019; Liu et al. 2019], is a clear advantage for a system controlled by an agent. Both the agent and the user can interpret the rules of such a **natural-language (NL) classifier**, build and iterate on it, and the system needs no traditional training loop. Put succinctly: the agent can write a decision policy for a classifier, the user can read it, and a change of policy is an edit to a sentence.

In this paper, we explore whether a highly capable model given an NL classifier as a subroutine can act as System 2: interpret labels and user feedback to build a classifier that performs its repeatable judgements. This translates into three research questions:

- **RQ1:** given training labels, can an agent build NL classifiers as
effective as a supervised classifier trained on the same labels?
- **RQ2:** without labelled data, how well can an agent build them from a task description, unlabelled data and a short user interview?
- **RQ3:** which interview strategies work well, and does the answer depend on the task?

We find that a frontier model can use an NL classifier effectively as a System 1 routine. On six classification tasks, a frontier model (Claude Opus 5.5) using Jev matches or beats a fine-tuned RoBERTa when both are given a full labelled set. With a budget equivalent to about 50 labels of a simulated user's time, it beats zero-shot wherever the user has something to teach, and on two tasks beats RoBERTa fine-tuned on twenty times as many labels. The best strategy depends on where the missing knowledge lies: following the classifier's uncertainty works when the definition is in the text, and fails when it is a private policy the agent must discover. We also find that other available options can play the role of System 1 with little difference in accuracy, but the System 2 model is important: the performance deteriorates with less capable models in the same model family.

We start with a review of related work in Section 2. Section 3 formulates budgeted building with a simulated user, and Section 4 describes the toolkit and builder. We describe the experiments in Section 5 and discuss the results in Section 6. Finally, we conclude with a discussion of monitoring and updating deployed classifiers as part of a functioning agentic system in Section 7.

## 2 Related Work

**Agents and the cost of reasoning.** Language agents use a reasoning model to plan, call tools and act [Yao et al. 2023; Schick et al. 2023; Wang et al. 2024]. Several lines of work reduce the cost of such systems by sending easy inputs to cheaper models, through cascades and routers between language models [Chen et al. 2023; Ong et al. 2024], or by distilling a large model's behaviour into a small one [Hsieh et al. 2023]. Dual-process architectures pair a fast and a slow component explicitly [Bengio 2019; Booch et al. 2021; Lin et al. 2023]. In these systems the fast component is a smaller generator or a trained network. We instead make it a classifier whose definition is text, which the slow component writes and can later revise.

**Classifiers defined in natural language.** Zero-shot classification casts labels as natural-language hypotheses or prompts [Yin et al. 2019; Schick and Schütze 2021], and instruction-tuned models follow task definitions written for people [Mishra et al. 2022]. Natural-language explanations and labelling functions have also been used to train conventional classifiers [Hancock et al. 2018; Ratner et al. 2017]. In our setting the definition is not a means of producing training data but the classifier itself, executed by a small judgement model such as Jev [TypeSafe 2026].

**Prompt optimisation.** Methods that search over instructions, such as APE, ProTeGi, OPRO and DSPy, improve a prompt against a labelled set [Zhou et al. 2023; Pryzant et al. 2023; Yang et al. 2024; Khattab et al. 2024]. Our setting with every training label is closest to this work, with a general agent in place of a fixed search procedure. Without labels, these methods have nothing to optimise against, and the builder must first acquire the evidence.

**Active learning, machine teaching and elicitation.** Active learning chooses which examples a person should label [Settles 2009], and some variants also ask the annotator about features, at a different cost [Raghavan et al. 2006; Druck et al. 2009]. Machine teaching shifts the focus to how a person transfers a concept to a learner [Simard et al. 2017]. Closest to our setting, language models have been used to elicit a user's preferences by asking open questions as well as for labels [Li et al. 2023], motivated by the ambiguity of tasks specified in a few words [Tamkin et al. 2023]. We study the same trade-off between labels and questions when the learner is an agent that must also encode what it learns in a classifier, and compare strategies for it on tasks where the missing knowledge lies in different places.

**Few-shot text classification.** With a few dozen labels, contrastive fine-tuning of sentence encoders is a strong baseline [Tunstall et al. 2022]. We compare against RoBERTa [Liu et al. 2019] fine-tuned on 50 labels, about what our budget buys, and on every training label.

## 3 Task Formulation

We model building as an interaction between an agent, the **builder**, and a **user** who needs a classifier. We simulate the user with an agent that holds two things the builder cannot see: a **guideline** that states the definition they have in mind, and the gold **labels**. The builder's output is an NL classifier: questions and option descriptions, combined into one of a few fixed structures (Section 4). As part of the process the builder has access to the unlabelled examples and is able to run different versions of the classifier.

**Building with labels.** In the supervised setting (RQ1), the builder receives all gold labels and does not interact with the user.

**Building from a user interview.** In the budgeted setting (RQ2 and RQ3), the builder starts with no labels and a budget of 100 points of the user's time. It can ask the user to **label** a pool record, which costs 2 points, or it can **ask** a question, which the user answers and prices by a fixed rubric meant to reflect the effort of answering:

- **2 points:** a question about a single record or type of message, or a yes/no fact;
- **5 points:** a targeted question about a rule or a group of messages;
- **10 points:** an open-ended question that needs a view across many examples, such as "what are the main confusions?", answered in summary.

A message can contain multiple questions, and their costs are added up. Requests that would exceed the budget are refused, and points left over do not affect the score.

**The simulated user.** A language model plays the user (Claude Sonnet 5 [Anthropic 2026]). It sees the task description, the private guideline, the records a question mentions and a fixed labelled sample of 150 pool records, and it prices each message by the rubric above. It is instructed to answer as a busy domain expert would: only what is asked, without reciting the guideline or volunteering rules, and in summary for open-ended questions. Where the guideline and the labelled sample conflict, it is told that the labels win, so that its answers describe the definition as applied. Section 6 shows that its answers can still drift towards the guideline, as a real user's might.

**Evaluation.** Each task also has a validation split, used only to tune the baselines, and a sealed **test** split; the builder never sees the labels of either. After its first draft and after every revision it keeps, the builder saves a **snapshot** of its classifier together with its own estimate of the score. After the run we score every snapshot on the test set. The final snapshot defines the run's result, and the earlier ones trace how the score develops as points are spent. Builders work in isolation and cannot read the labelled data, the task files or other runs (Section 4).

## 4 System

The system has three parts: a System 1 model that answers questions, a classifier format that composes those questions, and a skill that gives a coding agent the tools to write, run and revise classifiers.

### 4.1 System 1: Jev

Jev [TypeSafe 2026] answers questions about a **state**, a piece of text such as a message or a dialogue. A question is one of three types: a **choice** among up to 255 options, each with an optional description, which returns a probability for every option; a **yes/no** question, which returns the probability of yes; and a **score** on an ordered scale of up to ten levels, which returns a distribution over the levels. Its instructions and option descriptions can be structured, with definitions, inclusions and exclusions. One request can hold several questions about the same state, and the answers are deterministic.

### 4.2 NL classifiers

An NL classifier holds the static part of a Jev request: a template that renders the input as a state, and one or more questions. It takes one of five shapes:

- **flat choice:** one choice question whose options are the classes;
- **option map:** a choice with more options than classes, mapped many to one, where each class receives the summed probability of its options;
- **two-level:** a router question picks a group of classes and a second question picks a class within it, both asked in one request, so that a wrong group can be outweighed;
- **criteria:** several yes/no questions combined by a rule, for a policy that is a conjunction of tests;
- **ensemble:** the average of several classifiers, usually rewordings of one.

Any shape that yields class probabilities can also store a decision threshold. Running a classifier returns, for each record, the predicted class, the class probabilities, the most likely option and a **margin**, how far the prediction is from flipping. A classifier is only text and a few structural fields, so the user can read it, and changing a rule means editing a sentence. Because its questions are plain text, other System 1 models can answer them too (Section 5.4).

### 4.3 The builder

The builder is a general-purpose coding agent with shell access, given a run directory and the classifier-builder skill, a document it reads at the start of the run. The run directory holds the task description and class names, the unlabelled pool, the labels bought so far, and a journal the builder keeps. The skill explains the budget, the classifier format and how Jev behaves: it judges meaning better than surface patterns, does better with concrete options than with abstract ones, and can flip near-tied records on small rewordings. It then sets out a generic workflow. The builder reads the pool, writes a first draft from the description, lists what it does not know and buys the cheapest evidence that resolves it, and revises, saving a snapshot after each kept revision. It stops when nothing left to buy would change its predictions. The skill also warns that the user's answers about edge cases can disagree with their own labels, and that labels chosen because they are hard give a biased estimate of accuracy. A strategy replaces the middle of this workflow (Section 5.2). The tools are:

| Tool      | What it does                                         | Cost       |
| --------- | ---------------------------------------------------- | ---------- |
| Run       | run a classifier on the pool or on bought labels     | free       |
| Label     | ask the user for the labels of pool records          | 2 each     |
| Ask       | ask the user a question                              | 2, 5 or 10 |
| Score     | score on bought labels, with a 90% interval          | free       |
| Uncertain | list the records with the smallest margin            | free       |
| Sample    | pick records at random or spread over the options    | free       |
| Diff      | compare two versions on the pool and bought labels   | free       |
| Threshold | fit a decision threshold for a class                 | free       |
| Snapshot  | save a version with an estimate of its score         | free       |

Running classifiers costs the builder nothing, since Jev calls are cheap and cached; only the user's time is budgeted. Two further tools serve particular settings: the rules-only constraint adds a check that flags any six-word run shared by the definition and the pool, and the boundary strategy of Section 6.1 adds one that lists low-margin records by class pair and gives a verdict on each revision. With every training label, the labels file simply holds them all, and the same tools report per-class scores, confusions and scores on subsets.

Each builder first claims its run and receives a token that every command spending points or saving a snapshot requires, so concurrent builders cannot spend each other's budget. A hook checks every tool call before it runs and refuses reads of the labelled data, the task files, other runs and the simulated user's source, as well as web access beyond the TypeSafe documentation. Refusals are returned to the builder and logged.

## 5 Experiments

### 5.1 Tasks and data

We pick six tasks by where the knowledge the builder lacks lives: in the text, in a definition only the user holds, or nowhere the user can supply (Table 1). Three tasks judge single messages and three judge conversations, the setting that motivates this work.

| Task                                                         | Input                                                          | Classes | Pool / val / test   | Zero-shot (test) | Where the missing knowledge lives         |
| ------------------------------------------------------------ | -------------------------------------------------------------- | ------- | ------------------- | ---------------- | ----------------------------------------- |
| Banking77 intents [Casanueva et al. 2020]                    | a customer message                                             | 77      | 1,000 / 200 / 3,080 | 80.2% acc        | mostly in the text                        |
| Banking77 routing                                            | a customer message                                             | 6 teams | 1,000 / 200 / 3,080 | 73.7% acc        | a private mapping of intents to teams     |
| Hate speech (HatEval [Basile et al. 2019])                   | a tweet                                                        | 2       | 1,000 / 200 / 1,766 | 0.741 macro-F1   | an unstated annotation policy             |
| Persuasion strategy (Persuasion for Good [Wang et al. 2019]) | a persuader's message with the dialogue so far                 | 18      | 1,002 / 224 / 1,517 | 0.455 macro-F1   | a scheme defined by its annotation manual |
| Donation outcome (Persuasion for Good)                       | a whole charity-solicitation dialogue                          | 2       | 500 / 100 / 417     | 0.733 macro-F1   | nowhere: the label is a fact              |
| Deal reached (CraigslistBargain [He et al. 2018])            | a price negotiation without the formal offer and accept events | 2       | 1,000 / 200 / 582   | 0.889 macro-F1   | nowhere: a near-ceiling control           |

*Table 1: tasks. Zero-shot is the classifier built from the task description and class names alone.*

**Banking77 intents** asks for one of 77 fine-grained intents of a customer message to a bank. The intent names are informative, and the difficulty is separating near-synonyms such as a pending card payment and a pending transfer. **Banking77 routing** labels the same messages with one of six support teams by a private mapping from intents to teams, which includes some counter-intuitive assignments. **Hate speech** (HatEval, SemEval-2019 Task 5, English, via TweetEval [Barbieri et al. 2020]) labels tweets under a policy restricted to hate against women and immigrants, while the builder is told only that the labels follow "our annotation policy for hate speech".

The three conversation tasks come from an accuracy and calibration benchmark of Jev [TypeSafe 2026b]. In **persuasion strategy** the user's definitions are the point: the builder must learn, for example, that citing the charity's track record is a credibility appeal rather than a logical one. In **donation outcome** no definition decides whether the persuadee gave, so any gain has to come from labels. **Deal reached** is nearly solved zero-shot and tests whether builders know when to stop. We exclude the benchmark's fourth task, yes/no answers to Amazon product questions [McAuley and Yang 2016], on which Jev scores below the majority class.

We write each task's description and private guideline from the corpus's annotation instructions, keeping the description as brief as a request to an assistant. Splits are stratified, deduplicated and fixed by seed. Banking77 draws the pool and validation split from the official training split and tests on the official test set. HatEval's official test set is shifted from its training distribution, so we draw all three splits from it, and our scores are not comparable with published HatEval results. Persuasion strategy is split by dialogue, and deal reached tests on the corpus's validation split. Public datasets may let the builder recall the labels; routing, whose mapping is our own, measures what the builder has to acquire.

### 5.2 Builders and strategies

The main experiments use Claude Opus 5.5 [Anthropic 2026], and we repeat the key cells with Claude Sonnet 5.5 and Claude Haiku 4.5 to measure how much building depends on the builder's capability. Builders run headlessly through the Claude Agent SDK at high reasoning effort, with one prompt template for every task and model, and every session transcript is kept. A pilot on Banking77 intents and hate speech ran Opus builders interactively.

A **strategy** is a one-page instruction that replaces the skill's generic building step. We compare seven:

| Strategy             | Summary                                                                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Free                 | The skill's generic workflow only.                                                                                                                                              |
| Uncertainty          | Buy the records with the smallest margin between the top two classes in small batches, and revise after each batch.                                                             |
| Uncertainty + rules  | As above, but turn errors into general rules, and test any rule that moves many pool predictions with a label on a moved record.                                                |
| Policy first         | Ask the user about the main policy decisions, build a classifier that mirrors the answers, then calibrate with random labels.                                                   |
| Policy, labels first | Ask policy questions, then check the draft against random labels before testing edge cases, and follow labels where they contradict the user.                                   |
| Interview            | Read 200 pool records and list the phenomena; ask about those the text cannot settle; buy check labels and labels spread over the options; then refine on uncertain records.    |
| Interview, lean      | Read the pool and mark each phenomenon inferable or private; ask only about the private ones; spend the rest on whatever labels the builder chooses.                            |

The pilot also tried a category-by-category audit, a committee of three classifiers, a triage step and policy + rules; none beat the best strategy on either pilot task. Any strategy can run under the **rules-only constraint**, under which labels are evidence for rules and never enter the classifier: the definition may contain no text from a pool record, and a rule is kept only if it holds on records beyond the one that prompted it. Both interview strategies run under it.

### 5.3 Settings

**All labels (RQ1).** The builder receives the gold label of every training record and no budget. For the Banking77 tasks and deal reached this is the full training split (9,792 messages and 4,947 negotiations); for the other three it is the pool, which is all their labelled data outside the validation and test splits. The labels do not fit in context, so the builder queries them through tools (per-class scores, frequent confusions, scores on subsets), splits them into a building set and a development set of its choosing, and estimates its score on the latter. It gets no strategy; the prompt asks only that it hold out a development set, work from per-class scores and confusions, and state general rules rather than copy training records. We run Opus on all six tasks and Sonnet and Haiku on three, one run each.

**User interview (RQ2 and RQ3).** The budgeted grid has two parts. The **cross-model** part runs Banking77 intents, hate speech and persuasion strategy with all three builders, three runs each, using the best pilot strategy for each task (uncertainty for Banking77 intents, policy first for the other two). The **cross-strategy** part runs Opus on routing, donation and deal with the first five strategies, three runs each on routing and one on the other two. We then ran both interview strategies on all six tasks, three runs each, filled the missing strategy cells on the pilot tasks, and ran the rules-only constraint in ten runs matched to earlier ones.

### 5.4 System 1 models

Jev answers every question while building, at $0.042 per million input tokens. To test whether the classifiers depend on Jev, we run them unchanged on three other System 1 models. Perplexity's decision model [Perplexity 2026] takes Jev's request format directly. GPT-6 Luna [OpenAI 2026], a small general model at low reasoning effort, and Claude Sonnet 5 [Anthropic 2026], a large one without thinking, receive each question as a prompt with the options and their descriptions and return one option with a confidence. The other options share the remaining probability, so every classifier shape runs unchanged.

### 5.5 Baselines and metrics

Our baselines are the **zero-shot** classifier, built from the description and class names alone; the builder's **first draft**, its first saved snapshot; and RoBERTa-base [Liu et al. 2019] fine-tuned on the same labels as the all-labels builder, with the epoch chosen on the validation split. On the cross-model tasks we also fine-tune RoBERTa on 50 stratified labels, about what a 100-point builder buys, over three seeds.

We report test accuracy on Banking77 and macro-F1 elsewhere, for the final snapshot. Jev is deterministic, so the variance between runs comes from the builder, and we repeat the main cells three times. We compare two classifiers with an exact McNemar test on paired predictions. We compare groups of runs with a paired bootstrap over test records (2,000 resamples), which captures test-set noise, and with an exact permutation test over run scores, which captures run-to-run variance but cannot go below p = 0.05 with three runs per group. We log the cost of every run: the builder's API calls, the simulated user's, and the System 1 calls made while building.

<!--
Planned, not yet run: tasks varying class count, text length and multi-label output (CLINC150 [Larson et al. 2019], TREC [Li and Roth 2002], DBpedia and AG News with a secret relabelling rule [Zhang et al. 2015], PubMed RCT [Dernoncourt and Lee 2017], LEDGAR [Tuggener et al. 2020], GoEmotions [Demszky et al. 2020]); budgets of 0, 20, 50, 100 and 200 points; random-label, full-guideline and direct-LLM baselines; SetFit [Tunstall et al. 2022] and DSPy [Khattab et al. 2024]; builders that test drafts against another System 1 model; the hate speech official split with every label.
-->

## 6 Results

### 6.1 RQ1: building with every label

**With every label, an Opus builder matches or beats RoBERTa fine-tuned on the same labels on all six tasks** (Table 2). On hate speech and persuasion strategy, with about a thousand labels, both larger builders beat RoBERTa by 0.02–0.05 macro-F1. With ten thousand labels, Opus edges RoBERTa on both Banking77 tasks but stays below published full fine-tuning on intents (94.1%), and on deal reached the two are level with zero-shot. These are single runs, so margins under a point amount to parity. Donation outcome is the exception to more labels helping: both learners end below zero-shot, because 500 labelled dialogues teach cues that do not hold on the test set.

| Task                           | Labels | Zero-shot | RoBERTa, 50 labels | Opus, 100 pts | RoBERTa, all labels | Opus, all labels | Sonnet 5.5, all labels | Haiku 4.5, all labels |
| ------------------------------ | ------ | --------- | ------------------ | ------------- | ------------------- | ---------------- | ---------------------- | --------------------- |
| Banking77 intents (acc)        | 9,792  | 80.2      | 18.1               | 86.8          | 91.1                | **91.9**         | 91.3                   | 79.4                  |
| Banking77 routing (acc)        | 9,792  | 73.7      | —                  | 90.5          | 96.8                | **97.5**         | —                      | —                     |
| Hate speech (macro-F1)         | 1,000  | 0.741     | 0.635              | 0.804         | 0.780               | **0.823**        | 0.803                  | 0.729                 |
| Persuasion strategy (macro-F1) | 1,002  | 0.455     | 0.137              | 0.603         | 0.582               | 0.616            | **0.629**              | 0.486                 |
| Donation outcome (macro-F1)    | 500    | **0.733** | —                  | 0.720         | 0.675               | 0.680            | —                      | —                     |
| Deal reached (macro-F1)        | 4,947  | 0.889     | —                  | 0.871         | 0.889               | **0.896**        | —                      | —                     |

*Table 2: test scores with Jev as System 1. Labels is the number of training labels in the all-labels setting. Opus at 100 points is the mean of the budgeted runs in Table 4. RoBERTa with 50 labels averages three seeds; all-labels cells are single runs.*

**Using the labels takes a capable builder.** Sonnet comes within 0.6 points or 0.02 macro-F1 of Opus and is ahead on persuasion strategy. Haiku gains nothing: its all-labels classifiers score no better than its budgeted ones, and in all three runs its final classifier is its first draft. It read and split the labels but did not turn them into revisions, while Opus saved three to six improving snapshots. The failure is not one of judging its own classifier: every builder, Haiku included, estimated its score on its development set to within 0.035 of the test score.

**The builders converged on the same loop.** Without being told, the larger builders wrote a first draft from the description and a sample, ran it on the building set, and revised by rewriting the descriptions of the options with the most errors. Seven of the nine Opus and Sonnet classifiers use options finer than the classes, mapped many to one: 13 options for the two hate speech classes, 28 for the 18 persuasion strategies, and about 100 intent-level options with a learned team map on routing. Eight of the twelve classifiers are ensembles of two to four wordings, and none reproduces a training record. Builders mostly stopped when the remaining errors looked like disagreement among the labels; the persuasion builder, for instance, found "Great!" labelled almost at random as thanks, praise or acknowledgement.

**Revisions trade errors near the decision boundary.** Comparing consecutive snapshots on the test set after the runs, a correct record with a margin below 0.1 was broken by the next revision 32% of the time, against 0.7% for a record with a margin of 0.6 or more, and several late revisions were near-even trades on the builders' own building sets. We turned this into a strategy: read the low-margin records by class pair and either state a rule that separates the pair or declare it ambiguous, check each confident error against the nearest record labelled the other way, and keep a revision only if its fixes minus breaks exceed 2√(fixes + breaks). The strategy is level with no strategy on average (Table 3). Its one clear effect is on donation outcome, where the noise check rejected the over-tuning that had lowered the unguided run.

| Task (macro-F1)     | No strategy | Boundary strategy |
| ------------------- | ----------- | ----------------- |
| Hate speech         | **0.823**   | 0.814             |
| Persuasion strategy | **0.616**   | 0.609             |
| Donation outcome    | 0.680       | **0.719**         |
| Deal reached        | 0.896       | **0.902**         |
| Mean                | 0.754       | **0.761**         |

*Table 3: Opus all-labels builders without a strategy and with the boundary strategy, one run each. Each per-task difference is within the noise of a single run.*

### 6.2 RQ2: building from a user interview

**Without labels, Opus beats zero-shot wherever the user has something to teach** (Table 4). On Banking77 intents, routing, hate speech and persuasion strategy, the final classifier beats zero-shot in every run, by 6.6 points, 16.8 points, 0.063 and 0.148 on average, closing 56%, 71%, 77% and 92% of the gap to the all-labels builder. Having seen about 50 labels, it beats RoBERTa fine-tuned on all 1,000 on hate speech and persuasion strategy, while RoBERTa fine-tuned on the same 50 labels is far behind on every task. The encoder needs labels to learn what the classes mean; the builder brings that knowledge and uses labels to learn where the user draws the lines.

| Task                | Metric   | Zero-shot | First draft | Final (100 pts)     | Runs |
| ------------------- | -------- | --------- | ----------- | ------------------- | ---- |
| Banking77 intents   | acc      | 80.2      | 84.6        | 86.8 (85.8–87.3)    | 3    |
| Hate speech         | macro-F1 | 0.741     | 0.795       | 0.804 (0.792–0.823) | 3    |
| Persuasion strategy | macro-F1 | 0.455     | 0.593       | 0.603 (0.567–0.635) | 3    |
| Banking77 routing   | acc      | 73.7      | 83.5        | 90.5 (84.6–93.5)    | 15   |
| Donation outcome    | macro-F1 | 0.733     | 0.721       | 0.720 (0.699–0.734) | 5    |
| Deal reached        | macro-F1 | 0.889     | 0.853       | 0.871 (0.827–0.908) | 5    |

*Table 4: Opus builders with 100 points, test set. The first three rows use the cross-model strategy for the task; the others average the cross-strategy runs. Ranges give the lowest and highest run.*

**Much of the gain comes before the first label.** On Banking77 intents, the first draft, written from the description and the pool, closes 4.4 of the 6.6 points, and on persuasion strategy first drafts already reach 0.57–0.59 from the builder's knowledge of the scheme. On hate speech the gain comes from the user: the policy-first draft saved after the policy questions closes 0.054 of the 0.063 gap. On routing, first drafts close 9.8 of the 16.8 points, and the budget, which reveals the private mapping, supplies the rest.

**Where no definition decides the label, building does not help.** No run beats zero-shot on donation outcome. On deal reached, where zero-shot already scores 0.889, three of five runs match or beat it and two end well below it. When the zero-shot classifier is already good, building mainly adds the risk of moving it.

**Smaller builders are worse at building.** Opus leads Sonnet 5.5, which leads Haiku 4.5, on all three cross-model tasks (Table 5). Every pairwise gap is significant under the paired bootstrap (p ≤ 0.021), but the evidence that the builders themselves differ is weaker: the Banking77 runs separate completely (permutation p = 0.05, the minimum, for each pair), on hate speech only Opus and Haiku do, and the persuasion runs overlap. Haiku also skips steps: in six of its nine runs it saved its first snapshot only after spending 65–98 points. Its estimates of its own score were off by 0.166 on average, in both directions, because it scored itself on check sets of 10–14 labels or on the uncertain records it had bought.

| Task                           | Opus 5.5                        | Sonnet 5.5                  | Haiku 4.5                   |
| ------------------------------ | ------------------------------- | --------------------------- | --------------------------- |
| Banking77 intents (acc)        | 87.3, 87.3, 85.8 (**86.8**)     | 84.6, 83.3, 85.6 (84.5)     | 78.6, 79.3, 79.3 (79.1)     |
| Hate speech (macro-F1)         | 0.792, 0.823, 0.798 (**0.804**) | 0.751, 0.793, 0.786 (0.777) | 0.777, 0.690, 0.736 (0.734) |
| Persuasion strategy (macro-F1) | 0.607, 0.567, 0.635 (**0.603**) | 0.580, 0.571, 0.607 (0.586) | 0.560, 0.588, 0.562 (0.570) |
| Builder cost per run (USD)     | 1.39                            | 0.62                        | 0.46                        |

*Table 5: final test scores of three runs per cell, mean in parentheses. Cost is the mean over the nine runs of each model.*

### 6.3 RQ3: which interview strategies work

**The best strategy depends on where the missing knowledge lies** (Table 6). On Banking77 intents, whose meaning is in the text, uncertainty sampling is best, and policy first, which spends a third of the budget on questions, trails it by 2.8 points. On hate speech, where the labels follow a policy the builder cannot infer, the order reverses: policy first beats uncertainty + rules in all three repeats (McNemar p < 0.001 for the first pair) and pure uncertainty by 0.06, which swings the decision boundary with each noisy batch of labels. On persuasion strategy, a scheme the builder largely knows, the strategies differ less than repeats of one strategy.

| Strategy             | Banking77 intents (acc) | Hate speech (macro-F1) | Persuasion strategy | Banking77 routing | Donation outcome | Deal reached   |
| -------------------- | ----------------------- | ---------------------- | ------------------- | ----------------- | ---------------- | -------------- |
| Zero-shot (0 pts)    | 80.2                    | 0.741                  | 0.455               | 73.7              | 0.733            | 0.889          |
| Free                 | 86.3 (3 runs)           | 0.790 (3 runs)         | 0.604               | 92.6 (3 runs)     | 0.700            | 0.897          |
| Uncertainty          | **87.9** (3 runs)       | 0.751                  | 0.585               | 87.4 (3 runs)     | **0.734**        | 0.890          |
| Uncertainty + rules  | 87.4                    | 0.790 (3 runs)         | 0.570               | 88.9 (3 runs)     | 0.732            | **0.908**      |
| Policy first         | 85.1                    | **0.813** (3 runs)     | **0.607**           | 91.3 (3 runs)     | 0.733            | 0.832          |
| Policy, labels first | 86.2 (3 runs)           | 0.795 (2 runs)         | 0.549               | 92.4 (3 runs)     | 0.699            | 0.827          |
| Interview            | 85.9 (3 runs)           | 0.791 (3 runs)         | 0.590 (3 runs)      | 89.7 (3 runs)     | 0.720 (3 runs)   | 0.870 (3 runs) |
| Interview, lean      | 86.4 (3 runs)           | 0.791 (3 runs)         | 0.584 (3 runs)      | **93.0** (3 runs) | 0.722 (3 runs)   | 0.868 (3 runs) |

*Table 6: final test score by strategy, Opus builders, 100 points, one run per cell unless marked. The Banking77 intents and hate speech cells for uncertainty, uncertainty + rules and policy first, and policy with labels first on hate speech, come from the interactive pilot.*

**On routing, the strategies that probe the private mapping win.** Every run of free, policy first and policy with labels first scored 90.0–93.5%, and every run of uncertainty and uncertainty + rules scored 84.6–89.8% (permutation test over 15 runs, p < 0.001). The better strategies ask which team gets each kind of message, or buy one label for each intent whose team the builder cannot guess. Uncertainty sampling instead buys the records on which the classifier is torn between two teams, but a counter-intuitive assignment sends a whole intent to the wrong team with confidence, so its records never look uncertain. The lean interview, which asks only about what reading the pool cannot settle, does best: one message of questions about the routing rules lifts the first draft from about 81% to 88–91%, and its runs finish at 93.0% on average. The full interview, which adds fixed allowances for questions, coverage labels and a check set, is below the best strategy on every task, because the allowances leave too few labels for what the builder needs to learn.

**Where nothing is left to learn, questions can hurt.** On donation outcome no strategy beats zero-shot. On deal reached the label-driven strategies match or beat zero-shot, while both policy strategies fall to 0.83 by moving the decision boundary, in opposite directions: policy first took the user's answers about conditional agreements as a stricter definition of a deal, and policy with labels first over-corrected.

**Labels must be able to overrule the user.** The simulated user's answers about edge cases were stricter than the gold labels in every pilot hate speech run that asked them, as annotation guidelines often are stricter than annotators. Builders that mirrored those answers fell to 0.61–0.68 macro-F1 before recovering with labels. Checking random labels before testing edge cases removed the drop, but not the gap to policy first.

**Budgeted builders paste labels into the classifier, though they need not.** Under uncertainty sampling, 14 to 199 pool records per run share an eight-word run with the final definition, and one persuasion classifier gives every option a field of labelled examples. The all-labels classifiers copy almost nothing and describe patterns instead. Under the rules-only constraint (Table 7), every builder kept pool text out of its classifier and none lost accuracy, with the largest gains where the unconstrained builders had copied most. With one run per cell, the conclusion is that examples are not needed, not that rules are better.

| Task                | Strategy     | Rules only | Without constraint | Records copied (rules only / without) |
| ------------------- | ------------ | ---------- | ------------------ | ------------------------------------- |
| Persuasion strategy | Uncertainty  | 0.615      | 0.585              | 0 / 56                                |
| Deal reached        | Uncertainty  | 0.904      | 0.890              | 0 / 44                                |
| Banking77 intents   | Uncertainty  | 87.5       | 86.8 (3 runs)      | 0 / 26–48                             |
| Banking77 routing   | Uncertainty  | 87.7       | 87.4 (3 runs)      | 0 / 32–45                             |
| Donation outcome    | Uncertainty  | 0.731      | 0.734              | 0 / 28                                |
| Persuasion strategy | Free         | 0.607      | 0.604              | 0 / 15                                |
| Banking77 routing   | Free         | 92.7       | 92.6 (3 runs)      | 0 / 1–2                               |
| Hate speech         | Policy first | 0.804      | 0.804 (3 runs)     | 0 / 0–4                               |
| Deal reached        | Free         | 0.895      | 0.897              | 0 / 0                                 |
| Donation outcome    | Free         | 0.690      | 0.700              | 0 / 2                                 |

*Table 7: the rules-only constraint against the same strategy without it, Opus builders, 100 points, one rules-only run per cell. Records copied are pool records sharing a six-word run with the final definition.*

In short, the budget should go to the definition when the definition is what the builder lacks, and labels must be able to overrule what the user says. When the builder already knows the definition, or no definition decides the label, most strategies add little after a good first draft, and none of ours encodes when to stop.

### 6.4 Other System 1 models

**The classifiers transfer between System 1 models without retuning** (Table 8). The zero-shot classifiers spread by up to 0.07 macro-F1 across the four models, and no model is best on more than two tasks. Once Opus has written the definition from every label, the four models land within 0.031 macro-F1 of one another on every task and within one point on Banking77, and Jev, against which the classifiers were tuned, leads only on Banking77. A larger model adds little to a classifier that already states the definition: Sonnet 5 costs 40–75 times as much per record as Jev and is level with it.

| Task                           | Zero-shot: Jev | Luna      | Perplexity | Sonnet 5  | Opus, all labels: Jev | Luna      | Perplexity | Sonnet 5  |
| ------------------------------ | -------------- | --------- | ---------- | --------- | --------------------- | --------- | ---------- | --------- |
| Banking77 intents (acc)        | 80.2           | **82.8**  | 79.3       | 81.2      | **91.9**              | 91.5      | 91.1       | 91.0      |
| Banking77 routing (acc)        | 73.7           | **77.6**  | 72.6       | 76.5      | **97.5**              | 96.5      | 96.6       | 96.7      |
| Hate speech (macro-F1)         | **0.741**      | 0.740     | 0.709      | 0.691     | 0.823                 | **0.826** | 0.800      | 0.821     |
| Persuasion strategy (macro-F1) | 0.455          | 0.461     | 0.462      | **0.524** | 0.616                 | **0.621** | 0.615      | 0.605     |
| Donation outcome (macro-F1)    | **0.733**      | 0.721     | 0.724      | 0.703     | 0.680                 | 0.681     | 0.708      | **0.711** |
| Deal reached (macro-F1)        | 0.889          | 0.899     | 0.896      | **0.905** | 0.896                 | **0.912** | 0.906      | 0.896     |
| Cost per 1,000 records (USD)   | 0.02–0.05      | 0.04–0.09 | 0.01–0.03  | 1.1–2.7   | 0.09–0.45             | 0.10–0.97 | 0.06–0.36  | 4.8–16.7  |

*Table 8: the zero-shot and Opus all-labels classifiers, built against Jev and run unchanged on four System 1 models. Sonnet costs are at batch (half) price.*

The budgeted classifiers transfer even better (Table 9). Luna matches or beats Jev on every task mean and in 12 of the 14 runs, and Perplexity's decision model stays within 0.4 points and 0.014 macro-F1 of Jev. These classifiers were tuned on a few dozen labels rather than fitted option by option to Jev's answers on thousands of records, which may be why they lose nothing in transfer.

| Task                              | Runs | Jev                         | Luna                            | Perplexity                  |
| --------------------------------- | ---- | --------------------------- | ------------------------------- | --------------------------- |
| Banking77 intents (acc)           | 3    | 87.3, 87.3, 85.8 (86.8)     | 88.2, 87.9, 86.8 (**87.6**)     | 87.5, 86.3, 85.4 (86.4)     |
| Banking77 routing, free (acc)     | 3    | 93.5, 92.1, 92.4 (92.6)     | 93.5, 92.2, 92.9 (**92.9**)     | 93.3, 92.2, 92.1 (92.5)     |
| Hate speech (macro-F1)            | 3    | 0.792, 0.823, 0.798 (0.804) | 0.817, 0.816, 0.807 (**0.813**) | 0.812, 0.799, 0.786 (0.799) |
| Persuasion strategy (macro-F1)    | 3    | 0.607, 0.567, 0.635 (0.603) | 0.628, 0.576, 0.629 (**0.611**) | 0.609, 0.585, 0.627 (0.607) |
| Donation outcome, free (macro-F1) | 1    | 0.700                       | 0.719                           | **0.727**                   |
| Deal reached, free (macro-F1)     | 1    | 0.897                       | **0.902**                       | 0.883                       |

*Table 9: final classifiers of budgeted Opus builders (the cross-model runs of Table 5, and the free-strategy runs on the other tasks), built against Jev and run unchanged on Luna and Perplexity's decision model. Means in parentheses.*

### 6.5 Cost

Building a classifier from a user interview costs $1.03–3.70 per run (Table 10), most of it the builder's own API calls; the simulated user adds $0.06–0.33. With every label, running drafts over thousands of records raises the System 1 cost of building to $3–6 per run. Once built, the classifiers cost $0.07–0.25 per 1,000 records with Jev, two to four times as much with Luna, and $4.8–16.7 with Sonnet 5 even at batch price. Fine-tuning RoBERTa-base took from a minute to five hours on one M4 Max GPU, depending on the task. All runs in this paper cost about $855 in API calls.

| Setting                         | Runs | Builder | Simulated user | System 1 while building | Total to build | Minutes | Final classifier, per 1,000 records |
| ------------------------------- | ---- | ------- | -------------- | ----------------------- | -------------- | ------- | ----------------------------------- |
| Budgeted, Opus (cross-model)    | 9    | 1.39    | 0.18           | 0.66                    | 2.24           | 8.6     | 0.25                                |
| Budgeted, Sonnet (cross-model)  | 9    | 0.62    | 0.16           | 0.62                    | 1.40           | 5.3     | 0.15                                |
| Budgeted, Haiku (cross-model)   | 9    | 0.46    | 0.33           | 0.24                    | 1.03           | 8.5     | 0.07                                |
| Budgeted, Opus (cross-strategy) | 30   | 1.48    | 0.11           | 1.03                    | 2.62           | 7.9     | 0.20                                |
| Budgeted, Opus, rules only      | 10   | 1.75    | 0.06           | 1.88                    | 3.69           | 9.4     | 0.25                                |
| Budgeted, Opus, interview       | 18   | 1.96    | 0.11           | 1.11                    | 3.18           | 9.2     | 0.16                                |
| Budgeted, Opus, interview lean  | 18   | 1.91    | 0.08           | 1.70                    | 3.70           | 10.3    | 0.21                                |
| All labels, Opus                | 6    | 1.93    | —              | 6.09                    | 8.02           | 19.6    | 0.25                                |
| All labels, Sonnet              | 3    | 0.71    | —              | 3.14                    | 3.85           | 8.7     | 0.12                                |
| All labels, Haiku               | 3    | 0.55    | —              | 5.06                    | 5.61           | 11.7    | 0.12                                |

*Table 10: mean cost per run in USD. Builder is the agent's API cost; the simulated user is Claude Sonnet 5; System 1 while building is the builder's Jev calls. The last column is the Jev cost of running the final classifier.*

## 7 Discussion: monitoring and updating

The experiments measure building, but System 2's job continues after a
classifier is deployed. Its inputs drift, the user's definition changes,
and errors surface that no building set contained. Three properties of NL
classifiers make this part of the job tractable for an agent. First,
monitoring can reuse the building strategies as sampling policies over the
live stream: uncertainty sampling surfaces records near the decision
boundary, a random audit estimates the current accuracy without bias, and
running two versions side by side surfaces the records on which an edit
would change the outcome. Our results suggest that no single policy is
enough: on routing, a confidently wrong intent-to-team assignment never
looks uncertain, so a monitor that only follows uncertainty would miss it,
and an audit or a direct question would find it. Second, an update is an
edit to a readable definition. When the user says that a kind of message now
goes to another team, the agent changes one entry of the team map; a
fine-tuned encoder would need labelled examples of the change and a
retraining run before it applied the new rule. Third, the agent can judge
its own classifier when it has a development set of a few hundred labels
(§6.1), which gives it a basis for deciding when to escalate to the user
and when to stop. Measuring this loop, with drifting streams and users
whose definitions change, is future work.