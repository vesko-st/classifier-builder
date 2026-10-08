#!/usr/bin/env python3
"""Render paper.md as an ACL-format LaTeX paper (acl/paper.tex), then build the PDF.

    python3 paper/md_to_acl.py            # writes paper/acl/paper.tex and runs latexmk
    python3 paper/md_to_acl.py --no-pdf   # .tex only

Handles the markdown subset paper.md uses: "# title", "## Abstract", "## N Section",
"### N.M Subsection", paragraphs, "- " and "1. " lists, pipe tables, **bold**, *italic*,
`code`, HTML comments (kept as LaTeX comments), and [Author Year; Author Year] citations,
which must appear in CITE_KEYS. A table followed by an italic "*Table N: ...*" paragraph
becomes a numbered float with that caption; tables without one are set inline.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "paper.md"
OUT_DIR = HERE / "acl"

CITE_KEYS = {
    "TypeSafe 2026": "typesafe2026",
    "TypeSafe 2026b": "typesafe2026b",
    "OpenAI 2026": "openai2026",
    "Perplexity 2026": "perplexity2026",
    "Anthropic 2026": "anthropic2026",
    "Yao et al. 2023": "yao2023react",
    "Schick et al. 2023": "schick2023toolformer",
    "Wang et al. 2024": "wang2024survey",
    "Devlin et al. 2019": "devlin2019bert",
    "Liu et al. 2019": "liu2019roberta",
    "Kahneman 2011": "kahneman2011thinking",
    "Bengio 2019": "bengio2019system2",
    "Booch et al. 2021": "booch2021thinking",
    "Zhou et al. 2023": "zhou2023ape",
    "Khattab et al. 2024": "khattab2024dspy",
    "Yang et al. 2024": "yang2024opro",
    "Settles 2009": "settles2009active",
    "Simard et al. 2017": "simard2017machine",
    "Casanueva et al. 2020": "casanueva2020efficient",
    "Basile et al. 2019": "basile2019semeval",
    "Barbieri et al. 2020": "barbieri2020tweeteval",
    "Wang et al. 2019": "wang2019persuasion",
    "He et al. 2018": "he2018decoupling",
    "McAuley and Yang 2016": "mcauley2016addressing",
    "Larson et al. 2019": "larson2019evaluation",
    "Li and Roth 2002": "li2002learning",
    "Zhang et al. 2015": "zhang2015character",
    "Dernoncourt and Lee 2017": "dernoncourt2017pubmed",
    "Tuggener et al. 2020": "tuggener2020ledgar",
    "Demszky et al. 2020": "demszky2020goemotions",
    "Tunstall et al. 2022": "tunstall2022setfit",
    "Chen et al. 2023": "chen2023frugalgpt",
    "Ong et al. 2024": "ong2024routellm",
    "Hsieh et al. 2023": "hsieh2023distilling",
    "Lin et al. 2023": "lin2023swiftsage",
    "Yin et al. 2019": "yin2019benchmarking",
    "Schick and Schütze 2021": "schick2021exploiting",
    "Mishra et al. 2022": "mishra2022cross",
    "Hancock et al. 2018": "hancock2018training",
    "Ratner et al. 2017": "ratner2017snorkel",
    "Pryzant et al. 2023": "pryzant2023automatic",
    "Raghavan et al. 2006": "raghavan2006active",
    "Druck et al. 2009": "druck2009active",
    "Li et al. 2023": "li2023eliciting",
    "Tamkin et al. 2023": "tamkin2023task",
}

CITE = re.compile(r"\[([^\[\]]*?(?:19|20)\d\d[a-z]?(?:\s*;[^\[\]]*)?)\]")
UNICODE = {"–": "--", "—": "---", "§": r"\S{}", "≥": r"$\geq$", "≤": r"$\leq$", "√": r"$\surd$",
           "·": r"$\cdot$", "×": r"$\times$", "≈": r"$\approx$", "→": r"$\rightarrow$", "−": "-"}


def cite(m: re.Match[str]) -> str:
    keys = []
    for part in m.group(1).split(";"):
        name = " ".join(part.split())
        if name not in CITE_KEYS:
            raise SystemExit(f"unknown citation [{name}]: add it to CITE_KEYS and acl/references.bib")
        keys.append(CITE_KEYS[name])
    return r"\citep{" + ",".join(keys) + "}"


def inline(text: str) -> str:
    stash: list[str] = []

    def keep(s: str) -> str:
        stash.append(s)
        return f"\x00{len(stash) - 1}\x00"

    text = CITE.sub(lambda m: keep(cite(m)), text)
    text = re.sub(r"`([^`]+)`", lambda m: keep(r"\texttt{" + escape(m.group(1)) + "}"), text)
    text = text.replace(r"\*", "\x01")
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\\emph{\1}", text)
    text = re.sub(r'"(?=\S)(.+?)(?<=\S)"', r"``\1''", text)
    text = text.replace("\x01", r"$^*$")
    for k, v in UNICODE.items():
        text = text.replace(k, v)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


def escape(text: str) -> str:
    text = text.replace("\\", r"\textbackslash{}")
    for ch in "$%&#_{}":
        text = text.replace(ch, "\\" + ch)
    return text.replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_numeric(col: list[str]) -> bool:
    plain = [re.sub(r"[*\\%$,()–\- /.]|pts|acc", "", c) for c in col]
    return all(p.isdigit() or p in ("", "—", "n/a") for p in plain)


def table(rows: list[list[str]], caption: str | None, number: int | None) -> str:
    head, body = rows[0], rows[2:]
    ncol = len(head)
    longest = max(len(c) for r in rows for c in r)
    wide = caption is not None and (ncol >= 5 or longest > 60)
    if wide:
        spec = "l" + "".join("R" if is_numeric([r[i] for r in body]) else "L" for i in range(1, ncol))
        env_open, env_close = r"\begin{tabularx}{\textwidth}{" + spec + "}", r"\end{tabularx}"
    elif longest > 40:
        spec = "".join("L" if max(len(r[i]) for r in rows) > 30 else "l" for i in range(ncol))
        env_open, env_close = r"\begin{tabularx}{\linewidth}{" + spec + "}", r"\end{tabularx}"
    else:
        spec = "l" + "".join("r" if is_numeric([r[i] for r in body]) else "l" for i in range(1, ncol))
        env_open, env_close = r"\begin{tabular}{" + spec + "}", r"\end{tabular}"
    lines = [env_open, r"\toprule", " & ".join(inline(c) for c in head) + r" \\", r"\midrule"]
    lines += [" & ".join(inline(c) for c in r) + r" \\" for r in body]
    lines += [r"\bottomrule", env_close]
    tab = "\n".join(lines)
    if env_open.startswith(r"\begin{tabular}"):
        tab = r"\begin{adjustbox}{max width=\linewidth}" + "\n" + tab + "\n" + r"\end{adjustbox}"
    if caption is None:
        return "\n".join([r"\begin{center}\small", tab, r"\end{center}"])
    env = "table*" if wide else "table"
    size = r"\centering\small\setlength{\tabcolsep}{3.5pt}" if wide else r"\centering\small"
    return "\n".join([rf"\begin{{{env}}}[t]", size, tab,
                      rf"\caption{{{inline(caption)}}}", rf"\label{{tab:{number}}}", rf"\end{{{env}}}"])


def blocks(text: str) -> list[str]:
    out, cur = [], []
    for line in text.split("\n"):
        if not line.strip():
            if cur:
                out.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def render(md: str) -> tuple[str, str, str]:
    comments = []

    def comment(m: re.Match[str]) -> str:
        comments.append("\n".join("% " + line for line in m.group(1).strip().splitlines()))
        return f"\n\n\x02{len(comments) - 1}\x02\n\n"

    md = re.sub(r"<!--(.*?)-->", comment, md, flags=re.DOTALL)
    bs = blocks(md)
    title = abstract = ""
    body: list[str] = []
    in_abstract = False
    expected_table = 1
    i = 0
    while i < len(bs):
        b = bs[i]
        first = b.split("\n")[0]
        if re.fullmatch(r"\x02\d+\x02", b.strip()):
            body.append(comments[int(b.strip()[1:-1])])
        elif first.startswith("# "):
            title = inline(first[2:].strip())
        elif b.strip() == "*Anonymous ACL submission*":
            pass
        elif first.startswith("## "):
            name = first[3:].strip()
            in_abstract = name == "Abstract"
            if not in_abstract:
                body.append(r"\section{" + inline(re.sub(r"^\d+\s+", "", name)) + "}")
        elif first.startswith("### "):
            body.append(r"\subsection{" + inline(re.sub(r"^\d+(\.\d+)*\s+", "", first[4:].strip())) + "}")
        elif first.startswith("|"):
            rows = [cells(line) for line in b.split("\n")]
            caption = number = None
            if i + 1 < len(bs) and (m := re.match(r"\*Table (\d+):\s*(.*)\*\s*$", " ".join(bs[i + 1].split()))):
                number, caption = int(m.group(1)), m.group(2)
                if number != expected_table:
                    raise SystemExit(f"Table {number} appears where LaTeX will number it {expected_table}")
                expected_table += 1
                i += 1
            body.append(table(rows, caption, number))
        elif re.match(r"\s*(- |\d+\. )", first):
            ordered = bool(re.match(r"\s*\d+\. ", first))
            items, cur = [], []
            for line in b.split("\n"):
                if re.match(r"\s*(- |\d+\. )", line) and not line.startswith("    "):
                    if cur:
                        items.append(" ".join(cur))
                    cur = [re.sub(r"^\s*(- |\d+\. )", "", line)]
                else:
                    cur.append(line.strip())
            items.append(" ".join(cur))
            env = "enumerate" if ordered else "itemize"
            body.append("\n".join([rf"\begin{{{env}}}"] + [r"\item " + inline(it) for it in items] + [rf"\end{{{env}}}"]))
        else:
            para = inline(" ".join(line.strip() for line in b.split("\n")))
            if in_abstract:
                abstract += para + "\n\n"
            else:
                body.append(para)
        i += 1
    return title, abstract.strip(), "\n\n".join(body)


TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[review]{acl}
\usepackage{times}
\usepackage{latexsym}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{inconsolata}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{adjustbox}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}

\title{%(title)s}
\author{Anonymous ACL submission}

\begin{document}
\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

%(body)s

\bibliography{references}

\end{document}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()
    title, abstract, body = render(SRC.read_text())
    tex = OUT_DIR / "paper.tex"
    tex.write_text(TEMPLATE % {"title": title, "abstract": abstract, "body": body})
    print(f"Wrote {tex.relative_to(HERE.parent)}")
    if not args.no_pdf:
        subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-quiet", "paper.tex"],
                       cwd=OUT_DIR, check=True)
        print(f"Built {(OUT_DIR / 'paper.pdf').relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
