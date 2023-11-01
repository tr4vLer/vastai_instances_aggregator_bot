import requests
import logging
import paramiko
import re
import sys
import datetime

####### User configuration ####### 

# Path to your API key. 
# Default: 'api_key.txt' (Assumes the API key file is located in the same folder as this script).
# Update this path if your API key file is located elsewhere.
API_KEY_FILE = 'api_key.txt'

# SSH Key Configuration:
# In order to securely connect to Vast.ai instances, you need to generate an SSH key pair.
# Follow these steps:
#   1. Open a terminal (Linux/Mac) or Command Prompt/Powershell (Windows).
#   2. Run the following command to generate a new SSH key pair:
#      ssh-keygen -t ed25519
#   3. When prompted, press Enter to save the key pair into the default directory. If you prefer a different location, provide the path.
#   4. If you wish, provide a passphrase for additional security when prompted; otherwise, press Enter to skip.
#   5. Once generated, your private key will be saved to a file (by default, it's id_ed25519 in your ~/.ssh/ directory).
#   6. Your public key will be saved to a file with the same name but with .pub extension (by default, it's id_ed25519.pub).
#   7. Open the public key file with a text editor, copy its content, and paste it into the SSH Keys section on https://cloud.vast.ai/account/.
#      The content of the public key should look something like this example:
#      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK0wmN/Cr3JXqmLW7u+g9pTh+wyqDHpSQEIQczXkVx9q"
#   8. Ensure that you keep your private key secure and do not share it.

# Now, set the path to your private SSH key here. 
# Instructions: 
#   - Windows: Use a raw string (prefix the string with 'r') to ensure backslashes are treated literally, not as escape characters.
#   - Linux/Mac: Use a standard string with forward slashes.
# Example for Windows: r"C:/Users/your_username/.ssh/id_ed25519"
# Example for Linux: "/home/your_username/.ssh/id_ed25519"
# Example for Mac: "/Users/your_username/.ssh/id_ed25519"
private_key_path = r"C:/Users/user_name/.ssh/id_ed25519"

# If your private SSH key is protected by a passphrase, provide it here.
# If not, leave this as an empty string ("").
# Example: passphrase = "your_passphrase"
passphrase = ""

####### Table printout configuration ####### 

# Column index by which the table should be sorted.
# Note: Column indices start at 0. So, for example, to sort by the first column, set this value to 0.
# Default: 11 (Assumes "USD/Block" to sort by.)
sort_column_index = 11

# Order in which the table should be sorted.
# Options: 
#   - 'ascending': Sort from smallest to largest.
#   - 'descending': Sort from largest to smallest.
# Default: 'ascending'
sort_order = 'ascending'

####### End of user configuration ####### 



# Logging Configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("script_output.log"),
                              logging.StreamHandler()])

# Load API Key
try:
    with open(API_KEY_FILE, 'r') as file:
        api_key = file.read().strip()
except FileNotFoundError:
    logging.error(f"API key file '{API_KEY_FILE}' not found.")
    exit(1)
except Exception as e:
    logging.error(f"Error reading API key: {e}")
    exit(1)

# Define Functions
def test_api_connection():
    """Function to test the API connection."""
    test_url = "https://console.vast.ai/api/v0/"
    try:
        response = requests.get(test_url, headers={"Accept": "application/json"})
        if response.status_code == 200:
            logging.info("Connection with API established and working fine.")
        else:
            logging.error(f"Error connecting to API. Status code: {response.status_code}. Response: {response.text}")
    except Exception as e:
        logging.error(f"Error connecting to API: {e}")

