# Relationship extraction: evaluation results

## dev set (70 sentences)

| Method | Pair P | Pair R | Pair F1 | Triple F1 | Microbe P | Metabolite P | Negated pairs asserted |
|---|---|---|---|---|---|---|---|
| rules_v1 | 0.69 | 0.93 | 0.79 | 0.59 | 0.80 | 1.00 | 12 / 13 |
| rules_v2 | 1.00 | 0.95 | 0.97 | 0.97 | 1.00 | 1.00 | 0 / 13 |

Calibration (precision of predicted pairs by confidence):

| Method | 0.00-0.50 | 0.50-0.70 | 0.70-0.85 | 0.85-1.00 |
|---|---|---|---|---|
| rules_v1 | 0.17 (n=18) | 0.70 (n=20) | 0.83 (n=70) | 0.33 (n=3) |
| rules_v2 | 1.00 (n=2) | 1.00 (n=76) |

<details><summary>rules_v1: 60 errors</summary>

| ID | Error | Predicted | Expected |
|---|---|---|---|
| s001 | wrong type | faecalibacterium prausnitzii -[produces]-> acetate | ['consumes', 'converts'] |
| s002 | wrong type | roseburia intestinalis -[consumes]-> butyrate | ['produces'] |
| s002 | wrong type | roseburia intestinalis -[produces]-> inulin | ['consumes'] |
| s003 | negated pair asserted | escherichia coli -[produces]-> butyrate | - |
| s004 | wrong type | lactobacillus reuteri -[produces]-> tmao | ['inhibits'] |
| s004 | spurious pair | lactobacillus reuteri -[produces]-> acetate | - |
| s004 | spurious pair | escherichia coli -[produces]-> tmao | - |
| s005 | spurious pair | gut bacteria -[produces]-> propionate | - |
| s006 | spurious pair | the production -[produces]-> butyrate | - |
| s008 | wrong type | bacteroides thetaiotaomicron -[produces]-> pectin | ['consumes'] |
| s010 | wrong type | bifidobacterium longum -[consumes]-> lactate | ['produces', 'converts'] |
| s010 | wrong type | bifidobacterium longum -[consumes]-> acetate | ['produces', 'converts'] |
| s011 | negated pair asserted | ruminococcus gnavus -[associates_with]-> secondary bile acids | - |
| s013 | wrong type | streptococcus mutans -[consumes]-> lactic acid | ['produces', 'converts'] |
| s016 | spurious pair | supplementation with -[activates]-> butyrate | - |
| s018 | wrong type | enterococcus faecalis -[produces]-> tyrosine | ['consumes', 'converts'] |
| s020 | wrong type | methanobrevibacter smithii -[produces]-> hydrogen | ['consumes'] |
| s021 | spurious pair | these results -[regulates]-> gaba | - |
| s022 | negated pair asserted | saccharomyces boulardii -[regulates]-> tmao | - |
| s023 | wrong type | escherichia coli -[produces]-> choline | ['consumes', 'converts'] |
| s023 | wrong type | klebsiella oxytoca -[produces]-> choline | ['consumes', 'converts'] |
| s024 | spurious pair | lipopolysaccharide from -[activates]-> lipopolysaccharide | - |
| s024 | wrong type | escherichia coli -[activates]-> lipopolysaccharide | ['produces'] |
| s028 | negated pair asserted | bacteroides vulgatus -[produces]-> butyrate | - |
| s030 | spurious pair | pseudomonas aeruginosa -[produces]-> cysteine | - |
| s031 | spurious pair | serotonin synthesis -[produces]-> serotonin | - |
| s034 | missed | - | bilophila wadsworthia -[consumes/converts]-> taurine |
| s036 | spurious pair | in contrast -[inhibits]-> lithocholic acid | - |
| s037 | negated pair asserted | bifidobacterium breve -[consumes]-> xylose | - |
| s040 | spurious pair | lachnospiraceae strengthen -[produces]-> short-chain fatty acids | - |
| s041 | wrong type | salmonella enterica -[activates]-> succinate | ['consumes'] |
| s042 | spurious pair | treatment with -[inhibits]-> lactate | - |
| s042 | spurious pair | akkermansia muciniphila -[inhibits]-> lactate | - |
| s043 | spurious pair | nissle was -[consumes]-> phenylalanine | - |
| s045 | wrong type | ruminococcus gnavus -[activates]-> butyrate | ['associates_with', 'inhibits'] |
| s046 | negated pair asserted | bacteroides ovatus -[consumes]-> inulin | - |
| s047 | spurious pair | glucose was -[consumes]-> glucose | - |
| s047 | spurious pair | glucose was -[consumes]-> ethanol | - |
| s047 | spurious pair | glucose was -[consumes]-> carbon dioxide | - |
| s047 | wrong type | saccharomyces cerevisiae -[consumes]-> ethanol | ['produces', 'converts'] |
| s047 | wrong type | saccharomyces cerevisiae -[consumes]-> carbon dioxide | ['produces', 'converts'] |
| s049 | missed | - | penicillium chrysogenum -[produces]-> penicillin |
| s052 | spurious pair | butyrate reduced -[inhibits]-> butyrate | - |
| s055 | spurious pair | our data -[produces]-> choline | - |
| s055 | spurious pair | our data -[produces]-> tma | - |
| s055 | negated pair asserted | blautia producta -[produces]-> choline | - |
| s055 | negated pair asserted | blautia producta -[produces]-> tma | - |
| s056 | missed | - | lactobacillus rhamnosus -[inhibits]-> tmao |
| s058 | spurious pair | fecal acetate -[associates_with]-> acetate | - |
| s060 | missed | - | lactobacillus brevis -[consumes/converts]-> glutamate |
| s060 | missed | - | lactobacillus brevis -[produces/converts]-> gaba |
| s061 | negated pair asserted | candida glabrata -[produces]-> ethanol | - |
| s061 | negated pair asserted | candida tropicalis -[produces]-> ethanol | - |
| s063 | wrong type | anaerostipes caccae -[consumes]-> butyrate | ['produces', 'converts'] |
| s066 | negated pair asserted | ruminococcus albus -[consumes]-> pectin | - |
| s067 | spurious pair | mice colonized -[inhibits]-> lps | - |
| s068 | wrong type | candida albicans -[produces]-> ethanol | ['consumes', 'converts'] |
| s069 | spurious pair | within the -[associates_with]-> choline | - |
| s069 | negated pair asserted | escherichia coli -[associates_with]-> choline | - |
| s070 | missed | - | bifidobacterium infantis -[consumes]-> human milk oligosaccharides |

