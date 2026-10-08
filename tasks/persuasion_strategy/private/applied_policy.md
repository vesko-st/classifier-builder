# How the persuasion_strategy labels actually work

## Overview
The pool has 1,002 records and the classes are very uneven. Credibility-appeal (183) and other (145) are the largest. Personal-story (9) and off-task (5) are close to empty, so their macro-F1 will be noisy. The labels follow the policy closely for formulaic messages (greetings, thanks, payment facts, "have you heard of…"). They follow it loosely for the appeals and the inquiry types. Context matters: a bare "Great!" can get four different labels depending on what came before it.

## Greeting (high confidence, about 9 in 10 consistent)
Hellos, "how are you", and replies to those ("pretty good", "I am doing well, thank you", "glad your day is great") are greeting. If the greeting is attached to content, the content wins. "Hi, have you heard of Save the Children?" is source-related-inquiry. "Hi, do you usually donate?" is personal-related-inquiry. "Hey, give some money to kids" is proposition-of-donation.

## Thank (high confidence, about 9 in 10)
Thank-yous and "it's really appreciated" are thank. A thanks that carries an appeal ("the children will appreciate it") sometimes goes to emotion or credibility instead. Thanks for an answer to "how are you" is greeting.

## Source-related-inquiry (high confidence)
Asking whether the persuadee knows Save the Children, in any phrasing or position, is source-related. Rare extras: opening with "how do you feel about Save the Children?", and one "Did you know Save the Children is…" opener.

## Credibility-appeal (high confidence on the rule; it is a broad catch-all)
In practice this is the default label for any statement about the organisation, which is wider than the policy's "trustworthiness":
- what it does, where it works, and that it "helps children in developing countries"
- naming or introducing it ("there's a charity called Save the Children")
- the persuader's praise of it ("a fine organisation", "they do so much good")
- celebrities and awards
- fund-use percentages ("86% goes to programs") and ratings
- pointing to the website (about 3 in 4 URL messages)

Answers to "what do they do?" land here, not in other as the policy says.

## Emotion-appeal (moderately high confidence, about 3 in 4)
Child suffering, deaths, war and hunger statistics, "imagine", guilt, sadness. Policy departure: a third-person story about a child the charity helped (e.g. a serial story about one boy) is labelled emotion-appeal, not personal-story. A suffering fact phrased as "Did you know…?" sometimes goes to task-related-inquiry. Saying the charity is acting on the suffering pulls the label towards credibility.

## Logical-appeal (medium confidence, noisy)
Claims that donating has an effect ("your donation will make a huge impact", "they can only help when people donate"). Also moral reasoning ("we should all pitch in", "children are the future", "everyone deserves a fighting chance") and comparisons ("$20 is a week of coffee for you"). Some agreeable filler gets logical-appeal too. Expect overlap with emotion, credibility and foot-in-the-door.

## Foot-in-the-door (medium-high confidence; departs from the policy)
The policy wants a small request that leads to a bigger one. The labels instead give foot-in-the-door to the "even a small amount helps" message:
- "every little bit helps"
- "even the smallest donation makes a difference"
- "it only takes pocket change"
- "you can do as little as 5 cents"

The policy's own logical-appeal example ("even a small amount can…") is in practice foot-in-the-door about 2 times in 3, and logical-appeal the rest of the time. Policy-style small-then-larger requests hardly appear. One explicit "could you afford fifteen cents?" was labelled ask-donation-amount.

## Self-modeling (high confidence, about 9 in 10)
The persuader's own giving: intentions ("I'm going to donate $2"), matching offers ("if you give 30% I'll give 50%"), and also past or habitual giving ("I'm a monthly donor", "I have in the past"). One "I donate every Christmas" was labelled other.

## Personal-story (low confidence; almost unused)
Nine scattered cases: persuader anecdotes about travel or work, "I've thought about donating but never did", "I give $100 every year". Most persuader experiences go elsewhere:
- a friend's child dying → emotion-appeal
- the charity funding the persuader's child's school → credibility-appeal
- "I worked in Africa, a few dollars goes far" → foot-in-the-door
- giving to other charities → other or off-task

Don't expect this class to be learnable.

## Donation-information (high confidence, about 9 in 10)
Facts about the task donation: it comes out of the task payment, the $0–$2 range, "the research team will collect donations and send them" (9 of 10 such messages), and the donate box at the end. It also takes in general how-to-donate talk: payment methods, "only money is accepted in this format", "anything is acceptable", suggested amounts, and "it can come right out of your task money if you'd like".

## Proposition-of-donation vs task-related-inquiry vs ask-donation-amount
- **Proposition-of-donation (high confidence; departs from the policy):** any direct ask, including "Would you consider donating?", "Would you be willing to donate part of your earnings?" and "Do you think you'll donate today?". The policy puts "Would you consider donating?" under task-related-inquiry; the labels treat these as proposition about 9 in 10 times. Statements count as well ("we're asking people to give a small part of their payment", "if you'd just agree to donate it would go quicker").
- **Ask-donation-amount (about 3 in 4):** "How much would you like to give?", "What amount were you thinking?". About 1 in 6 of these are proposition instead.
- **Task-related-inquiry (medium-low confidence; a catch-all for persuader questions):** opinion questions ("What do you think of it?", "Best way to help the kids?"), "Is there any information I can give you?", "What questions do you have?", "What are you not sure about?", "Can you elaborate?", "Whaddya say?", fact quizzes framed as "Did you know…?", and even "What part of the US are you from?".

## Personal-related-inquiry vs task-related-inquiry (low consistency)
"Do you have kids?", "Are you involved in children's charity?" and "Which charities do you give to?" are personal-related. Donation-history questions ("Do you donate to charities?", "Have you ever donated to them?", "Do you volunteer?") split about 60/40 between personal-related and task-related. The policy puts them all under personal-related. The model can't do better than the annotators here.

## Acknowledgement vs praise-user vs other
- **Acknowledgement:** agreeing or reacting to what the persuadee said ("That's great to hear", "I agree 100%", "okay great", "Yes they do").
- **Praise-user:** compliments ("You're such a nice person", "very generous", "you'll make a child's dreams come true"), and bare "Great!/Awesome!" right after the persuadee commits.
- Bare "Great!" splits roughly 7 praise, 6 acknowledgement, 3 thank, 1 greeting, depending on context.
- Flat fillers ("Ok…", "Fine…", "yeah..", "yes, indeed.") usually go to other, not acknowledgement.

## Other (high confidence on the listed types)
These match the policy:
- closings and "have a great night"
- confirming the amount ("so that's 20 cents, right?")
- asking for more ("could you give a bit more?", "can I count on $500?")
- answering the persuadee's questions, especially "No, I don't donate" or "Yes, I'm familiar with them"
- talking about other charities
- insults and arguing ("where are you getting your information?")
- remarks about the task itself ("we need 10 turns")
- non-English messages and typo fixes

## Off-task (low confidence)
Only 5 cases: one tangent about immigrants, a closing "lovely chatting", and a mention of animal charities. Most chit-chat goes to other, task-related-inquiry or greeting instead.

## Biggest departures from the written policy
1. "Small amounts help" is foot-in-the-door, not logical-appeal.
2. "Would you consider donating?" is proposition-of-donation, not task-related-inquiry.
3. Donation-history questions are split between personal-related and task-related.
4. Credibility-appeal covers any description or praise of the charity, including answers to questions.
5. Third-person beneficiary stories are emotion-appeal; personal-story is almost unused.
6. Off-task is almost unused; such chat goes to other.