def instance_list():
    """Function to list instances and get SSH information."""
    url = f'https://console.vast.ai/api/v0/instances/?api_key={api_key}'
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    ssh_info_list = []

    if response.status_code == 200:
        response_json = response.json()

        if 'instances' not in response_json:
            logging.error("'instances' key not found in response. Please check the API documentation for the correct structure.")
            return ssh_info_list
        instances = response_json['instances']

        # Print information about each instance
        logging.info("Your Instances:")
        
        # Additional variables to store the total_dph for running machines        
        total_dph_running_machines = 0
        
        for instance in instances:
            instance_id = instance.get('id', 'N/A')
            gpu_name = instance.get('gpu_name', 'N/A')
            dph_total = instance.get('dph_total', 'N/A')
            ssh_host = instance.get('ssh_host', 'N/A')
            ssh_port = instance.get('ssh_port', 'N/A')
            num_gpus = instance.get('num_gpus', 'N/A')
            label = instance.get('label', 'N/A')
            actual_status = instance.get('actual_status', 'N/A')
            if actual_status.lower() == 'running':
                total_dph_running_machines += float(dph_total)

            logging.info("Instance ID: %s", instance_id)
            logging.info("GPU Name: %s", gpu_name)
            logging.info("Dollars Per Hour (DPH): %s", dph_total)
            logging.info("SSH Command: ssh -p %s root@%s -L 8080:localhost:8080", ssh_port, ssh_host)
            logging.info("Number of GPUs: %s", num_gpus)
            logging.info("Current state: %s", actual_status)
            logging.info("-" * 30)

            ssh_info = {
                'instance_id': instance_id,
                'gpu_name': gpu_name,
                'dph_total': dph_total,
                'ssh_host': ssh_host,
                'ssh_port': ssh_port,
                'num_gpus': num_gpus,
                'actual_status': actual_status,
                'label': label
            }
            ssh_info_list.append(ssh_info)

    else:
        logging.error("Failed to retrieve instances. Status code: %s. Response: %s", response.status_code, response.text)

    return ssh_info_list, total_dph_running_machines

def clean_ansi_codes(input_string):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.IGNORECASE)
    return ansi_escape.sub('', input_string)

def get_log_info(ssh_host, ssh_port, username):

    # Create an SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Load the private key
        key = paramiko.Ed25519Key(filename=private_key_path, password=passphrase)
        
        # Connect to the server
        ssh.connect(ssh_host, port=ssh_port, username=username, pkey=key)
        
        # Execute the command to get the log information
        _, stdout, _ = ssh.exec_command('tail -n 1 /root/XENGPUMiner/miner.log')
        last_line = stdout.read().decode().strip()
        logging.info("Raw log line: %s", last_line)
        
        # Clean ANSI codes from the log line
        last_line = clean_ansi_codes(last_line)
        
        # Parse the last line to get the required information
        pattern = re.compile(r'Mining:.*\[(?:(\d+):)?(\d+):(\d+),.*(?:Blocks/s|.*(?:Details=(?:super:(\d+)|normal:(\d+)|xuni:(\d+)))).*HashRate:(\d+\.\d+).*Difficulty=(\d+).*\]')
        match = pattern.search(last_line)
        if match:
            # Extracting the running time and blocks information
            hours, minutes, seconds, super_blocks, normal_blocks, xuni_blocks, hash_rate, difficulty = match.groups()
            
            hours = int(hours) if hours is not None else 0
            super_blocks = int(super_blocks) if super_blocks is not None else 0
            normal_blocks = int(normal_blocks) if normal_blocks is not None else 0
            xuni_blocks = int(xuni_blocks) if xuni_blocks is not None else 0

            return int(hours), int(minutes), int(seconds), super_blocks, normal_blocks, xuni_blocks, float(hash_rate), int(difficulty)
        else:
            logging.error("Failed to parse the log line")
            return None, None, None, None, None, None, None, None
        
    except Exception as e:
        logging.error("Failed to connect or retrieve log info: %s", e)
        return None, None, None, None, None, None, None, None
    
    finally:
        ssh.close()


from prettytable import PrettyTable      
def print_table(data, mean_difficulty, average_dollars_per_normal_block, total_dph_running_machines, usd_per_gpu, hash_rate_per_gpu, hash_rate_per_usd, label, output_file='table_output.txt'):
    # Define the table and its columns
    table = PrettyTable()
    table.field_names = ["Instance ID", "GPU Name", "GPU's", "USD/h", "USD/GPU", "Instance h/s", "GPU h/s", "XNM Blocks", "Runtime", "Block/h", "h/s/USD", "USD/Block", "Label"]

    
    # Add rows to the table to console
    for row in data:
        table.add_row(row)

    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print the table
    if mean_difficulty is not None:
        print(f"\nTimestamp: {timestamp}, Difficulty: {int(mean_difficulty)}, Total Hash: {total_hash_rate:.2f} h/s, Total DPH: {total_dph_running_machines:.4f}$, Avg_$/Block: {average_dollars_per_normal_block:.4f}$")
    print(table)

    # Write the table and timestamp to a text file
    with open(output_file, 'a') as f:
        f.write(f"Timestamp: {timestamp}, Difficulty: {int(mean_difficulty)}, Total Hash: {total_hash_rate:.2f} h/s, Total DPH: {total_dph_running_machines:.4f}$, Avg_$/Block: {average_dollars_per_normal_block:.4f}$\n{table}\n")
    print(f"Table also written to {output_file}")


# Test API Connection
test_api_connection()

# List Instances and Get SSH Information
ssh_info_list, total_dph_running_machines = instance_list()
username = "root"

