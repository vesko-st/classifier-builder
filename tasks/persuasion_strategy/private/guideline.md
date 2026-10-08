# Persuasion strategy annotation scheme (private)

Paraphrase of the Persuasion for Good annotation scheme (Wang et al., ACL 2019).
The labelled records are the ground truth; where this summary and the labels
disagree, the labels win.

**Setting.** Two crowd workers chat online. The persuader tries to convince the
persuadee to donate part of their task payment (between $0 and $2) to the
charity Save the Children. Every persuader message is tagged with one label:
the persuasion strategy it uses, or, if it uses none, the dialogue act it
performs. When a message does several things, the tag is the most prominent
strategy; strategies take precedence over plain dialogue acts.

## Persuasion strategies

- **logical-appeal**: reasoning or evidence that a donation will have an
  effect ("even a small amount can buy a child a meal"; "your money goes
  directly to children in need").
- **emotion-appeal**: eliciting sympathy, guilt, sadness or hope, for example
  by describing children's suffering or asking the persuadee to imagine it.
- **credibility-appeal**: establishing the charity's trustworthiness: its
  history, reach, credentials, ratings, or how funds are used ("Save the
  Children has been around since 1919 and works in 120 countries"). Citing
  facts about the organisation is credibility, not logic.
- **foot-in-the-door**: starting with a small request to make a later,
  larger one easier ("could you give just a few cents?").
- **self-modeling**: the persuader states their own intention to donate, to
  act as a role model ("I'm going to donate $1 myself").
- **personal-story**: a narrative about the persuader's or someone else's
  experience with donating or with the beneficiaries.
- **donation-information**: facts about the donation procedure in this task:
  that it comes out of the task payment, the amount range, when it is paid.
- **source-related-inquiry**: asking whether the persuadee knows the charity
  ("Have you heard of Save the Children?").
- **task-related-inquiry**: asking the persuadee's opinion or expectations
  about donating or this task ("Would you consider donating?"; "How much do
  you usually give?" is ask-donation-amount instead).
- **personal-related-inquiry**: asking about the persuadee's own life or
  experiences related to charity ("Do you have kids?"; "Have you donated
  before?").

## Dialogue acts (no strategy)

- **greeting**: hello, how are you, introductions.
- **thank**: thanking the persuadee.
- **acknowledgement**: acknowledging or agreeing with what the persuadee said
  ("I understand", "that's true") without adding a strategy.
- **praise-user**: complimenting the persuadee ("that's very generous of you").
- **proposition-of-donation**: directly asking the persuadee to donate.
- **ask-donation-amount**: asking how much the persuadee will donate.
- **off-task**: chat unrelated to the donation.
- **other**: everything else, including answering the persuadee's questions
  (positively, neutrally or negatively), closing the conversation, confirming
  the persuadee's donation, asking them to donate more, commenting on the
  partner, asking why they will not donate, and "you're welcome".

Annotators saw the dialogue up to and including the message, and tagged the
message in that context.
