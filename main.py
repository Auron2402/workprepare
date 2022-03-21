from argparse import ArgumentParser
import re
from pathlib import Path
from datetime import datetime

def parse_arguments():
    parser = ArgumentParser(description="Wrapper Script für psteal von Plaso")
    parser.add_argument("-i", "--input", dest="input",
                        help="Pfad zu input ZIP oder Ordner")
    parser.add_argument("-o", "--output", dest="output",
                        help="pfad und Name der csv Timline")
    parser.add_argument("-s", "--start_time", dest="start_time",
                        help="Zeiptunkt ab dem die Supertimeline beginnen soll (Format: YYYY-MM-DD HH-MM-SS)")
    parser.add_argument("-e", "--end_time", dest="end_time",
                        help="Zeiptunkt ab dem die Supertimeline enden soll (Format: YYYY-MM-DD HH-MM-SS)")
    parser.add_argument("-p", "--password", dest="password",
                        help="Passwort des zip Archivs")
    parser.add_argument("-m", "--mail_addr", dest="mail",
                        help="Mailadresse für Empfangen des Logs / Statusmeldung")
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                        help="Script frägt bei optionalen Argumenten NICHT nach")
    return parser.parse_args()


def check_args_output(output):
    # check output exists
    if output is None:
        output = input("Output fehlt: Pfad und Name der Ziel CSV angeben oder leer lassen für standard Name\n")
        if output == "":
            output = "Supertimeline_" + str(datetime.date(datetime.now())) + ".csv"

    # check if valid output path
    search = re.search(r"(?:.*[/\\])?(.*\.(?:csv|CSV))", output)
    if search is None:
        print("Sicher dass das ein valider CSV outputpfad ist? -> EXIT")
        exit(3)

    path = Path(output)
    if path.is_file():
        print("Angegebene Ouput Datei existiert bereits -> EXIT")
        exit(4)
    return output



def check_arguments(args):
    args.input = check_args_input(args.input)

    # bei quiet nicht nach args fragen
    if args.quiet:
        return args

    args.output = check_args_output(args.output)


def check_args_input(inp):
    # check input exists
    if inp is None:
        inp = input("Input fehlt: Bitte Pfad der Zip oder des Ordners angeben\n")
    # check input is valid
    search = re.search(r".*[/\\](.*\.(?:zip|ZIP))", inp)
    path = Path(inp)
    if search is not None:
        if not path.is_file():
            print("Angegebene Input Datei nicht gefunden -> EXIT")
            exit(1)
    else:
        if not path.is_dir():
            print("Angegebener Input Ordner nicht gefunden -> EXIT")
            exit(2)
    return inp


def main():
    args = parse_arguments()
    check_arguments(args)
    # todo: add logfile createion?


if __name__ == '__main__':
    main()
