# Config
För varje Sparv-funktion anges config-variabler och eventuella default-värden.

En annoterares åtkomst till config-värden sker alltid via funktionens argument (signaturen). Ingen läsning av configen sker i själva funktions-bodyn.

För att kunna referera till en config-variabel måste den vara deklarerad någonstans. Detta görs i decoratorn. Obs: det räcker med att variabeln är deklarerad i någon decorator (måste inte ske i den decoratorn som tillhör funktionen där man använder variabeln.)

Prioritering: corpus-config > default-config > modul-default
