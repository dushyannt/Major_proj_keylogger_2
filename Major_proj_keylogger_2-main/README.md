# Advanced System Monitoring Tool

A comprehensive system monitoring solution that combines keylogging, system information collection, clipboard monitoring, browser history tracking, and automated reporting capabilities.

## Features

### 1. Keylogging
- Real-time keyboard input monitoring
- Special key detection
- Timestamp-based logging
- Formatted output

### 2. System Information Collection
- Hardware specifications
- IP address
- Processor details
- System information
- Host name
- Excel format storage

### 3. Clipboard Monitoring
- Real-time clipboard content tracking
- Timestamp-based logging
- Formatted output

### 4. Browser History Tracking
- Chrome browser history collection
- URL and title tracking
- Visit timestamps
- Excel format storage

### 5. Screenshot Capability
- Screen capture functionality
- PNG format storage
- Timestamp-based naming

### 6. Automated Reporting
- Email-based reporting system
- Scheduled data transmission
- Multiple file attachments
- Secure SMTP connection

## Technical Implementation

### Core Components
- Python-based implementation
- Class-based architecture
- Multi-threaded operation
- Error handling and logging
- Resource management

### File Structure
- `system_track.pyw` - Main program file
- `start.vbs` - Silent launcher
- `start.bat` - Batch launcher
- `requirements.txt` - Dependencies

### Generated Files
- `keystrokes.txt` - Keyboard input logs
- `error_logs.txt` - Error tracking
- `clipboard.txt` - Clipboard content
- `system_info.xlsx` - System information
- `chrome_history.xlsx` - Browser history
- `screenshot.png` - Screen captures

## Installation

1. Ensure Python 3.x is installed
2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Silent Operation
1. Double-click `start.vbs`
- Runs program silently
- No console window
- Background operation

### Batch Operation
1. Double-click `start.bat`
- Runs program in background
- No command prompt
- Easy execution

## Configuration

### Email Settings
Update the following in `system_track.pyw`:
```python
self.sender_email = "your_email@example.com"
self.sender_password = "your_password"
self.receiver_email = "receiver@example.com"
```

### Monitoring Interval
Adjust the monitoring interval in `system_track.pyw`:
```python
time.sleep(3600)  # Default: 1 hour
```

## Technical Details

### Dependencies
- pynput
- pandas
- pillow
- win32clipboard
- sqlite3
- smtplib

### Error Handling
- Comprehensive error logging
- Automatic error recovery
- Detailed error messages
- Separate error log file

### Security Features
- Secure email transmission
- File cleanup after sending
- Error logging
- Resource management

## Development

### Code Structure
- Object-oriented design
- Modular implementation
- Clean code practices
- Comprehensive documentation

### Best Practices
- Error handling
- Resource management
- Code organization
- Documentation

## Notes
- Program runs silently in background
- Automatic file cleanup after email sending
- Configurable monitoring intervals
- Secure data transmission

## Disclaimer
This tool is for educational purposes only. Always ensure proper authorization before monitoring any system.

# Spyware

Hey you all this is Ashutosh Behera. I have developed this advanced spyware tool to demonstrate the working of the spyware and how it tries to steal user's data.

DISCLAMIER

This python program is for educational purpose only. Don't use it for any malicious purpose. The authoe of this program will not be responsible for any kind of malicious activity.

WHAT IS A SPYWARE

Spyware is a type of malicious software -- or malware -- that is installed on a computing device without the end user's knowledge. It invades the device, steals sensitive information and internet usage data, and relays it to advertisers, data firms or external users.

WHAT ARE THE FEATURES OF THIS CODE

(1)Record keystrokes and store it in a text file.

(2)Record clipboard in a text file.

(3)Record google search history and store in an excel file.

(4)Retrieve user system's information like IP address, host, OS etc.

(5)Finally take a screenshot when you stop the program.

