"""
Disk Management Utility Script

This script helps manage disks in a virtual disk environment (mmvdisk), identifying disks
that need replacement and providing options to prepare or replace them.

Version: Beta 1
Revision: 1.0
"""

import json
import logging
import smtplib
import subprocess
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import SysLogHandler

import pandas as pd
from docopt import docopt
from prettytable import PrettyTable

# Constants
__version__ = 'Beta 1'
__revision__ = '1.0'
__deprecated__ = False

# Command configurations
COMMAND_CONFIG = {
    'all_not_ok': ['mmvdisk', 'pdisk', 'list', '--rg', 'all', '--not-ok'],
    'replace': ['mmvdisk', 'pdisk', 'list', '--rg', 'all', '--replace'],
}

# Email configuration
EMAIL_CONFIG = {
    'sender_email': "your email address",
    'sender_password': "your password",
    'smtp_server': "smtp.gmail.com",
    'smtp_port': 587
}

# File paths
FILE_PATHS = {
    'not_ok_pdisk': 'not_ok_pdisk.txt',
    'replace_pdisk': 'replace_pdisk.txt',
    'output': 'disk_health_result.txt',
    'log': 'logs.log'
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename=FILE_PATHS['log'], 
    filemode='a', 
    format='%(message)s  %(asctime)s', 
    datefmt="%Y-%m-%d %T"
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
logger.addHandler(SysLogHandler())

# Global storage
list_pdisk = []
commands = []


def get_args():
    """
    Function to get command line arguments.
    
    Defines arguments needed to run this program.
    
    Returns:
        dict: Dictionary with parsed arguments
    """
    usage = """
    Usage:
        try.py --replace [--short]
        try.py --prepare [--short]
        try.py --email -e <EMAIL> 
        try.py --version
        try.py -h | --help

    Options:
        -h --help            Show this message and exit
    """

    args = docopt(usage)
    return args


def get_failed_pdisk(filename, command):
    """
    Get the list of pdisk and recovery group from the output file.
    
    Args:
        filename (str): Path to the file containing command output
        command (str): The command that was executed
        
    Returns:
        pandas.DataFrame: DataFrame containing recovery group and pdisk info
        
    Exits:
        If all disks are OK or no pdisks are marked for replacement
    """
    with open(filename, 'r') as file:
        contents = file.read()

        # Check if all disks are OK
        if 'All pdisks are ok.' in contents:
            print(f"Command: {command} ---> All disk are OK!")
            logging.info(f"Command: {command} ---> Output: All disk are OK!")
            exit(0)

        # Check if no disks are marked for replacement
        elif 'No pdisks are marked for replacement.' in contents:
            print(f"Command: {command} ---> No pdisk are marked for replacement!")
            logging.info(f"Command: {command} ---> Output: No pdisk are marked for replacement!")
            exit(0)

        # Clean up the contents for better parsing
        if 'declustered' in contents:
            contents = contents.replace('declustered', '')

        if 'mmvdisk: A lower priority value means a higher need for replacement.' in contents:
            contents = contents.replace('mmvdisk: A lower priority value means a higher need for replacement.', '')

    # Write the cleaned contents back to the file
    with open(filename, 'w') as file:
        file.write(contents)

    # Parse the file with pandas
    df = pd.read_csv(filename, sep='\s{2,}', engine='python')
    return df[["recovery group", "pdisk"]]


def command(command, filename, table):
    """
    Execute a command and save its output to a file.
    
    Args:
        command (list): Command to execute as a list of strings
        filename (str): File to save the output to
        table (str): Description of what the command does for the table
        
    Returns:
        tuple: (filename, command_string)
    """
    command_str = ' '.join([str(elem) for elem in command])

    # Create a pretty table for display
    t = PrettyTable()
    t.field_names = ["Command: ", command_str]
    t.add_row([' ', table])
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, error = process.communicate()

        if error:
            print(f"Command: {command_str} ---> Error: {error.decode('utf-8')}")
            exit(1)
            
        print(t)
        print(output.decode('utf-8'))
        
        with open(filename, 'w') as f:
            f.write(output.decode('utf-8'))
        
        return filename, command_str
    
    except subprocess.CalledProcessError:
        return "Error running command."
    except FileNotFoundError:
        return "Command not found."


def show_data(filename, short=False):
    """
    Display data from a JSON file in a pretty table.
    
    Args:
        filename (str): JSON file to read
        short (bool): Whether to show a shorter version of the table
    """
    with open(filename, "r") as f:
        json_data = f.read()

    data = json.loads(json_data)
    table = PrettyTable()
    
    if short:
        table.field_names = ["Name", "RecoveryGroup", "state", "location", "Server"]
        for item in data:
            table.add_row([
                item["name"],
                item["recoveryGroup"],
                item["state"],
                item["location"],
                item["server"]
            ])
    else:
        table.field_names = ["Name", "RecoveryGroup", "state", "location", "hardware", "User location", "Server"]
        for item in data:
            table.add_row([
                item["name"],
                item["recoveryGroup"],
                item["state"],
                item["location"],
                item["hardware"],
                item["userLocation"],
                item["server"]
            ])

    print(table)


def text_to_dict(text):
    """
    Convert key=value text output to a dictionary.
    
    Args:
        text (str): Text with key=value pairs
        
    Returns:
        dict: Parsed dictionary
    """
    result_dict = {}
    
    if 'pdisk:' in text:
        text = text.replace('pdisk:', '')
        
    for line in text.split("\n"):
        if not line.strip():  # Skip empty lines
            continue
            
        if '=' not in line:
            continue
            
        key, value = line.split("=", 1)
        value = value.strip().strip("")
        key = key.strip()
        
        # Try to convert to int if possible
        try:
            value = int(value)
        except ValueError:
            pass
            
        result_dict[key] = value
        
    # Clean up string values
    for key, value in result_dict.items():
        if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            result_dict[key] = value[1:-1]
            
    return result_dict


def create_file(filename, data, short_format=False):
    """
    Create a JSON file with the provided data and display it.
    
    Args:
        filename (str): File path to write JSON data
        data (list): List of dictionaries to save as JSON
        short_format (bool): Whether to display in short format
    """
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
        
    show_data(filename, short_format)

    
def get_pdisk_info(pdisk, group):
    """
    Get information about a specific pdisk within a recovery group.
    
    Args:
        pdisk (str): The pdisk identifier
        group (str): The recovery group name
    """
    cmd = ['mmvdisk', 'pdisk', 'list', '--rg', group, '--pdisk', pdisk, '-L']
    output_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, _ = output_proc.communicate()
    
    pdisk_info = text_to_dict(output.decode('utf-8'))
    list_pdisk.append(pdisk_info)

    
def replace_pdisk(args, pdisk, group, need_replace):
    """
    Handle pdisk replacement based on provided arguments.
    
    Args:
        args (dict): Command line arguments
        pdisk (str): The pdisk identifier
        group (str): The recovery group name
        need_replace (list): List of disks that need replacement
    """
    # Construct the command
    command_parts = ['mmvdisk', 'pdisk', 'replace', '--prepare', '--rg', group, '--pdisk', pdisk]
    command_str = ' '.join([str(elem) for elem in command_parts])
    commands.append(command_str)


    if args['--email']:
        # Send email with disk replacement information
        send_emails(args['<EMAIL>'], need_replace)

    elif args['--prepare']:
        # Prepare disks for replacement
        output_proc = subprocess.Popen(
            ['mmvdisk', 'pdisk', 'replace', '--prepare', '--rg', group, '--pdisk', pdisk], 
            stdout=subprocess.PIPE
        )
        output, _ = output_proc.communicate()
        output_text = output.decode('utf-8')
        
        # Check if preparation was successful
        if 'Reinsert carrier.' in output_text:
            success_msg = f"Successfully prepared pdisk for replace!\n Command: {command_str} --> OUTPUT: {output_text}"
            print(success_msg)
            logging.info(success_msg)
        else:
            error_msg = f"Command: {command_str} --> OUTPUT: {output_text}"
            print(error_msg)
            logging.info(f"Failed preparing pdisk for replace!\n {error_msg}")

    else:
        # Actually replace the pdisk
        output_proc = subprocess.Popen(
            ['mmvdisk', 'pdisk', 'replace', '--recovery-group', group, '--pdisk', pdisk], 
            stdout=subprocess.PIPE
        )
        output, _ = output_proc.communicate()
        output_text = output.decode('utf-8')

        if 'not physically replaced with a new disk.' in output_text:
            error_msg = f"Command: {command_str} --> Error: {output_text}"
            print(error_msg)
            logging.info(f"Failed replacing pdisk! {error_msg}")
        else:
            success_msg = f"Replacing pdisk! Command: {command_str} --> OUTPUT: {output_text}"
            print(success_msg)
            logging.info(success_msg)


def send_email(sender_email, sender_password, receiver_email, subject, message):
    """
    Send an email.
    
    Args:
        sender_email (str): Email address of sender
        sender_password (str): Password for sender's email
        receiver_email (str): Email address of recipient
        subject (str): Email subject
        message (str): Email body
    """
    # Create a multipart message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # Add the message body
    msg.attach(MIMEText(message, "plain"))

    # Create SMTP session for sending the mail
    with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as smtp:
        smtp.starttls()
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)


