"""Enable `py -m portaw ...` (PATH-independent entry; same callable as the
`portaw` console script). Useful on Windows where the Scripts dir may not be on
PATH after a plain install."""

from portaw.main import cli

if __name__ == "__main__":
    cli()
