# Python-KontAKTRetention

Advarer om opbevaringsfristen og **arkiverer** aktindsigter, når den er nået.

Lineær robot. Kører én gang i døgnet.

## Hvad "arkivér" betyder

Dokumentfilerne slettes - både på ADM og i DMZ'en - og sagen låses, så den kun
kan læses.

Alt andet bliver stående: sagen selv, dokumentlisten, hver afgørelse med sin
begrundelse, mailtråden og hele revisionssporet. Bagefter kan man stadig se
**hvad** der blev udleveret og **hvorfor** - man kan bare ikke åbne filerne.

Sagen bliver altså ikke slettet. Det kan en administrator gøre i hånden
(`cases.delete_case`), men det er ikke det, opbevaringsreglen gør.

**Arkivering kan ikke fortrydes.** Bytesene findes ikke mere.

## Fristen

    max(delingslinket sendt, seneste korrespondance) + 100 dage

"Seneste korrespondance" er den nyeste mail på sagen - ikke `last_activity_at`.
De to ligner hinanden, og forskellen er hele pointen: `last_activity_at` rykkes
af enhver handling, også at nogen retter en stavefejl i titlen. Hang sletningen
på den, ville et tilfældigt klik i en gammel sag købe 100 dage mere, uden at
nogen havde ment det.

Der advares **30 dage før**. Advarslen siger datoen og den ene ting, der stopper
det: genåbn sagen.

Reglen selv står i `app/retention.py` i KontAKT - ikke her. Robotten spørger om
planen og beder om én sag ad gangen; KontAKT tjekker fristen igen ved hvert
kald, fordi planen er et øjebliksbillede, og nogen kan nå at genåbne en sag
imens.

## Sager, hvor F2 mangler noget, røres ikke

F2 er arkivet; KontAKT er arbejdskopien. Sletter vi noget her, som aldrig kom
over i F2, er det ikke oprydning men tab.

Journalisering sker **løbende**, så længe sagen er åben. Spørgsmålet er derfor
ikke *"er sagen journaliseret?"* men **"mangler F2 noget lige nu?"** - og det
regner KontAKT ud på selve dagen, ud af den plan journaliseringen selv kører på:

| Spærrer arkiveringen |
|---|
| et udleveret dokument uden en kopi i F2 |
| et dokument ændret, siden det kom i F2 |
| en modtaget eller afsendt mail uden akt |
| en sag med en noteret synkroniseringsfejl |
| sagen har intet F2-sagsnummer |
| F2-planen kunne ikke beregnes (tvivl tæller som mangler) |

Er bare én af dem tilbage, svarer KontAKT 409, og sagen står i `blocked` med en
begrundelse, robotten skriver i loggen.

Når en sagsbehandler **afslutter** en sag, sætter KontAKT en sidste
journalisering i kø. Det er sidste chance for at få alt over, og det er dét, der
gør, at listen over spærrede sager normalt er tom.

`journalized_at` alene åbner altså ikke for arkivering. Den siger kun, hvornår
F2 sidst blev bekræftet i sync.

## Spærren

Vil en kørsel arkivere mere end **50** sager, stopper robotten uden at slette
noget. Så mange på én dag ligner en fejl i fristerne - en forkert dato, en tom
kolonne - og ikke en travl dag.

## OO config

| Type | Navn | Værdi |
|---|---|---|
| Credential | `KontAKTAPI` | username = KontAKTs base-URL, password = `X-API-Key` |
| Constant | `Error Email` | hvor fejlskærmbilleder sendes hen |

Der er **ingen F2-opsætning**, og det er med vilje: robotten rører ikke F2.
Derfor står `oomtm` heller ikke i `pyproject.toml`.

## Kald robotten bruger

    GET  /api/v1/retention/plan                     hvad skal advares/arkiveres
    POST /api/v1/cases/<id>/retention/warn          send advarslen
    POST /api/v1/cases/<id>/retention/archive       slet filerne, lås sagen