def send_emails(receiver_email, need_replace_disk):
    """
    Send email notification about disks that need replacement.
    
    Args:
        receiver_email (str): Email address to send notification to
        need_replace_disk (list): List of disks that need replacement
    """
    name = "Trial1"
    subject = "Disk with issue"
    message = f"DISKS NEEDS REPLACEMENT! {need_replace_disk} "

    send_email(
        EMAIL_CONFIG['sender_email'], 
        EMAIL_CONFIG['sender_password'], 
        receiver_email, 
        subject, 
        message
    )
    print(f"Email sent to {name} ({receiver_email})")

    

def display_state(dataframe, title):
    """
    Display pdisk information in a table and return as JSON data.
    
    Args:
        dataframe (pandas.DataFrame): DataFrame with pdisk information
        title (str): Title to display above the table
        
    Returns:
        list: JSON data of disk information
    """
    list_disk = []
    
    # Loop through the DataFrame
    for index, row in dataframe.iterrows():
        if '--------' not in row['recovery group'] and '--------' not in row['pdisk']:
            cmd = ['mmvdisk', 'pdisk', 'list', '--rg', row['recovery group'], '--pdisk', row['pdisk'], '-L']
            output_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            output, _ = output_proc.communicate()
            
            # Parse the output into a dictionary
            disk_info = text_to_dict(output.decode('utf-8'))
            list_disk.append(disk_info)

    # Convert to JSON for display
    data_json = json.dumps(list_disk)
    data = json.loads(data_json)
    
    # Create and display the table
    table = PrettyTable()
    table.field_names = ["Name", "RecoveryGroup", "state", "location", "hardware", "User location", "Server"]

    for item in data:
        table.add_row([
            item["name"],
            item["recoveryGroup"],
            item["state"],
            item["location"],
            item["hardware"],
            item["userLocation"],
            item["server"]
        ])
        
    print(f"{title}")
    print(table)

    return data


