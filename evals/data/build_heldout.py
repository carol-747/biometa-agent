"""Held-out relationship benchmark: v2 was never inspected against these.

Same labeling scheme as build_benchmark.py. Used only for final reporting, to
show the improvement isn't from tuning the rules to the dev sentences.
"""
import json
from pathlib import Path

P, C, V, I, A, R, S, X = ("produces", "consumes", "converts", "inhibits", "activates",
                          "regulates", "associates_with", "interacts")

ITEMS = [
    ("Roseburia hominis produces butyrate from dietary fiber.",
     ["Roseburia hominis"], ["butyrate"], [("Roseburia hominis", "butyrate", [P])], [], ["simple"]),
    ("Acetate is produced by Bifidobacterium bifidum during growth on lactose.",
     ["Bifidobacterium bifidum"], ["Acetate", "lactose"],
     [("Bifidobacterium bifidum", "Acetate", [P]), ("Bifidobacterium bifidum", "lactose", [C])], [], ["passive"]),
    ("Bacteroides fragilis did not produce propionate in this assay.",
     ["Bacteroides fragilis"], ["propionate"], [], [("Bacteroides fragilis", "propionate")], ["negation"]),
    ("Clostridium difficile was inhibited by secondary bile acids.",
     ["Clostridium difficile"], ["secondary bile acids"],
     [("Clostridium difficile", "secondary bile acids", [I])], [], ["metabolite-acts"]),
    ("Prevotella copri abundance was associated with higher branched-chain amino acids.",
     ["Prevotella copri"], [], [], [], ["oov-metabolite"]),
    ("The synthesis of indole was enhanced in germ-free mice.",
     [], ["indole"], [], [], ["false-entity"]),
    ("Eubacterium limosum converts methanol to acetate.",
     ["Eubacterium limosum"], ["methanol", "acetate"],
     [("Eubacterium limosum", "acetate", [P, V])], [], ["substrate", "oov-metabolite"]),
    ("Lactobacillus casei and Lactobacillus gasseri both ferment glucose to lactate.",
     ["Lactobacillus casei", "Lactobacillus gasseri"], ["glucose", "lactate"],
     [("Lactobacillus casei", "glucose", [C, V]), ("Lactobacillus gasseri", "glucose", [C, V]),
      ("Lactobacillus casei", "lactate", [P, V]), ("Lactobacillus gasseri", "lactate", [P, V])],
     [], ["coordination", "substrate"]),
    ("Fusobacterium nucleatum produces hydrogen sulfide, whereas Veillonella parvula consumes lactate.",
     ["Fusobacterium nucleatum", "Veillonella parvula"], ["hydrogen sulfide", "lactate"],
     [("Fusobacterium nucleatum", "hydrogen sulfide", [P]), ("Veillonella parvula", "lactate", [C])],
     [], ["multi-clause", "oov-microbe"]),
    ("Gut microbes metabolize tryptophan.", [], ["tryptophan"], [], [], ["generic-microbe"]),
    ("Blautia obeum reduced TMA formation from choline.",
     ["Blautia obeum"], ["TMA", "choline"], [("Blautia obeum", "TMA", [I])], [], ["simple"]),
    ("Neither Escherichia coli nor Salmonella enterica produced butyrate.",
     ["Escherichia coli", "Salmonella enterica"], ["butyrate"], [],
     [("Escherichia coli", "butyrate"), ("Salmonella enterica", "butyrate")], ["negation", "coordination"]),
    ("Streptococcus thermophilus secretes folate during yogurt fermentation.",
     ["Streptococcus thermophilus"], ["folate"], [("Streptococcus thermophilus", "folate", [P])], [], ["simple"]),
    ("Desulfovibrio piger generates hydrogen sulfide from sulfate.",
     ["Desulfovibrio piger"], ["hydrogen sulfide", "sulfate"],
     [("Desulfovibrio piger", "hydrogen sulfide", [P]), ("Desulfovibrio piger", "sulfate", [C, V])],
     [], ["oov-microbe", "substrate"]),
    ("Colonic butyrate was depleted in patients with Ruminococcus gnavus overgrowth.",
     ["Ruminococcus gnavus"], ["butyrate"], [("Ruminococcus gnavus", "butyrate", [S, I])], [], ["association"]),
    ("Bacteroides thetaiotaomicron does not utilize cellulose but degrades xylan.",
     ["Bacteroides thetaiotaomicron"], ["cellulose"], [],
     [("Bacteroides thetaiotaomicron", "cellulose")], ["negation", "oov-metabolite"]),
    ("Akkermansia muciniphila was positively correlated with propionate.",
     ["Akkermansia muciniphila"], ["propionate"], [("Akkermansia muciniphila", "propionate", [S, A])], [], ["association"]),
    ("Candida albicans ferments glucose to ethanol.",
     ["Candida albicans"], ["glucose", "ethanol"],
     [("Candida albicans", "glucose", [C, V]), ("Candida albicans", "ethanol", [P, V])], [], ["substrate"]),
    ("Supplementation with inulin raised fecal acetate in healthy volunteers.",
     [], ["inulin", "acetate"], [], [], ["false-entity", "no-microbe"]),
    ("Enterococcus faecalis produces tyramine, which may raise blood pressure.",
     ["Enterococcus faecalis"], ["tyramine"], [("Enterococcus faecalis", "tyramine", [P])], [], ["distractor"]),
    ("Helicobacter pylori urease hydrolyzes urea to ammonia.",
     ["Helicobacter pylori"], ["urea", "ammonia"],
     [("Helicobacter pylori", "ammonia", [P, V])], [], ["oov-metabolite", "substrate"]),
    ("Bifidobacterium longum was unable to produce hydrogen sulfide.",
     ["Bifidobacterium longum"], ["hydrogen sulfide"], [],
     [("Bifidobacterium longum", "hydrogen sulfide")], ["negation"]),
    ("Clostridium butyricum and Faecalibacterium prausnitzii are major butyrate producers.",
     ["Clostridium butyricum", "Faecalibacterium prausnitzii"], ["butyrate"],
     [("Clostridium butyricum", "butyrate", [P]), ("Faecalibacterium prausnitzii", "butyrate", [P])],
     [], ["nominal", "coordination"]),
    ("Propionate production by Bacteroides vulgatus was confirmed by isotope labeling.",
     ["Bacteroides vulgatus"], ["Propionate"], [("Bacteroides vulgatus", "Propionate", [P])], [], ["nominal"]),
    ("Lactobacillus plantarum modulates serotonin signaling in the gut.",
     ["Lactobacillus plantarum"], ["serotonin"], [("Lactobacillus plantarum", "serotonin", [R])], [], ["simple"]),
    ("Choline was not metabolized by Bifidobacterium breve.",
     ["Bifidobacterium breve"], ["Choline"], [], [("Bifidobacterium breve", "Choline")], ["negation", "passive"]),
    ("Streptomyces coelicolor synthesizes actinorhodin.",
     ["Streptomyces coelicolor"], [], [], [], ["oov-metabolite"]),
    ("Higher Bilophila abundance was linked to elevated hydrogen sulfide.",
     [], ["hydrogen sulfide"], [], [], ["genus-only"]),
    ("Anaerostipes hadrus converts lactate and acetate into butyrate.",
     ["Anaerostipes hadrus"], ["lactate", "acetate", "butyrate"],
     [("Anaerostipes hadrus", "lactate", [C, V]), ("Anaerostipes hadrus", "acetate", [C, V]),
      ("Anaerostipes hadrus", "butyrate", [P, V])], [], ["substrate", "coordination"]),
    ("Saccharomyces cerevisiae produces ethanol and carbon dioxide from sucrose.",
     ["Saccharomyces cerevisiae"], ["ethanol", "carbon dioxide", "sucrose"],
     [("Saccharomyces cerevisiae", "ethanol", [P]), ("Saccharomyces cerevisiae", "carbon dioxide", [P]),
      ("Saccharomyces cerevisiae", "sucrose", [C, V])], [], ["coordination", "substrate"]),
]


def main():
    out = Path(__file__).with_name("relation_heldout.jsonl")
    with out.open("w") as f:
        for k, (text, mics, mets, rels, neg, tags) in enumerate(ITEMS, 1):
            for m in mics: assert m in text, (k, m)
            for x in mets: assert x in text, (k, x)
            for m, x, *_ in rels + [(a, b) for a, b in neg]:
                assert m in mics and x in mets, (k, m, x)
            f.write(json.dumps({
                "id": f"h{k:03d}", "text": text, "microbes": mics, "metabolites": mets,
                "relations": [{"microbe": m, "metabolite": x, "types": t} for m, x, t in rels],
                "negated": [{"microbe": m, "metabolite": x} for m, x in neg], "tags": tags,
            }) + "\n")
    print(f"wrote {len(ITEMS)} items to {out}")


if __name__ == "__main__":
    main()
