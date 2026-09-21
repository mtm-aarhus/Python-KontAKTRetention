"""KontAKT: advar om opbevaringsfristen, og arkivér sagen når den er nået.

Kører én gang i døgnet.

HVAD "ARKIVÉR" BETYDER HER
    Filerne slettes - både på ADM og i DMZ'en - og sagen låses. Alt andet bliver
    stående: dokumentlisten, hver afgørelse med begrundelse, mailtråden og hele
    revisionssporet. Man kan bagefter se HVAD der blev udleveret og HVORFOR; man
    kan bare ikke åbne filerne.

    Sagen SLETTES altså ikke. Det kan en administrator gøre i hånden, men det er
    ikke det, opbevaringsreglen gør.

    Det kan ikke fortrydes. Derfor advares sagsbehandleren 30 dage før, med
    datoen, og med den ene ting der stopper det: genåbn sagen.

ROBOTTEN BESLUTTER INGENTING
    Den spørger KontAKT om planen og beder derefter om én sag ad gangen. Fristen
    tjekkes igen inde i KontAKT ved hvert enkelt kald - planen er et
    øjebliksbillede, og der kan gå tid, eller nogen kan nå at genåbne en sag,
    mellem at listen blev hentet og sagen blev nået.

    Den grænse er med vilje: reglen om hvornår noget slettes hører hjemme ét
    sted, sammen med dataene, og ikke i en robot der kan køre med en gammel
    udgave af sig selv.

SAGER, HVOR F2 MANGLER NOGET, RØRES IKKE
    F2 er arkivet; KontAKT er arbejdskopien. Sletter vi noget her, som aldrig
    kom over i F2, er det ikke oprydning men tab.

    Journalisering sker løbende, så længe sagen er åben, så spørgsmålet er ikke
    "er sagen journaliseret?" men "mangler F2 noget lige nu?". KontAKT regner
    det ud på selve dagen - udleverede dokumenter uden en F2-kopi, dokumenter
    ændret siden de kom over, mails uden akt, sager med en noteret
    synkroniseringsfejl. Er bare én af dem tilbage, svarer KontAKT 409, og
    sagen står i ``blocked`` med en begrundelse, der kan handles på.

OO config:
    Credential KontAKTAPI      username = base URL, password = X-API-Key
"""
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

import requests

from robot_framework import reset

# En daglig koersel, der pludselig vil arkivere hundredvis af sager, er ikke en
# travl dag - det er en fejl et andet sted (en forkert dato, en tom kolonne). Saa
# stopper robotten og beder om et menneske, frem for at slette filer i tusindvis.
MAX_ARKIVERINGER = 50


def process(
    orchestrator_connection: OrchestratorConnection,
    queue_element=None,          # ubrugt: robotten er lineaer
    client: "reset.Client | None" = None,
) -> None:
    orchestrator_connection.log_trace("Running process.")
    if client is None:
        client = reset.open_all(orchestrator_connection)

    plan = _hent(client, "/api/v1/retention/plan")
    advar = plan.get("warn") or []
    arkiver = plan.get("archive") or []
    spaerret = plan.get("blocked") or []
    orchestrator_connection.log_info(
        f"Opbevaring: {len(advar)} skal advares, {len(arkiver)} skal arkiveres, "
        f"{len(spaerret)} er spærret (ikke journaliseret).")

    if len(arkiver) > MAX_ARKIVERINGER:
        raise RuntimeError(
            f"{len(arkiver)} sager er modne til arkivering på én dag - grænsen "
            f"er {MAX_ARKIVERINGER}. Det ligner en fejl i fristerne og ikke en "
            f"travl dag, så der slettes ingenting. Se KontAKTs retention/plan.")

    for sag in spaerret:
        # HVAD der mangler, og ikke bare at noget gør. En linje, der siger
        # "spærret", er en linje, ingen kan handle på.
        hvad = "; ".join(sag.get("missing") or ["ukendt"])
        orchestrator_connection.log_info(
            f"Sag {sag['case_id']}: fristen er nået ({sag.get('due_at')}), men "
            f"F2 mangler noget: {hvad}. Arkiveres ikke. Kræver et menneske.")

    advaret = _advar_alle(orchestrator_connection, client, advar)
    arkiveret = _arkiver_alle(orchestrator_connection, client, arkiver)

    orchestrator_connection.log_info(
        f"Færdig. {advaret} advaret, {arkiveret} arkiveret, {len(spaerret)} spærret.")


def _advar_alle(oc, client, sager) -> int:
    """Advar om hver sag for sig.

    En sag, der fejler, stopper ikke de andre: den værste udgang her er ikke en
    manglende advarsel, men en RÆKKE manglende advarsler, fordi den første
    fejlede. Robotten prøver igen i morgen - KontAKT sætter kun
    ``retention_warned_at``, når en mail faktisk kom af sted.
    """
    antal = 0
    for sag in sager:
        cid = sag["case_id"]
        try:
            svar = _send(client, f"/api/v1/cases/{cid}/retention/warn")
            if svar.get("ok"):
                antal += 1
                oc.log_info(f"Sag {cid}: advaret om sletning den "
                            f"{(sag.get('due_at') or '')[:10]} "
                            f"({len(svar.get('recipients') or [])} modtagere).")
            else:
                oc.log_info(f"Sag {cid}: ingen kunne advares. Prøves igen i morgen.")
        except Exception as exc:                    # pylint: disable=broad-except
            oc.log_info(f"Sag {cid}: advarsel fejlede: {exc!r}")
    return antal


def _arkiver_alle(oc, client, sager) -> int:
    antal = 0
    for sag in sager:
        cid = sag["case_id"]
        try:
            svar = _send(client, f"/api/v1/cases/{cid}/retention/archive")
            if svar.get("already"):
                oc.log_info(f"Sag {cid}: var allerede arkiveret.")
                continue
            antal += 1
            oc.log_info(
                f"Sag {cid}: arkiveret. {svar.get('documents', 0)} dokumenter og "
                f"{svar.get('attachments', 0)} vedhæftninger slettet, "
                f"{svar.get('delivery_links', 0)} udleveringer taget ned.")
        except Exception as exc:                    # pylint: disable=broad-except
            oc.log_info(f"Sag {cid}: arkivering fejlede: {exc!r}")
    return antal


def _hent(client, sti: str) -> dict:
    r = requests.get(f"{client.kontakt_base}{sti}",
                     headers={"X-API-Key": client.kontakt_key}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"KontAKT svarede HTTP {r.status_code} på {sti}: "
                           f"{r.text[:300]!r}")
    return r.json()


def _send(client, sti: str) -> dict:
    r = requests.post(f"{client.kontakt_base}{sti}",
                      headers={"X-API-Key": client.kontakt_key,
                               "Content-Type": "application/json"},
                      json={}, timeout=300)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"KontAKT svarede HTTP {r.status_code} på {sti}: "
                           f"{r.text[:300]!r}")
    return r.json()
