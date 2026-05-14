/// Gene panels for lymphoma ctDNA tier classification.
/// Ported from `annotate_vcf.py` (whopark/ctDNA).
library;

/// Tier 1/2 — established lymphoma drivers with strong/potential clinical significance.
const Set<String> kTier12Genes = {
  // DLBCL / aggressive B-cell lymphoma drivers
  'TP53', 'MYC', 'BCL2', 'BCL6',
  'MYD88', 'CD79B', 'CD79A', 'CARD11', 'TNFAIP3',
  'KMT2D', 'CREBBP', 'EZH2', 'EP300', 'ARID1A',
  'NOTCH1', 'NOTCH2', 'PIM1', 'CCND1', 'CCND3',
  'SOCS1', 'SGK1', 'TET2', 'GNA13', 'IRF4',
  'FOXO1', 'MEF2B', 'PRDM1', 'NFKBIA', 'TCF3', 'ID3',
  'STAT6', 'TNFRSF14', 'B2M', 'CIITA', 'CD58', 'FAS',
  'BCL10', 'CD70', 'DTX1', 'UBE2A', 'SPEN',
  'IRF8', 'BTG1', 'KLHL6', 'TBL1XR1',
  // Targeted therapy genes
  'BTK', 'PLCG2', 'PI3KCA', 'PIK3CD', 'PIK3R1', 'PTEN', 'MTOR',
  'ALK', 'JAK1', 'JAK2', 'STAT3', 'STAT5B',
  'BRAF', 'KRAS', 'NRAS', 'MCL1',
  // Cell cycle / tumor suppressors
  'CDKN2A', 'RB1', 'FBXW7', 'POT1', 'ATM',
  // Splicing / signaling
  'SF3B1', 'BIRC3',
  // Other hematologic malignancy drivers
  'DNMT3A', 'IDH1', 'IDH2', 'NPM1', 'FLT3',
  'BCOR', 'BCORL1', 'DDX3X',
};

/// Tier 3 — broader cancer / lymphoma-associated genes (129 genes).
const Set<String> kTier3Genes = {
  // Chromatin / epigenetic
  'KMT2D', 'CREBBP', 'EP300', 'EZH2', 'ARID1A',
  'ARID1B', 'SMARCA4', 'SMARCB1', 'TET2', 'DNMT3A',
  'IDH2', 'IDH1', 'SETD2', 'KDM6A', 'KDM5C',
  'KMT2A', 'KMT2C', 'KMT2E', 'NSD2', 'NSD1',
  'ASXL1', 'ASXL2', 'BCOR', 'BCORL1',
  'CHD2', 'CHD4', 'ATRX', 'HIST1H1E', 'HIST1H1C', 'BCL7A',
  // DNA repair / cell cycle
  'TP53', 'ATM', 'ATR', 'CHEK1', 'CHEK2',
  'BRCA1', 'BRCA2', 'PALB2', 'RAD51', 'RAD51C', 'RAD51D',
  'FANCA', 'FANCD2', 'BLM', 'WRN',
  'MSH2', 'MSH6', 'MLH1', 'PMS2', 'POLE', 'POLD1', 'PARP1',
  'CDKN2A', 'CDKN2B', 'RB1', 'CCND1', 'CCND2', 'CCND3',
  'CDK4', 'CDK6', 'E2F1', 'MYC', 'BCL2', 'PTEN', 'TP73',
  // RTK / signaling
  'EGFR', 'ERBB2', 'ERBB3', 'ERBB4',
  'FGFR1', 'FGFR2', 'FGFR3',
  'PDGFRA', 'PDGFRB', 'KIT', 'MET', 'FLT3',
  'JAK1', 'JAK2', 'JAK3', 'STAT3', 'STAT5B',
  'KRAS', 'NRAS', 'HRAS', 'BRAF', 'MAP2K1', 'MAP2K2',
  'PIK3CA', 'PIK3CD', 'PIK3R1', 'AKT1', 'AKT2', 'AKT3', 'MTOR',
  'SYK', 'LYN', 'BLK', 'BTK', 'PLCG2',
  'CARD11', 'MYD88', 'IRAK4', 'TNFAIP3', 'NFKBIA',
  // Nuclear export
  'XPO1',
  // Splicing
  'SF3B1', 'SRSF2', 'U2AF1', 'U2AF2', 'ZRSR2',
  'PRPF8', 'PRPF40B', 'SF1',
  'RBM10', 'RBM15', 'RBM15B',
  'DDX3X', 'DDX41',
  'HNRNPK', 'HNRNPA1', 'HNRNPA2B1', 'SFPQ',
  'FUBP1', 'WTAP', 'LUC7L2', 'PHF5A', 'TCERG1', 'EFTUD2',
};

