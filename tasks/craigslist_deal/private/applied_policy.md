# How the craigslist_deal labels actually work

## What the label records

The pool has 1,000 records: about 75% are labelled deal and 25% no_deal. The label follows the policy's definition. It records whether the seller accepted the buyer's formal offer, and it comes from the hidden outcome, not from anyone's reading of the chat. The offer, accept, reject and quit events are removed from the transcript, so the chat is only indirect evidence. In many records the label cannot be worked out from the text at all. Expect a real error floor even with perfect reading of the chat.

My judgement is that the labels are internally consistent with the hidden outcome. Wherever they look "inconsistent", it is between the label and what the chat appears to say. Below I describe each kind of chat ending and how its labels are split.

## Deal

**Clear verbal agreement at the end (high confidence).** Examples: a closing "Deal!", "sounds good", "ok", "I'll take it", or "sold". Also a seller saying "I accept your $X, send the offer". Roughly 94% of these chats are labelled deal (about 227 of 241 that I matched). Agreement counts whatever the price:
- a price far below the listing
- a price above the listing
- a deal with add-ons (delivery, a helmet, a free oil change)
- a deal with silly jokes in the chat

Chats where one side says to submit or send the formal offer are about 88% deal.

**Exceptions: verbal agreement labelled no_deal (about 1 in 17).** The policy warns that a verbal agreement is not itself a deal, and these are the cases where that matters. Examples:
- The seller says "That seems more than fair" and the record is still no_deal.
- They agree on a flat price including utilities, then no_deal.
- The buyer says "OK deal" to the seller's final price, then no_deal.

You cannot see why from the text. The likely causes are an offer entered at the wrong amount, a technical problem, or a change of mind. A model should treat these as noise.

**The chat ends with no resolution, but the label is deal (medium confidence).** A large share of deal labels come from chats that stop mid-negotiation. Examples:
- The buyer's last line is "Best I can do is $1200, take it or leave it", with no reply.
- The seller's last line is "$1900 is the lowest", and the buyer had been at $1400.
- The chat drifts into small talk, or a joke, after a counteroffer.

Presumably the buyer then submitted an offer the seller accepted. When the chat ends on a buyer counteroffer, about 60% are deal. When it ends on the seller stating a "lowest" or "final" price, it is roughly 55/45 deal.

## No_deal

**Chats with no negotiation (high confidence).** These are the clearest no_deal cases:
- greetings only ("Hi", "Hello, are you interested?")
- one or two product questions and then nothing
- chats that never mention a number

About 86% of chats with no digits anywhere are labelled no_deal. About 80% of one-message chats are no_deal. These are almost certainly quits or abandoned sessions, which the policy counts as "someone quit". Still, about 1 in 7 of these near-empty chats are labelled deal; the formal offer was apparently made and accepted without any chat about price.

**Explicit breakdown (high confidence).** Typical endings:
- The seller ends with a refusal: "No.", "No thank you, I can get my asking price", "I hope you find what you want elsewhere", "we're not a good match, good luck".
- Either side says they can't make a deal.
- The buyer says they will pass.

About 80% of chats ending in a seller refusal are no_deal. The rest are deal, which suggests the buyer gave in through the formal offer.

**Role confusion, wrong item, and platform trouble (medium-high confidence).** Examples:
- The seller talks about a mirror when the listing is a bed frame.
- A participant thinks they are the buyer when they are the seller.
- Someone complains that the task glitched, they can't submit, or the offer won't accept.

These are mostly no_deal when the confusion never gets resolved. When the pair sort it out and then haggle normally ("Oops, the dresser is my other ad… I can offer $100" / "That works"), they are usually labelled deal. The policy says nothing about these chats.

**Chats that stop on a buyer's opening offer.** Examples are a lone "450" or "Would you accept $1900?" with no reply. These lean no_deal: about two-thirds of chats ending on a buyer's price question are no_deal.

## Rough decision guide, from most to least reliable

1. No price discussed, or the chat is only greetings or questions → no_deal (about 86%).
2. Explicit agreement on a price in the last turn or two → deal (about 94%).
3. Explicit refusal or walk-away at the end → no_deal (about 80%).
4. Gap still open when the chat ends → near coin-flip, leaning deal (about 55–60%), because the base rate is 75% deal.
5. A buyer's first offer gets no reply → leans no_deal (about 65%).

## Other observations

- **Category.** Housing has a slightly higher no_deal rate (about 31%) than cars (about 25%) and the other categories (about 22%). The difference is small and probably reflects longer, harder rent negotiations, not a labelling rule.
- **Repeated messages.** Some transcripts contain duplicated messages, a glitch in the source data. They don't affect the label.
- **Messages that look like broken text** ("must type to pay", messages cut off mid-sentence) appear under both labels.
- **The agreed price is not checked against anything.** It doesn't matter whether it is plausible or what the private targets were. A $10,500 settlement on a $13,500 listing and a deal well above the listing price are both deal.

## Where the labels depart from the written policy

- **Abandoned chats.** The policy describes only rejection and quitting as no_deal. In practice the biggest group of no_deal records is chats with little or no negotiation. That is consistent with "someone quit", but the policy doesn't say so.
- **Unresolved chats.** The policy implies the chat is secondary, which is correct. It understates how often the label disagrees with the obvious reading of the chat. Roughly a quarter of deal records have no visible agreement. A small but real group of no_deal records end in an apparent agreement.
- **Garbled sessions.** The policy is silent on wrong-item, role-confusion and broken-session chats. The labels handle them by outcome: usually no_deal unless the pair recover and negotiate.

## Confidence and consistency

- **High confidence:** the base rate; that agreement endings are deal and empty chats are no_deal.
- **Medium confidence:** the exact percentages for unresolved endings. They come from regex samples of 14–30 records each.

Overall, I'd expect a careful human reader to match the labels on about 85% of records. The remaining disagreement comes from information that isn't in the transcript, not from annotator error.
