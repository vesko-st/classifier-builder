# How the donation labels behave in practice

## What the labels are
There are 500 records: 268 donated (54%) and 232 not_donated (46%). In line with the written policy, each label records what the persuadee actually gave after the chat, not what they said in it. This makes the labels noisy compared with the chat text. Many cases that look the same in the chat end up with opposite labels. A model that reads the chat perfectly will still miss a large share of cases, so expect a modest ceiling on macro-F1.

The policy says the chat is "evidence about intent", and it is. But it is much weaker evidence on the donated side than on the not_donated side. The sections below give rough rates for each kind of chat. These come from regex searches plus reading a few dozen records, so treat the figures as approximate.

## Firm refusals → not_donated (high confidence)
Persuadees who say no clearly, and keep saying no under pressure, are almost always not_donated. My estimate is 9 in 10 or more. Examples:
- "No, sorry… my answer is still no."
- "I'd rather keep the money I make."
- "I choose $0."
- "I'd rather give to them directly, not through this system."
- "I don't really care, I want the full reward."

The same goes for refusals based on beliefs: "only American kids", "charities have too much overhead", "children's charities aren't worthwhile", "I only give locally". Hard refusals that end up donated are rare in the pool. The policy says "some who … refused did give", but in practice that hardly happens with firm refusals. Where a "no" record is labelled donated, the persuadee nearly always changed their mind during the chat and named an amount (for example "I can't now… well, I can spare a penny").

## A specific pledge → donated about 3 times in 5 (medium confidence)
When the persuadee names an amount within the task's range ("I'll do $1", "50 cents", "half my payment", "10%"), the record is donated only about 60% of the time. The other 40% are not_donated. Nothing in the text reliably separates them. Polite, clean chats where the persuadee says "I'll donate $1" and the persuader confirms appear with both labels. This is the main place where the labels depart from what the chat suggests. Agreeing to give is only a moderately good predictor of giving.

Things that shift the odds:
- **Pledging the full amount** ("all of it", "the whole $2", "the full 30 cents") is the strongest donated signal. Roughly 4 in 5 or more of these are donated. I'm fairly confident, but this subset is small (a few dozen).
- **Small or token amounts given reluctantly after pressure** ("fine, .12", "3 cents", "I may could do .25", "5 cents if you promise 10") are close to a coin flip, maybe slightly towards not_donated. Small amounts offered freely and cheerfully ("sure, I'll donate $0.25") lean donated.
- **Haggling** (the persuader pushes 25¢ → 50¢ → $1, and the persuadee gives in grudgingly) leans not_donated in the examples I read.
- **Percentages or "half"**: about 3 in 5 donated, the same as other pledges.

## Pledges outside the task's range → coin flip (medium confidence)
Some persuadees misunderstand the task and pledge real-world sums: "$5", "$10", "$20 when I get my check", "$50", "$100", "$36 a month to sponsor". These are labelled about 50/50. The same applies to "I'll donate on the website", "next month" or "when I'm paid" (about half donated). Don't read a large pledge as a strong donated signal.

## No amount ever stated → leans not_donated (medium confidence)
Of chats where the persuadee never names an amount, about 1 in 3 are donated and 2 in 3 not_donated. This group mixes several kinds of chat:
- **Hard refusals:** almost all not_donated, as above.
- **Skeptics who end on "I need to research more", "I'll look into it", "I'm not ready to decide":** mostly not_donated.
- **Warm but vague persuadees** ("I probably will", "count me in", "okay, I can agree with that", "I'll check the website and donate") and chats that drift into small talk after a friendly start: often donated, roughly half or a bit more. Example: the persuader explains the charity, the persuadee says it's wonderful, and they chat about the weather; this kind of chat is frequently donated.
- **Chats that end just before the amount question** ("Yes, of course" followed by the persuader asking how much, with no answer): lean not_donated.

## Garbled, all-caps, scripted-looking chats → not_donated (fairly high confidence)
The policy doesn't mention this. In chats where one side (either side) writes in repetitive all caps or broken template English, labels are about 9 in 10 not_donated. That holds even when the persuadee says "OK I WILL DONATE", "ok i 2" or "20 DOLLAR FOR THE CHILD". Examples: "HI GOOD MORNING / MANY CHILDREN ARE DYING / YOU WILL DONATE TO THE CHILD". Nonsense replies that don't follow the conversation (pasted unrelated sentences) are also not_donated.

Ordinary non-native or low-effort English, without the caps or template pattern, is mixed. Several such chats with odd pledges ("i willl be doniated in $15", "I will like to pay 30 dollars") are labelled donated.

## Off-topic or role-confused chats → coin flip (low–medium confidence)
About 30 chats never name Save the Children. These include chats where the roles get reversed (the persuadee does the persuading or asks the persuader how much they'll give), chats that turn into politics or job talk, and chats about "a children's charity" in general. They split exactly 50/50, so the chat content tells you little here.

Chats where the persuadee is openly trolling ("I'm like Jesus", jokes about the charity) or rushing ("done this HIT 12 times, let's be quick") lean not_donated even with a pledge, but there are only a few examples.

## Things that don't seem to matter
I saw no consistent effect from these, though I didn't count any of them systematically:
- the persuader offering to match the donation
- the persuader confirming the amount ("so that's $1, correct?")
- how much charity information was exchanged
- the persuadee asking about overhead or legitimacy before pledging
- how long the chat is

A persuadee saying they already give to other charities is neutral if they then pledge. If they don't pledge, it goes with refusal.

## Where the labels depart from the written policy
1. The policy implies the two directions are equally unreliable. In fact refusals are reliable (not_donated) and agreements are not (only about 60% donated).
2. Bot-like, all-caps or nonsense chats are nearly always not_donated whatever was pledged. The policy doesn't cover these.
3. Pledges outside the $0–$2 range, and promises to give elsewhere or later, carry almost no signal.
4. Warm but noncommittal persuadees donate fairly often, so having no stated amount doesn't mean not_donated.

## Practical summary for the engineer
| Kind of chat | Label | Rough rate | Confidence |
|---|---|---|---|
| Firm refusal | not_donated | ~90%+ | High |
| Spammy / all-caps chat | not_donated | ~90% | Fairly high |
| Full-amount pledge | donated | ~80%+ | Fairly confident; small subset |
| Any other in-range pledge | donated | ~60% | Medium |
| Out-of-range or deferred pledge | either | ~50/50 | Medium |
| No amount, skeptical | not_donated | mostly | Medium |
| No amount, warm | either | ~50/50, slight lean donated | Medium |

Expect about one in three or four labels to look "wrong" against the chat text. That is in the data, not annotator error you can clean up.
