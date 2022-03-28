import os
import smtplib
import subprocess
from argparse import ArgumentParser
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from pathlib import Path
from datetime import datetime
import zipfile
import tempfile
import logging
from time import sleep


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
    logging.info(f"Output: {output}")

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
    logging.info(f"{start_var}: {timestamp}")

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
            logging.info("Kein Passwort angegeben")
            return None
    logging.info(f"Passwort: Ich log das Passwort lieber nicht")
    return password


def check_args_mail(mail):
    # check mail exists
    if mail is None:
        mail = input("Mailadresse fehlt: Bitte Mailadresse angeben oder leer lassen falls keine Log-Mail benötigt\n")
        if mail == "":
            return None
    logging.info(f"Mailadresse: {mail}")

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
    logging.info(f"Input: {inp}")

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
    logging.info(f"Temp ZIP Directory: {temp_dir_path}")

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
    logging.info(f"log2timeline command: {command}")

    # run log2timeline
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True, )
    logging.info(f"log2timeline started at {datetime.now()} with PID {process.pid}")

    # wait for log2timeline to finish
    while True:
        sleep(10)
        return_code = process.poll()
        if return_code is not None:
            if return_code == 0:
                logging.info("log2timeline finished successfully at " + str(datetime.now()))
            else:
                logging.error("log2timeline finished unsuccessfully at " + str(datetime.now()))
                logging.error(process.stderr.read())
            break

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
    logging.info(f"psort command: {command}")

    # run psort
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    logging.info("psort started at " + str(datetime.now()) + " with PID " + str(process.pid))

    # wait for psort to finish
    while True:
        sleep(10)
        return_code = process.poll()
        if return_code is not None:
            if return_code == 0:
                logging.info("psort finished successfully at " + str(datetime.now()))
            else:
                logging.error("psort finished unsuccessfully at " + str(datetime.now()))
                logging.error(process.stderr.read())
            break


def send_mail(send_to, files=None):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = "SENDER"
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = "PLASO STATUS REPORT"

    msg.attach(MIMEText("Plaso Erfolgreich abgeschlossen. Logfile befindet sich im Anhang."))

    for path in files:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename={}'.format(Path(path).name))
        msg.attach(part)

    smtp = smtplib.SMTP("SMTPSERVEREINFÜGEN", 25) # todo: SMTP-Server einfügen
    smtp.sendmail("send_from", send_to, msg.as_string()) # todo: send_from einfügen
    smtp.quit()


def main():
    # start logging
    logging.basicConfig(filename="log.log", level=logging.INFO)
    logging.info("Start: " + str(datetime.now()))

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
    # write_mail(args.mail)


if __name__ == '__main__':
    main()
