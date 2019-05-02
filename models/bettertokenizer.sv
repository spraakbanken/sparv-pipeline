# Configuration file for BetterTokenizer (segment.py)

# Set whether the tokenizer should be case sensitive or not (true/false)
case_sensitive:	false

# Relative or absolute path to an optional file with a list of tokens, one per row, for tokens not handled by the rules below
token_list:	./bettertokenizer.sv.saldo-tokens

# Characters that cannot start word tokens (no regex escaping needed)
start:	({[]})"“”'‘’`»;:–—\/&#*@-,…|_¨

# Characters that cannot appear within words (no regex escaping needed)
within:	({[]})"“”'‘’»;–—\/*%…?!,|_¨

# Characters that cannot end word tokens (in addition to the characters defined above) (no regex escaping needed)
end:	`:&#@,.|_¨

# Multi-character punctuation (Python regular expression)
multi:	(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)

# Decimal numbers (Python regular expression)
number:	\d+,\d+

# Miscellaneous Python regular expressions matching tokens (names should begin with 'misc_')
misc_url:		(?:http|ftp|https):\/\/[\w\-_]+(?:\.[\w\-_]+)+(?:[\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?
misc_email:		(?:[a-zA-Z0-9_\-\.]+)@(?:(?:\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(?:(?:[a-zA-Z0-9\-]+\.)+))(?:[a-zA-Z]{2,4}|[0-9]{1,3})(?:\]?)(?!\w)
misc_smiley:	(?:(?:(?<=\s)|(?<=\A))(?:(?:(?:>[:;=+])|[>:;=+])[,*]?[-~+o]?(?:\)+|\(+|\}+|\{+|\]+|\[+|\|+|\\+|/+|>+|<+|D+|[@#!OoPpXxZS$03])|>?[xX8][-~+o]?(?:\)+|\(+|\}+|\{+|\]+|\[+|\|+|\\+|/+|>+|<+|D+))(?=\s|\Z))

# Abbreviations, one per line, without final period (nothing but abbreviations should be added beyond this point)
abbreviations:
	a.a
	a.d
	agr
	a.k.a
	alt
	ang
	anm
	art
	avd
	avl
	b.b
	betr
	b.g
	b.h
	bif
	bl.a
	b.r.b
	b.t.w
	civ.ek
	civ.ing
	co
	dir
	div
	d.m
	doc
	dr
	d.s
	d.s.o
	d.v
	d.v.s
	d.y
	dåv
	d.ä
	e.a.g
	e.d
	eftr
	eg
	ekon
	e.kr
	dyl
	e.d
	em
	e.m
	enl
	e.o
	etc
	e.u
	ev
	ex
	exkl
	f
	farm
	f.d
	ff
	fig
	f.k
	f.kr
	f.m
	f.n
	forts
	fr
	fr.a
	fr.o.m
	f.v.b
	f.v.t
	f.ö
	följ
	föreg
	förf
	gr
	g.s
	h.h.k.k.h.h
	h.k.h
	h.m
	ill
	inkl
	i.o.m
	st.f
	jur
	kand
	kap
	kl
	lb
	leg
	lic
	lisp
	m.a.a
	mag
	m.a.o
	m.a.p
	m.fl
	m.h.a
	m.h.t
	milj
	m.m
	m.m.d
	mom
	m.v.h
	möjl
	n.b
	näml
	nästk
	o
	o.d
	odont
	o.dyl
	omkr
	o.m.s
	op
	ordf
	o.s.a
	o.s.v
	pers
	p.gr
	p.g.a
	pol
	prel
	prof
	rc
	ref
	resp
	r.i.p
	rst
	s.a.s
	sek
	sekr
	sid
	sign
	sistl
	s.k
	sk
	skålp
	s.m
	s.m.s
	sp
	spec
	s.st
	st
	stud
	särsk
	tab
	tekn
	tel
	teol
	t.ex
	tf
	t.h
	tim
	t.o.m
	tr
	trol
	t.v
	u.p.a
	urspr
	utg
	v
	w
	v.d
	å.k
	ä.k.s
	äv
	ö.g
	ö.h
	ök
	övers