# Store the data for the table
table_data = []
difficulties = []
hash_rates = []
dph_values = []
dollars_per_normal_block_values = []

# Fetch Log Information for Each Instance
for ssh_info in ssh_info_list:
    instance_id = ssh_info['instance_id']
    gpu_name = ssh_info['gpu_name']
    num_gpus = ssh_info['num_gpus']
    actual_status = ssh_info['actual_status']
    label = ssh_info['label'] if ssh_info['label'] is not None else ''       
    dph_total = float(ssh_info['dph_total'])  # Convert DPH to float for calculations
    dph_values.append(dph_total)
    ssh_host = ssh_info['ssh_host']
    ssh_port = ssh_info['ssh_port']

    logging.info("Fetching log info for instance ID: %s", instance_id)
    hours, minutes, seconds, super_blocks, normal_blocks, xuni_blocks, hash_rate, difficulty = get_log_info(ssh_host, ssh_port, username)

    if num_gpus != 'N/A' and dph_total != 'N/A':
        usd_per_gpu = round(dph_total / float(num_gpus), 4)
    else:
        usd_per_gpu = 'N/A'
    if dph_total != 'N/A' and hash_rate is not None:
        hash_rate_per_usd = round(hash_rate / dph_total, 2)
    else:
        hash_rate_per_usd = 'N/A'        
   
    if difficulty is not None and difficulty != 0:
        difficulties.append(difficulty)
    if hash_rate is not None and hash_rate != 0:
        hash_rates.append(hash_rate)        
    
    if normal_blocks is not None and xuni_blocks is not None:
        runtime_hours = hours + minutes / 60 + seconds / 3600
        logging.info("Running Time: %d hours, %d minutes, %d seconds", hours, minutes, seconds)
        logging.info("Normal Blocks: %d", normal_blocks)
        logging.info("HashRate: %.2f", hash_rate)

        # Calculate Block/h and handle the case when runtime is zero
        normal_block_per_hour = normal_blocks / runtime_hours if runtime_hours != 0 else 0

        # Calculate $/Blocks and handle the case when the number of blocks is zero
        if normal_blocks != 0:
            dollars_per_normal_block = (runtime_hours * dph_total) / normal_blocks
            dollars_per_normal_block_values.append(dollars_per_normal_block)
        else:
            dollars_per_normal_block = 0
        
        hash_rate_per_gpu = hash_rate / float(num_gpus) if num_gpus != 'N/A' and hash_rate is not None else 'N/A'
        
        table_data.append([instance_id, gpu_name, num_gpus, round(dph_total, 4), round(usd_per_gpu, 4), round(hash_rate, 2), round(hash_rate_per_gpu, 2), normal_blocks, round(runtime_hours, 2), round(normal_block_per_hour, 2), round(hash_rate_per_usd, 2), round(dollars_per_normal_block, 2), label])        
    else:
        logging.error("Failed to retrieve log information or normal blocks is None for instance ID: %s", instance_id)


    if difficulties:
        mean_difficulty = sum(difficulties) / len(difficulties)
    else:
        logging.info("No valid difficulties were found.")           
    if hash_rates:
        total_hash_rate = sum(hash_rates)
    else:
        logging.info("No valid HashRate were found.")  
    if dph_values:
        total_dph = sum(dph_values)
    else:
        logging.info("No valid DPH values were found.")
    if dollars_per_normal_block_values:
        average_dollars_per_normal_block = sum(dollars_per_normal_block_values) / len(dollars_per_normal_block_values)
    else:
        average_dollars_per_normal_block = None
        logging.info("No valid $/Block values were found.")

# Sort the data by "Blocks/$" in increasing order
    if not table_data:
        print("Error: table_data is empty!")
    elif sort_column_index < 0 or (table_data and sort_column_index >= len(table_data[0])):
        print("Invalid sort_column_index: {}. Must be between 0 and {}.".format(sort_column_index, len(table_data[0])-1 if table_data else 'N/A'))
    else:
        if all(len(row) > sort_column_index for row in table_data):
            table_data.sort(key=lambda x: (x[sort_column_index] if x[sort_column_index] is not None else float('-inf'), x), 
                            reverse=(sort_order == 'descending'))
        else:
            print("Error: Not all rows have enough columns for sort_column_index {}".format(sort_column_index))
# Print the table
print_table(table_data, mean_difficulty, average_dollars_per_normal_block, total_dph_running_machines, usd_per_gpu, hash_rate_per_gpu, hash_rate_per_usd, label)

# Exit the script
sys.exit()
