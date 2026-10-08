# Deal reached (private)

From the CraigslistBargain corpus (He et al., EMNLP 2018). The labelled records
are the ground truth; where this summary and the labels disagree, the labels
win.

**Setting.** Two crowd workers negotiate the price of an item listed on
Craigslist, one as buyer and one as seller, each with a private target price.
After chatting, the buyer submits a formal offer, which the seller accepts or
rejects; either side may also quit. The formal offer, accept, reject and quit
actions are not in the transcript, only the chat messages.

- **deal**: the negotiation ended with the seller accepting the buyer's
  formal offer.
- **no_deal**: the seller rejected the final offer, or someone quit.

A verbal agreement in the chat is not itself a deal: what counts is whether
the formal offer that followed was accepted.
