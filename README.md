# IBM mmvdisk manager

This script helps manage disks in a virtual disk environment (mmvdisk), identifying disks
that need replacement and providing options to prepare or replace them.

## Overview

This script helps IBM storage administrators identify and manage virtual disks that need attention or replacement in IBM Spectrum Scale environments. IBM's mmvdisk utility provides storage virtualization capabilities that require monitoring and maintenance, which this tool helps automate.

## Features

- **Disk Health Checks**: Identify disks that are not in "OK" state within IBM recovery groups
- **Replacement Management**: Identify and prepare IBM pdisks that need replacement
- **Multiple Modes**:
  - `--prepare`: Prepare disks for replacement
  - `--replace`: Execute full disk replacement
  - `--dryrun`: Preview commands without executing them
  - `--email`: Send email notifications about problematic disks
- **Detailed Reporting**: Formatted tables showing disk health status
- **Comprehensive Logging**: Track all operations and results

## Requirements

- Python 3.6+
- IBM Spectrum Scale environment with mmvdisk
- Access to IBM mmvdisk command line tools
- Access to email SMTP if using alert feature
- Required Python packages:
  - pandas
  - docopt
  - prettytable

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ibm-mmvdisk-manager.git
cd ibm-mmvdisk-manager

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Show help
python disk_manager.py --help

# Check and prepare disks for replacement
python disk_manager.py --prepare

# Show condensed output
python disk_manager.py --prepare --short

# Execute disk replacement
python disk_manager.py --replace

# Simulate commands without executing (dry run)
python disk_manager.py --dryrun

# Send email notifications
python disk_manager.py --email -e your.email@example.com
```

## Output Example

The script provides detailed tables of IBM Spectrum Scale disk status information:

```
+------+---------------+-------+----------+----------+---------------+--------+
| Name | RecoveryGroup | state | location | hardware | User location | Server |
+------+---------------+-------+----------+----------+---------------+--------+
| pd1  | rg1           | not_ok| slot_3   | ssd_nvme | rack_a1       | srv01  |
| pd7  | rg2           | failed| slot_12  | ssd_sata | rack_b3       | srv02  |
+------+---------------+-------+----------+----------+---------------+--------+
```

## Configuration

Modify the constants in the script to match your IBM environment:

- `EMAIL_CONFIG`: Update with your email server details
- `FILE_PATHS`: Customize log and output file locations
- `COMMAND_CONFIG`: Adjust IBM mmvdisk command parameters if needed

## Logging

The script maintains detailed logs of all operations, including:
- Commands executed
- Operation results
- Error messages
- Time and date information

