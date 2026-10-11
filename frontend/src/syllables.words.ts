// Words a child of class 1 to 4 meets, each with its breaks as school teaches them (Sprechsilben): the Duden's
// Worttrennung in the reformed spelling, and a vowel spoken alone stands alone ("A-bend", "Ra-di-o").
// Written by hand before the splitter ran on any of them: the test measures the module against this list.
// Each word stands once, under the kind it is the plainest case of.
export const WORDS: Record<string, string[]> = {
  compound: [
    "Haus-tür", "Fuß-ball-spiel", "Haus-auf-ga-be", "Schul-hof", "Kin-der-gar-ten", "Bahn-hof", "Ap-fel-baum",
    "Schnee-mann", "Hand-schuh", "Früh-stück", "Ge-burts-tag", "Fahr-rad", "Schul-ta-sche", "Blu-men-topf",
    "Re-gen-bo-gen", "Son-nen-schein", "Zahn-bürs-te", "Bil-der-buch", "Wohn-zim-mer", "Fuß-bo-den", "Nach-mit-tag",
    "Tisch-de-cke", "Brief-kas-ten", "Weih-nachts-baum", "Os-ter-ei", "Vo-gel-nest", "Klas-sen-zim-mer",
    "Tür-klin-ke", "Au-to-bahn", "Was-ser-hahn", "Kran-ken-haus", "Feu-er-wehr", "Erd-bee-re", "But-ter-brot",
    "Spiel-zeug", "Mit-tag-es-sen", "A-bend-es-sen", "Haus-tier", "Fern-se-her", "Turn-hal-le", "Schwimm-bad",
    "Pau-sen-brot", "Le-se-buch", "Diens-tag", "Don-ners-tag", "Sams-tag", "Sonn-tag", "Mitt-woch", "Mon-tag",
    "Frei-tag", "Kühl-schrank", "Lö-wen-zahn", "Tier-arzt", "Stra-ßen-bahn",
  ],
  double: [
    "Was-ser", "Mut-ter", "But-ter", "Him-mel", "Som-mer", "Son-ne", "Tel-ler", "Löf-fel", "Kof-fer", "Pup-pe",
    "Sup-pe", "Bet-ten", "ren-nen", "schwim-men", "kom-men", "fal-len", "hof-fen", "Wet-ter", "Zim-mer", "Klas-se",
    "Tas-se", "es-sen", "mes-sen", "Af-fe", "Rob-be", "Wel-le", "Ham-mer", "Num-mer", "Schlüs-sel", "bit-ten",
    "tref-fen", "Qual-le", "kön-nen", "müs-sen", "wol-len", "im-mer", "Bag-ger", "Schmet-ter-ling",
  ],
  ck: [
    "Zu-cker", "ba-cken", "De-cke", "Ja-cke", "Brü-cke", "Mü-cke", "Schne-cke", "pa-cken", "le-cker", "Glo-cke",
    "He-cke", "So-cke", "di-cker", "schme-cken", "we-cken", "Rü-cken", "Bä-cker", "Lü-cke", "gu-cken", "Stü-cke",
    "tro-cken", "drü-cken", "Ho-cker", "zwi-cken",
  ],
  sch: [
    "Ta-sche", "Fla-sche", "Du-sche", "wa-schen", "Fi-sche", "Ti-sche", "Kir-sche", "Men-schen", "zwi-schen",
    "wün-schen", "Ma-schi-ne", "Schu-le", "Scho-ko-la-de", "Sche-re", "Schau-kel", "schrei-ben", "Ge-schich-te",
    "Ge-schenk", "fri-sche", "Bü-sche", "mi-schen", "Frö-sche", "na-schen", "Rut-sche", "Deutsch-land",
  ],
  ch: [
    "Kü-che", "la-chen", "ma-chen", "Ku-chen", "su-chen", "Bü-cher", "Dä-cher", "Lö-cher", "Wo-che", "spre-chen",
    "ko-chen", "Ei-che", "Kno-chen", "Sa-chen", "bre-chen", "Mäd-chen", "Häus-chen", "Kir-che", "rie-chen",
    "brau-chen", "leuch-ten", "Toch-ter", "Nach-bar", "wich-tig", "rich-tig", "Be-cher", "si-cher", "Dra-chen",
    "Zei-chen", "Mär-chen", "Hähn-chen", "Fich-te",
  ],
  st: [
    "Fens-ter", "Kas-ten", "Schwes-ter", "Os-tern", "Wes-te", "Kis-te", "Lis-te", "Pflas-ter", "Meis-ter",
    "bes-te", "ges-tern", "Hus-ten", "Küs-te", "kos-ten", "Pos-ter", "Nes-ter", "Bürs-te", "durs-tig", "lus-tig",
    "ers-te", "Wüs-te", "flüs-tern", "Bahn-steig", "Blei-stift", "ver-ste-hen", "auf-ste-hen", "Stie-fel",
    "Stun-de", "be-stel-len", "Buch-sta-be", "Bau-stel-le",
  ],
  sp: [
    "Wes-pe", "Spiel-platz", "Kas-per", "Knos-pe", "lis-peln", "Ras-pel", "Ves-per", "wis-pern", "Spie-gel",
    "spa-ren", "sprin-gen", "Spin-ne", "Spa-ten", "spit-zen", "Bei-spiel", "ver-spre-chen", "Spra-che", "spü-len",
    "Spei-se", "spa-zie-ren", "Spat-zen", "aus-spre-chen",
  ],
  diphthong: [
    "Eu-le", "Bau-er", "Feu-er", "Ei-er", "Mäu-se", "Häu-ser", "Bäu-me", "Lei-ter", "Rei-se", "Sei-fe", "Zei-tung",
    "heu-te", "Leu-te", "Freun-de", "neu-e", "teu-er", "Mau-er", "sau-er", "Trau-be", "Tau-be", "lau-fen",
    "kau-fen", "Au-ge", "Au-to", "ei-ne", "Ei-mer", "Ei-sen", "Eu-ro", "Kai-ser", "träu-men", "Räu-ber", "bau-en",
    "schau-en", "schrei-en", "Bei-ne", "klei-ne", "Wei-de", "freu-en", "Scheu-ne", "Kreu-zung", "Steu-er",
    "Treu-e", "Frau-en", "blau-e", "schlau-er", "Pau-se", "Säu-le", "Läu-fer", "läu-ten",
  ],
  one_letter: [
    "A-bend", "O-fen", "I-gel", "E-sel", "U-hu", "ü-ber", "Ra-di-o", "O-ma", "O-pa", "A-mei-se", "E-le-fant",
    "I-dee", "U-fer", "o-der", "a-ber", "e-ben", "ü-ben", "Ü-bung", "Ö-fen", "O-ze-an", "E-cke", "I-ta-li-en",
    "A-na-nas", "O-ran-ge", "O-li-ve", "A-tem", "e-wig", "O-a-se", "Vi-de-o", "Stu-di-o", "A-ben-teu-er",
    "ü-ber-all", "Ü-ber-ra-schung", "e-gal", "A-qua-ri-um", "o-ben", "A-horn", "A-der", "ü-bel", "U-ni-form",
  ],
  umlaut: [
    "Äp-fel", "Vö-gel", "Kä-se", "Bä-ren", "Tü-re", "Kä-fer", "Blü-te", "Hü-te", "Kö-nig", "Lö-we", "Mö-we",
    "Mül-ler", "Müt-ze", "Kör-per", "Wör-ter", "Gär-ten", "Vä-ter", "Brü-der", "Müt-ter", "Töch-ter", "Hän-de",
    "Zäh-ne", "Füch-se", "fröh-lich", "glück-lich", "zäh-len", "hö-ren", "füh-len", "wäh-len", "Kü-he", "Zü-ge",
    "Flü-gel", "Hü-gel", "Rä-der", "Glä-ser", "Blät-ter", "Nüs-se", "Flüs-se", "Stüh-le", "Äs-te", "Är-mel",
  ],
  eszett: [
    "Stra-ße", "hei-ßen", "Fuß", "Fü-ße", "grü-ßen", "sü-ße", "wei-ße", "gro-ße", "Grö-ße", "drau-ßen", "au-ßen",
    "bei-ßen", "flie-ßen", "gie-ßen", "schlie-ßen", "Spaß", "Gruß", "So-ße", "Klö-ße", "flei-ßig", "drei-ßig",
    "sto-ßen", "schie-ßen", "Fuß-ball", "heiß", "weiß", "groß", "süß",
  ],
  one_syllable: [
    "Maus", "Baum", "Knie", "Strumpf", "Haus", "Hund", "Tisch", "Buch", "Kind", "Ball", "Brot", "Milch", "Herbst",
    "Obst", "Schrank", "Pferd", "Arzt", "Zwerg", "Frosch", "Stuhl", "Stern", "Tür", "Bär", "schön", "grün", "Zoo",
    "See", "Schnee", "Tee", "Schuh", "Kuh", "Reh", "Ohr", "Uhr", "Eis", "Ei", "Heu", "blau", "neu", "acht", "elf",
    "zwölf", "fünf", "schwarz", "Angst", "ich", "du", "und", "im", "Mai", "Tier", "vier", "Spiel", "Dieb", "Lied",
    "Sport", "Nacht",
  ],
  prefix: [
    "be-ob-ach-ten", "ver-ges-sen", "er-in-nern", "be-kom-men", "ver-ste-cken", "er-zäh-len", "ent-de-cken",
    "zer-bre-chen", "ge-fal-len", "be-su-chen", "ver-lie-ren", "er-klä-ren", "ge-win-nen", "an-fan-gen",
    "auf-räu-men", "aus-ma-len", "ein-kau-fen", "vor-le-sen", "mit-brin-gen", "ab-ho-len", "zu-hö-ren",
    "un-ter-schrei-ben", "ü-ber-le-gen", "um-zie-hen", "weg-lau-fen", "hin-fal-len", "vor-sich-tig", "Un-ter-richt",
    "Ant-wort", "Ur-laub", "un-glück-lich", "Ge-mü-se", "Be-ruf", "Ver-kehr", "ver-rei-sen", "be-en-den",
    "be-ei-len", "voll-en-den", "er-ar-bei-ten", "auf-es-sen", "an-zie-hen", "be-ant-wor-ten",
  ],
  hiatus: [
    "Fa-mi-li-e", "Fe-ri-en", "The-a-ter", "Lie-be", "spie-len", "Tie-re", "vie-le", "sie-ben", "Wie-se", "Bie-ne",
    "flie-gen", "lie-gen", "Zie-ge", "Brie-fe", "Die-be", "nie-mand", "wie-der", "Pa-pier", "Kla-vier", "Li-ni-e",
    "Li-li-e", "Ma-te-ri-al", "Mu-se-um", "Na-ti-on", "Sta-ti-on", "Mil-li-on", "Me-lo-die", "Fan-ta-sie",
    "Ru-i-ne", "Se-en", "Le-o-pard", "Di-no-sau-ri-er", "Spa-ni-en", "Vi-o-li-ne", "In-di-a-ner", "kni-en",
    "Zwie-bel", "Flie-ge", "schie-ben", "krie-chen", "Rie-se", "die-se", "Ja-nu-ar", "Li-ne-al", "Sta-di-on",
    "pro-bie-ren", "se-hen", "ge-hen", "Schu-he", "nä-hen", "dre-hen", "Rei-he", "ru-hig", "sä-en",
  ],
};