</details>

<details><summary>rules_v2: 4 errors</summary>

| ID | Error | Predicted | Expected |
|---|---|---|---|
| s028 | missed | - | eubacterium rectale -[produces]-> butyrate |
| s034 | missed | - | bilophila wadsworthia -[consumes/converts]-> taurine |
| s046 | missed | - | bacteroides uniformis -[consumes]-> inulin |
| s070 | missed | - | bifidobacterium infantis -[consumes]-> human milk oligosaccharides |

</details>

## held-out set (30 sentences)

| Method | Pair P | Pair R | Pair F1 | Triple F1 | Microbe P | Metabolite P | Negated pairs asserted |
|---|---|---|---|---|---|---|---|
| rules_v1 | 0.67 | 0.94 | 0.78 | 0.59 | 0.81 | 1.00 | 6 / 6 |
| rules_v2 | 1.00 | 0.84 | 0.91 | 0.91 | 1.00 | 1.00 | 0 / 6 |

Calibration (precision of predicted pairs by confidence):

| Method | 0.00-0.50 | 0.50-0.70 | 0.70-0.85 | 0.85-1.00 |
|---|---|---|---|---|
| rules_v1 | 0.00 (n=7) | 0.75 (n=8) | 0.85 (n=26) | 0.50 (n=2) |
| rules_v2 | 1.00 (n=2) | 1.00 (n=24) |

<details><summary>rules_v1: 23 errors</summary>

| ID | Error | Predicted | Expected |
|---|---|---|---|
| h002 | wrong type | bifidobacterium bifidum -[produces]-> lactose | ['consumes'] |
| h003 | negated pair asserted | bacteroides fragilis -[produces]-> propionate | - |
| h006 | spurious pair | the synthesis -[produces]-> indole | - |
| h008 | wrong type | lactobacillus casei -[consumes]-> lactate | ['produces', 'converts'] |
| h008 | wrong type | lactobacillus gasseri -[consumes]-> lactate | ['produces', 'converts'] |
| h009 | spurious pair | fusobacterium nucleatum -[produces]-> lactate | - |
| h009 | spurious pair | veillonella parvula -[consumes]-> hydrogen sulfide | - |
| h009 | wrong type | veillonella parvula -[produces]-> lactate | ['consumes'] |
| h010 | spurious pair | gut microbes -[consumes]-> tryptophan | - |
| h011 | spurious pair | blautia obeum -[inhibits]-> choline | - |
| h012 | negated pair asserted | escherichia coli -[produces]-> butyrate | - |
| h012 | negated pair asserted | salmonella enterica -[produces]-> butyrate | - |
| h014 | wrong type | desulfovibrio piger -[produces]-> sulfate | ['consumes', 'converts'] |
| h015 | missed | - | ruminococcus gnavus -[associates_with/inhibits]-> butyrate |
| h016 | negated pair asserted | bacteroides thetaiotaomicron -[consumes]-> cellulose | - |
| h018 | wrong type | candida albicans -[consumes]-> ethanol | ['produces', 'converts'] |
| h021 | missed | - | helicobacter pylori -[produces/converts]-> ammonia |
| h022 | negated pair asserted | bifidobacterium longum -[produces]-> hydrogen sulfide | - |
| h024 | spurious pair | propionate production -[produces]-> propionate | - |
| h026 | spurious pair | choline was -[consumes]-> choline | - |
| h026 | negated pair asserted | bifidobacterium breve -[consumes]-> choline | - |
| h028 | spurious pair | bilophila abundance -[associates_with]-> hydrogen sulfide | - |
| h030 | wrong type | saccharomyces cerevisiae -[produces]-> sucrose | ['consumes', 'converts'] |

</details>

<details><summary>rules_v2: 5 errors</summary>

| ID | Error | Predicted | Expected |
|---|---|---|---|
| h002 | missed | - | bifidobacterium bifidum -[consumes]-> lactose |
| h015 | missed | - | ruminococcus gnavus -[associates_with/inhibits]-> butyrate |
| h021 | missed | - | helicobacter pylori -[produces/converts]-> ammonia |
| h023 | missed | - | clostridium butyricum -[produces]-> butyrate |
| h023 | missed | - | faecalibacterium prausnitzii -[produces]-> butyrate |

</details>
