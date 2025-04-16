import serial
from tests.comms_importer import comms
from polling import poll, TimeoutException

# Hardcoded file paths for the certificates
rootca_file_path = '/home/sumaji/Test/AmazonRootCA1.pem'
otacert_file_path = '/home/sumaji/Test/ota_certificate.pem'

# Serial Port Settings
SERIAL_PORT = '/dev/ttyS0'  # Use COM^ for Windows

sp = serial.Serial(port=SERIAL_PORT, baudrate=115200, timeout=0.1)

def write_device(input: str):
    """Send the string data in input to the device, encoded in iso_8859_1."""
    sp.write(input.encode('iso_8859_1', 'replace'))

def read_device() -> str:
    """Read the data that is currently available in the buffer."""
    received = sp.readline()
    return received.decode('iso_8859_1')

def cmd(input: str, print_output: bool = True, timeout: int = 120) -> str:
    """Send the input, then wait up to 120 seconds for a response"""
    if len(input) > 0:
        write_device(input)

    response: str = ""
    if print_output:
        print(bytes(f"Command:  {input}", encoding='iso_8859_1'), end='')

    def check_response() -> bool:
        nonlocal response
        response += read_device()
        if print_output:
            print('.', end='', flush=True)
        return len(response) > 0 and response[-1] == "\n"

    poll(check_response, step=0.01, timeout=timeout)
    if print_output:
        print()
        print(bytes(f"Response: {response}", encoding='iso_8859_1'),
              end='\n\n')
    return response

def read_file(filename):
    """Read the content of a file."""
    with open(filename, 'r') as f:
        return f.read()

def main():
    rootca = read_file(rootca_file_path)
    otacert = read_file(otacert_file_path)

    cmd(f"AT+CONF RootCA=pem\n{rootca}", print_output=True)
    cmd(f"AT+CONF OTAcertificate=pem\n{otacert}", print_output=True)

if __name__ == "__main__":
    main()
