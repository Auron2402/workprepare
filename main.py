import os
import smtplib
import subprocess
from argparse import ArgumentParser
import re
from pathlib import Path
from datetime import datetime
import zipfile
import tempfile


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


def check_args_time(timestamp, end_time=False):
    # create text variables
    if end_time:
        start_var = "Endzeit"
    else:
        start_var = "Startzeit"

    # check start time exists
    if timestamp is None:
        timestamp = input(f"{start_var} fehlt: Bitte {start_var} angeben (Format: YYYY-MM-DD HH-MM-SS) oder leer "
                          f"lassen\n")
        if timestamp == "":
            return None

    # check start time is valid
    search = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})", timestamp)

    # convert input to datetime object and check if valid
    if search is None:
        print(f"Angegebene {start_var} ist ungültig -> EXIT")
        exit(5)
    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H-%M-%S")

    return timestamp


def check_args_password(password):
    # check password exists
    if password is None:
        password = input(
            "Passwort fehlt: Bitte Passwort angeben oder leer lassen falls Input-ZIP kein Passwort benötigt\n")
        if password == "":
            return None
    return password


def check_args_mail(mail):
    # check mail exists
    if mail is None:
        mail = input("Mailadresse fehlt: Bitte Mailadresse angeben oder leer lassen falls keine Log-Mail benötigt\n")
        if mail == "":
            return None

    # check mail is valid
    search = re.search(r"([a-zA-Z0-9_.+-]+@lsi\.bayern\.de)", mail)
    if search is None:
        print("Angegebene Mailadresse ist ungültig oder keine LSI Adresse -> EXIT")
        exit(6)

    return mail


def check_arguments(args):
    args.input = check_args_input(args.input)

    # dont ask for args if quiet
    if args.quiet:
        return args

    # ask for optional arguments
    args.output = check_args_output(args.output)
    args.start_time = check_args_time(args.start_time)
    args.end_time = check_args_time(args.end_time, end_time=True)
    args.password = check_args_password(args.password)
    args.mail = check_args_mail(args.mail)
    return args


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


def unzip_files(input_path, password):
    # create temp directory
    temp_dir = tempfile.TemporaryDirectory()
    temp_dir_path = Path(temp_dir.name)

    # unzip files
    with zipfile.ZipFile(input_path, "r") as zip_ref:
        if password is None:
            zip_ref.extractall(temp_dir_path)
        else:
            zip_ref.extractall(temp_dir_path, pwd=password.encode())

    # return path to unzipped files
    return temp_dir


def print_all_files_in_directory(directory):
    for file in os.listdir(directory):
        print(file)


def run_log2timeline(temp_dir):
    # create output directory
    output_dir = tempfile.TemporaryDirectory()
    output_dir_path = Path(output_dir.name)

    # create log2timeline command
    command = ["log2timeline.py", "--parsers", "win7_slow", temp_dir, output_dir_path]

    # run log2timeline
    subprocess.run(command)

    # return path to output directory
    return output_dir


def run_psort(output_dir, output_file, start_time, end_time):
    # create psort command
    command = ["psort.py", "-o", "l2tcsv", "-w", output_file, output_dir]
    if start_time is not None:
        command.extend(f"date < '{start_time}'")
        if end_time is not None:
            command.extend(" AND ")
    if end_time is not None:
        command.extend(f"date > '{end_time}'")

    # run psort
    subprocess.run(command)


def write_mail(mail):
    # setup mail server
    server_adress = "SMTPSERVER"
    port = 25
    sender = "SENDER"
    receiver = mail
    text = "Dies ist eine automatisch generierte Mail"
    # todo: write mail

    smtppObj = smtplib.SMTP(server_adress, port)
    smtppObj.sendmail(sender, receiver, text)
    smtppObj.quit()


def main():
    # parse arguments
    args = parse_arguments()
    args = check_arguments(args)
    # run plaso
    temp_dir = unzip_files(args.input, args.password)
    output_dir = run_log2timeline(Path(temp_dir.name))
    temp_dir.cleanup()
    run_psort(output_dir, args.output, args.start_time, args.end_time)
    output_dir.cleanup()
    # send mail
    #write_mail(args.mail)


    # todo: add logfile createion?


if __name__ == '__main__':
    main()