/// Actionable drug-target genes (FDA-approved or late-stage trial agents).
const Set<String> kDrugTargetGenes = {
  // RTK / kinase
  'KIT', 'EGFR', 'ERBB2', 'ERBB3',
  'FGFR1', 'FGFR2', 'FGFR3',
  'PDGFRA', 'MET', 'FLT3',
  // JAK / STAT
  'JAK1', 'JAK2', 'JAK3',
  // RAS / RAF / MEK
  'KRAS', 'NRAS', 'BRAF', 'MAP2K1', 'MAP2K2',
  // PI3K / AKT / mTOR
  'PIK3CA', 'PIK3CD', 'PIK3R1', 'AKT1', 'MTOR', 'PTEN',
  // BCR / NF-kB
  'BTK', 'PLCG2', 'CARD11', 'MYD88', 'IRAK4', 'SYK',
  // Epigenetic
  'EZH2', 'IDH1', 'IDH2',
  // Cell cycle
  'CDK4', 'CDK6',
  // DNA repair / PARP
  'BRCA1', 'BRCA2', 'PALB2', 'ATM', 'ATR', 'CHEK1', 'CHEK2', 'PARP1',
  // MMR / IO
  'MSH2', 'MSH6', 'MLH1', 'PMS2',
  // Splicing
  'SF3B1', 'SRSF2', 'DDX3X', 'DDX41',
  // Lymphoma-specific
  'XPO1', 'PIM1', 'BIRC3',
};

/// Risk stratification / prognostic genes.
const Set<String> kRiskStratificationGenes = {
  'TP53',
  'MYC', 'BCL2',
  'KMT2D', 'CREBBP', 'EP300', 'KMT2C',
  'ARID1A',
  'DNMT3A', 'TET2', 'ASXL1',
  'SETD2', 'BCOR',
  'FBXW7',
  'CDKN2A', 'RB1', 'CCND1',
  'STAT3', 'STAT5B',
  'TNFAIP3', 'NFKBIA',
};

/// Combined actionable Tier 3 whitelist (drug targets ∪ risk stratification).
Set<String> get kActionableTier3Genes =>
    {...kDrugTargetGenes, ...kRiskStratificationGenes};

/// Example targeted agents per gene — abbreviated catalogue for the viewer.
const Map<String, String> kTherapyHints = {
  'KIT': 'imatinib, sunitinib, avapritinib, ripretinib',
  'EGFR': 'osimertinib, erlotinib, gefitinib',
  'ERBB2': 'trastuzumab, T-DXd, tucatinib',
  'FGFR1': 'erdafitinib, pemigatinib',
  'FGFR2': 'erdafitinib, pemigatinib, futibatinib',
  'FGFR3': 'erdafitinib',
  'PDGFRA': 'imatinib, avapritinib',
  'MET': 'capmatinib, tepotinib',
  'FLT3': 'midostaurin, gilteritinib, quizartinib',
  'JAK1': 'ruxolitinib, itacitinib',
  'JAK2': 'ruxolitinib, fedratinib, pacritinib',
  'JAK3': 'tofacitinib',
  'KRAS': 'sotorasib, adagrasib (G12C)',
  'NRAS': 'binimetinib + ribociclib (trial)',
  'BRAF': 'vemurafenib, dabrafenib, encorafenib',
  'MAP2K1': 'trametinib, cobimetinib',
  'MAP2K2': 'trametinib',
  'PIK3CA': 'alpelisib, inavolisib',
  'PIK3CD': 'idelalisib, umbralisib',
  'PIK3R1': 'alpelisib (context)',
  'AKT1': 'capivasertib',
  'MTOR': 'everolimus, temsirolimus',
  'PTEN': 'PI3K/AKT pathway inhibitors',
  'BTK': 'ibrutinib, acalabrutinib, zanubrutinib, pirtobrutinib',
  'PLCG2': 'BTK-inhibitor resistance marker',
  'CARD11': 'NF-kB pathway, BTKi resistance',
  'MYD88': 'ibrutinib (WM, MYD88 L265P)',
  'IRAK4': 'IRAK4 inhibitors (trial)',
  'SYK': 'fostamatinib',
  'EZH2': 'tazemetostat',
  'IDH1': 'ivosidenib',
  'IDH2': 'enasidenib',
  'CDK4': 'palbociclib, ribociclib, abemaciclib',
  'CDK6': 'palbociclib, ribociclib, abemaciclib',
  'BRCA1': 'olaparib, niraparib, rucaparib, talazoparib',
  'BRCA2': 'olaparib, niraparib, rucaparib, talazoparib',
  'PALB2': 'PARP inhibitors',
  'ATM': 'ceralasertib (ATRi), PARPi',
  'ATR': 'ceralasertib, berzosertib',
  'CHEK1': 'prexasertib (trial)',
  'CHEK2': 'PARPi (context)',
  'PARP1': 'PARP inhibitors',
  'MSH2': 'pembrolizumab (MSI-H), dostarlimab',
  'MSH6': 'pembrolizumab (MSI-H), dostarlimab',
  'MLH1': 'pembrolizumab (MSI-H), dostarlimab',
  'PMS2': 'pembrolizumab (MSI-H), dostarlimab',
  'SF3B1': 'H3B-8800 (trial)',
  'XPO1': 'selinexor (XPOVIO)',
  'PIM1': 'AZD1208 (trial)',
  'BIRC3': 'NF-kB / SMAC mimetics (trial)',
};
