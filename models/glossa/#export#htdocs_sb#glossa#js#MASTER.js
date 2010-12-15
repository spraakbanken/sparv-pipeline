
var htmlRoot = '/glossa/';
var cgiRoot = '/cgi-bin/glossa/';

var Menu = new Array;
var conf = new Array;
var languageOpts = new Array;

var language = 'swe';

function standardDefaultMenu() {
    return new Hash(1, new Hash(
	"contents", "<nobr> alternativ » </nobr>", 

	1, new Hash(
	    "contents", "ord » ", 
	    1, new Hash("contents", "lemma/grundform", "type", "js", "uri", "addOpt('w','lemma','lemma/grundform')"), 
	    2, new Hash("contents", "storlekskänsligt", "type", "js", "uri", "addOpt('w','case','storlekskänsligt')"), 
	    3, new Hash("contents", "i början av ord", "type", "js", "uri", "addOpt('w','start','i början av ord')"), 
	    4, new Hash("contents", "i slutet av ord", "type", "js", "uri", "addOpt('w','end','i slutet av ord')"), 
	    5, new Hash("contents", "i mitten av ord", "type", "js", "uri", "addOpt('w','middle','i mitten av ord')"), 
	    6, new Hash("contents", "uteslut", "type", "js", "uri", "addOpt('w','neg','uteslut')")), 

	2, new Hash(
	    "contents", "ordklassen är » ", 
            1, new Hash("contents", "adverb", "type", "js", "uri", "addOpt('pos', 'AB', 'adverb (AB)')"),
            2, new Hash("contents", "interpunktion", "type", "js", "uri", "addOpt('pos', 'DL', 'interpunktion (DL)')"),
            3, new Hash("contents", "determinerare", "type", "js", "uri", "addOpt('pos', 'DT', 'determinerare (DT)')"),
            4, new Hash("contents", "frågande/relativt adverb", "type", "js", "uri", "addOpt('pos', 'HA', 'frågande/relativt adverb (HA)')"),
            5, new Hash("contents", "frågande/relativ determinerare", "type", "js", "uri", "addOpt('pos', 'HD', 'frågande/relativ determinerare (HD)')"),
            6, new Hash("contents", "frågande/relativt pronomen", "type", "js", "uri", "addOpt('pos', 'HP', 'frågande/relativt pronomen (HP)')"),
            7, new Hash("contents", "frågande/relativt possessivt pronomen", "type", "js", "uri", "addOpt('pos', 'HS', 'frågande/relativt possessivt pronomen (HS)')"),
            8, new Hash("contents", "infinitivmärke", "type", "js", "uri", "addOpt('pos', 'IE', 'infinitivmärke (IE)')"),
            9, new Hash("contents", "interjektion", "type", "js", "uri", "addOpt('pos', 'IN', 'interjektion (IN)')"),
            10, new Hash("contents", "adjektiv", "type", "js", "uri", "addOpt('pos', 'JJ', 'adjektiv (JJ)')"),
            11, new Hash("contents", "konjunktion", "type", "js", "uri", "addOpt('pos', 'KN', 'konjunktion (KN)')"),
            12, new Hash("contents", "substantiv", "type", "js", "uri", "addOpt('pos', 'NN', 'substantiv (NN)')"),
            13, new Hash("contents", "particip", "type", "js", "uri", "addOpt('pos', 'PC', 'particip (PC)')"),
            14, new Hash("contents", "partikel", "type", "js", "uri", "addOpt('pos', 'PL', 'partikel (PL)')"),
            15, new Hash("contents", "egennamn", "type", "js", "uri", "addOpt('pos', 'PM', 'egennamn (PM)')"),
            16, new Hash("contents", "pronomen", "type", "js", "uri", "addOpt('pos', 'PN', 'pronomen (PN)')"),
            17, new Hash("contents", "preposition", "type", "js", "uri", "addOpt('pos', 'PP', 'preposition (PP)')"),
            18, new Hash("contents", "possessivt pronomen", "type", "js", "uri", "addOpt('pos', 'PS', 'possessivt pronomen (PS)')"),
            19, new Hash("contents", "grundtal", "type", "js", "uri", "addOpt('pos', 'RG', 'grundtal (RG)')"),
            20, new Hash("contents", "ordningstal", "type", "js", "uri", "addOpt('pos', 'RO', 'ordningstal (RO)')"),
            21, new Hash("contents", "subjunktion", "type", "js", "uri", "addOpt('pos', 'SN', 'subjunktion (SN)')"),
            22, new Hash("contents", "utländskt ord", "type", "js", "uri", "addOpt('pos', 'UO', 'utländskt ord (UO)')"),
            23, new Hash("contents", "verb", "type", "js", "uri", "addOpt('pos', 'VB', 'verb (VB)')")),

	3, new Hash(
	    "contents", "ordklassen är inte » ", 
            1, new Hash("contents", "adverb", "type", "js", "uri", "addOpt('pos', '!AB', 'inte adverb (AB)')"),
            2, new Hash("contents", "interpunktion", "type", "js", "uri", "addOpt('pos', '!DL', 'inte interpunktion (DL)')"),
            3, new Hash("contents", "determinerare", "type", "js", "uri", "addOpt('pos', '!DT', 'inte determinerare (DT)')"),
            4, new Hash("contents", "frågande/relativt adverb", "type", "js", "uri", "addOpt('pos', '!HA', 'inte frågande/relativt adverb (HA)')"),
            5, new Hash("contents", "frågande/relativ determinerare", "type", "js", "uri", "addOpt('pos', '!HD', 'inte frågande/relativ determinerare (HD)')"),
            6, new Hash("contents", "frågande/relativt pronomen", "type", "js", "uri", "addOpt('pos', '!HP', 'inte frågande/relativt pronomen (HP)')"),
            7, new Hash("contents", "frågande/relativt possessivt pronomen", "type", "js", "uri", "addOpt('pos', '!HS', 'inte frågande/relativt possessivt pronomen (HS)')"),
            8, new Hash("contents", "infinitivmärke", "type", "js", "uri", "addOpt('pos', '!IE', 'inte infinitivmärke (IE)')"),
            9, new Hash("contents", "interjektion", "type", "js", "uri", "addOpt('pos', '!IN', 'inte interjektion (IN)')"),
            10, new Hash("contents", "adjektiv", "type", "js", "uri", "addOpt('pos', '!JJ', 'inte adjektiv (JJ)')"),
            11, new Hash("contents", "konjunktion", "type", "js", "uri", "addOpt('pos', '!KN', 'inte konjunktion (KN)')"),
            12, new Hash("contents", "substantiv", "type", "js", "uri", "addOpt('pos', '!NN', 'inte substantiv (NN)')"),
            13, new Hash("contents", "particip", "type", "js", "uri", "addOpt('pos', '!PC', 'inte particip (PC)')"),
            14, new Hash("contents", "partikel", "type", "js", "uri", "addOpt('pos', '!PL', 'inte partikel (PL)')"),
            15, new Hash("contents", "egennamn", "type", "js", "uri", "addOpt('pos', '!PM', 'inte egennamn (PM)')"),
            16, new Hash("contents", "pronomen", "type", "js", "uri", "addOpt('pos', '!PN', 'inte pronomen (PN)')"),
            17, new Hash("contents", "preposition", "type", "js", "uri", "addOpt('pos', '!PP', 'inte preposition (PP)')"),
            18, new Hash("contents", "possessivt pronomen", "type", "js", "uri", "addOpt('pos', '!PS', 'inte possessivt pronomen (PS)')"),
            19, new Hash("contents", "grundtal", "type", "js", "uri", "addOpt('pos', '!RG', 'inte grundtal (RG)')"),
            20, new Hash("contents", "ordningstal", "type", "js", "uri", "addOpt('pos', '!RO', 'inte ordningstal (RO)')"),
            21, new Hash("contents", "subjunktion", "type", "js", "uri", "addOpt('pos', '!SN', 'inte subjunktion (SN)')"),
            22, new Hash("contents", "utländskt ord", "type", "js", "uri", "addOpt('pos', '!UO', 'inte utländskt ord (UO)')"),
            23, new Hash("contents", "verb", "type", "js", "uri", "addOpt('pos', '!VB', 'inte verb (VB)')")),

	4, new Hash(
            "contents", "förekomster » ", 
            1, new Hash("contents", "noll eller en", "type", "js", "uri", "addOpt('occ','?','noll eller en förekomst')"), 
            2, new Hash("contents", "noll eller flera", "type", "js", "uri", "addOpt('occ','*','noll eller flera förekomster')"), 
            3, new Hash("contents", "minst en", "type", "js", "uri", "addOpt('occ','+','minst en förekomst')"), 
            4, new Hash("contents", "minst två i följd", "type", "js", "uri", "addOpt('occ','{2,}','minst två i följd')"), 
            5, new Hash("contents", "minst tre i följd", "type", "js", "uri", "addOpt('occ','{3,}','minst tre i följd')"))

	// 5, new Hash(
	//     "contents", "lägg till » ", 
	//     1, new Hash("contents", "lägg till ordform", "type", "js", "uri", "addInteractive('word', 'Lägg till ordform:', '', 'ordet är: ')"), 
	//     2, new Hash("contents", "lägg till negerad ordform", "type", "js", "uri", "addInteractive('word', 'Negerad ordform:', '!', 'ordet är inte: ')"), 
        //     3, new Hash("contents", "lägg till lemma/grundform", "type", "js", "uri", "addInteractive('lemma', 'Lägg till lemma:', '', 'lemma/grundform är: ')"), 
        //     4, new Hash("contents", "lägg till negerat lemma", "type", "js", "uri", "addInteractive('lemma', 'Negerat lemma:', '!', 'lemma/grundform är inte: ')"),
        //     5, new Hash("contents", "lägg till finkornig ordklass (MSD)", "type", "js", "uri", "addInteractive('msd', 'Finkornig ordklass (MSD):', '', 'ordklass (MSD) är: ')"),
        //     6, new Hash("contents", "lägg till negerad finkornig ordklass", "type", "js", "uri", "addInteractive('msd', 'Negerad ordklass (MSD):', '!', 'ordklass (MSD) är inte: ')"))
    ));
}


// ** shortcuts ** //

shortcut('Ctrl+Shift+L',function() {
    addOpt('w','lemma','grundform');
});

shortcut('Ctrl+Shift+E',function() {
    addOpt('w','end','slutet av ordet')
});

shortcut('Ctrl+Shift+S',function() {
    addOpt('w','start','början av ordet')
});

shortcut('Ctrl+Shift+C',function() {
    addOpt('w','case','skilj på stora/små bokstäver.')
});