def main(args):
    """
    Main function to execute the disk management script.
    
    Args:
        args (dict): Command line arguments
    """
    # Record start time and date
    start_time = time.time()
    date_stamp = datetime.utcnow().strftime('%Y-%m-%d,%H:%M UTC')
    
    # Get list of disks not OK
    not_ok_file, command_str = command(
        COMMAND_CONFIG['all_not_ok'], 
        FILE_PATHS['not_ok_pdisk'], 
        'Disk not ok'
    )
    
    # Get list of disks marked for replacement
    replace_file, command_str = command(
        COMMAND_CONFIG['replace'], 
        FILE_PATHS['replace_pdisk'], 
        'List of replace disks'
    )

    # Process and display disks with issues
    not_ok_df = get_failed_pdisk(not_ok_file, command_str)
    disk_not_ok = display_state(not_ok_df, 'List of Disks that are not ok')
    
    # Process and display disks that need replacement
    replace_df = get_failed_pdisk(replace_file, command_str)
    need_replace = display_state(replace_df, 'List of disks needs replace')

    print('\n\n')
    print("DISKS NEEDS REPLACEMENT!")
    print(need_replace)
    print('\n\n')
    
    # Build and log the command
    replace_cmd = ' '.join([str(elem) for elem in COMMAND_CONFIG['replace']])
    commands.append(replace_cmd)
    cmd_info = f"List of pdisk needs to be replaced:\n Command: {commands}\n{replace_df}\n\t\t"
    print(cmd_info)
    logging.info(cmd_info)

    # Process each disk that needs replacement
    for index, row in replace_df.iterrows():
        if '--------' not in row['recovery group'] and '--------' not in row['pdisk']:
            pdisk = row['pdisk']
            group = row['recovery group']
            replace_pdisk(args, pdisk, group, need_replace)
            get_pdisk_info(pdisk, group)

    # Create output file with collected disk information
    create_file(
        FILE_PATHS['output'], 
        list_pdisk, 
        args['--short']
    )

    # Calculate and display elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f'The program took {int(hours)}:{int(minutes):02}:{seconds:02.0f} to run.')
    print(f'Date and time program was initiated {date_stamp}')


if __name__ == '__main__':
    ARGS = get_args()
    main(ARGS)