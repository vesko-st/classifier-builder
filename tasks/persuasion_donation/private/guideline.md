# Donation outcome (private)

From the Persuasion for Good corpus (Wang et al., ACL 2019). The labelled
records are the ground truth; where this summary and the labels disagree, the
labels win.

**Setting.** Two crowd workers chat online. The persuader tries to convince the
persuadee to donate part of their task payment (between $0 and $2) to the
charity Save the Children. After the chat, the persuadee privately chose how
much to actually donate.

- **donated**: the persuadee's actual donation, recorded after the
  conversation, was more than $0.
- **not_donated**: the actual donation was $0.

The label is what the persuadee did, not what they said. Some persuadees who
agreed to donate during the chat gave nothing afterwards, and some who were
noncommittal or refused did give. The conversation is the only evidence, but
it is evidence about intent, not a record of the payment.
