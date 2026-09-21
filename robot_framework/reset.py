"""This module handles resetting the state of the computer so the robot can work with a clean slate.

For this robot the "state" is only the cached KontAKT credentials. Der aabnes
BEVIDST ingen F2-forbindelse: robotten rører ikke F2. Arkiveringen fjerner
arbejdskopien i KontAKT og pakkerne i DMZ'en - journalen i F2 er netop det, der
bliver tilbage, og det ville være forkert at have en levende F2-session åben i
en proces, hvis eneste opgave er at slette filer.
"""

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection


class Client:
    """Cached KontAKT credentials."""

    def __init__(self, orchestrator_connection: OrchestratorConnection):
        kontakt = orchestrator_connection.get_credential("KontAKTAPI")
        self.kontakt_base = (kontakt.username or "").rstrip("/")
        self.kontakt_key = kontakt.password


def reset(orchestrator_connection: OrchestratorConnection) -> Client:
    """Clean up, close/kill all programs, then (re)open the connections."""
    orchestrator_connection.log_trace("Resetting.")
    clean_up(orchestrator_connection)
    close_all(orchestrator_connection)
    kill_all(orchestrator_connection)
    return open_all(orchestrator_connection)


def clean_up(orchestrator_connection: OrchestratorConnection) -> None:
    """Do any cleanup needed to leave a blank slate."""
    orchestrator_connection.log_trace("Doing cleanup.")


def close_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Gracefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Closing all applications.")


def kill_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Forcefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Killing all applications.")


def open_all(orchestrator_connection: OrchestratorConnection) -> Client:
    """Open all connections used by the robot and return them as a :class:`Client`."""
    orchestrator_connection.log_trace("Reading KontAKT credentials.")
    return Client(orchestrator_connection)
