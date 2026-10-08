# Hate speech annotation policy (private)

Paraphrase of the SemEval-2019 Task 5 (HatEval) guidelines. The labelled
records are the ground truth; where this summary and the labels disagree, the
labels win.

- **Scope:** only hate against two target groups counts: **immigrants**
  (including refugees and migrants) and **women**. Hostility toward other
  groups or individuals for other reasons is `not_hate` under this policy.
- **Hate:** the tweet spreads, incites, promotes or justifies hatred or violence
  toward the target group, or toward an individual *because* they belong to
  it, or dehumanises, degrades or intimidates them. Calls to deport, attack or
  exclude, and demeaning generalisations, count.
- **Explicit misogynistic abuse** aimed at a woman (sexualised insults and
  slurs used to degrade her) was usually labelled `hate`.
- **Not hate:** discussing immigration policy without hostility toward
  people; reporting or condemning hate; jokes and profanity without a target
  from the two groups; general rudeness.
- Hashtags are part of the content (for example #BuildTheWall, #SendThemBack
  campaigns were typically hateful when used approvingly).
- Annotators labelled from the text alone, without following links.
