import requests
import logging
import paramiko
import re
import sys
import datetime

API_KEY_FILE = 'api_key.txt'

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
        for instance in instances:
            instance_id = instance.get('id', 'N/A')
            gpu_name = instance.get('gpu_name', 'N/A')
            dph_total = instance.get('dph_total', 'N/A')
            ssh_host = instance.get('ssh_host', 'N/A')
            ssh_port = instance.get('ssh_port', 'N/A')
            num_gpus = instance.get('num_gpus', 'N/A')

            logging.info("Instance ID: %s", instance_id)
            logging.info("GPU Name: %s", gpu_name)
            logging.info("Dollars Per Hour (DPH): %s", dph_total)
            logging.info("SSH Command: ssh -p %s root@%s -L 8080:localhost:8080", ssh_port, ssh_host)
            logging.info("Number of GPUs: %s", num_gpus)
            logging.info("-" * 30)

            ssh_info = {
                'instance_id': instance_id,
                'gpu_name': gpu_name,
                'dph_total': dph_total,
                'ssh_host': ssh_host,
                'ssh_port': ssh_port,
                'num_gpus': num_gpus
            }
            ssh_info_list.append(ssh_info)

    else:
        logging.error("Failed to retrieve instances. Status code: %s. Response: %s", response.status_code, response.text)

    return ssh_info_list

def clean_ansi_codes(input_string):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.IGNORECASE)
    return ansi_escape.sub('', input_string)

import re

def get_log_info(ssh_host, ssh_port, username):
    private_key_path = "/home/admin/.ssh/id_ed25519"
    
    # Create an SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Load the private key
        key = paramiko.Ed25519Key(filename=private_key_path)
        
        # Connect to the server
        ssh.connect(ssh_host, port=ssh_port, username=username, pkey=key)
        
        # Execute the command to get the log information
        _, stdout, _ = ssh.exec_command('tail -n 1 /root/XENGPUMiner/miner.log')
        last_line = stdout.read().decode().strip()
        logging.info("Raw log line: %s", last_line)
        
        # Clean ANSI codes from the log line
        last_line = clean_ansi_codes(last_line)
        
        # Parse the last line to get the required information
        pattern = re.compile(r'Mining:.*\[(\d+):(\d+):(\d+),.*(?:Details=normal:(\d+)|Details=xuni:(\d+)).*HashRate:(\d+.\d+).*Difficulty=(\d+).*\]')
        match = pattern.search(last_line)
        if match:
            # Extracting the running time and normal blocks
            hours, minutes, seconds, normal_blocks, xuni_blocks, hash_rate, difficulty = match.groups()
            blocks = int(normal_blocks) if normal_blocks is not None else int(xuni_blocks) if xuni_blocks is not None else None
            
            if blocks is not None:
                return int(hours), int(minutes), int(seconds), blocks, float(hash_rate), int(difficulty)
            else:
                logging.error("Failed to extract block information")
                return None, None, None, None, None, None
        else:
            logging.error("Failed to parse the log line")
            return None, None, None, None, None, None
        
    except Exception as e:
        logging.error("Failed to connect or retrieve log info: %s", e)
        return None, None, None, None, None, None
    
    finally:
        ssh.close()


from prettytable import PrettyTable      
def print_table(data, mean_difficulty, output_file='table_output.txt'):
    # Define the table and its columns
    table = PrettyTable()
    table.field_names = ["Instance ID", "GPU Name", "GPU count", "HashRate (h/s)", "DPH", "XNM Blocks", "Runtime (hours)", "Block/h", "$/Blocks"]
    
    # Add rows to the table to console
    for row in data:
        table.add_row(row)

    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print the table
    if mean_difficulty is not None:
        print(f"\nTimestamp: {timestamp}, Difficulty: {int(mean_difficulty)}, Total Hash: {total_hash_rate:.2f}h/s, Total DPH: {total_dph:.4f}$")
    print(table)

    # Write the table and timestamp to a text file
    with open(output_file, 'a') as f:
        f.write(f"Timestamp: {timestamp}, Difficulty: {int(mean_difficulty)}, Total Hash: {total_hash_rate:.2f}h/s, Total DPH: {total_dph:.4f}$\n{table}\n")
    print(f"Table also written to {output_file}")


# Test API Connection
test_api_connection()

# List Instances and Get SSH Information
ssh_info_list = instance_list()
username = "root"

# Store the data for the table
table_data = []
difficulties = []
hash_rates = []
dph_values = []

# Fetch Log Information for Each Instance
for ssh_info in ssh_info_list:
    instance_id = ssh_info['instance_id']
    gpu_name = ssh_info['gpu_name']
    num_gpus = ssh_info['num_gpus']
    dph_total = float(ssh_info['dph_total'])  # Convert DPH to float for calculations
    dph_values.append(dph_total)
    ssh_host = ssh_info['ssh_host']
    ssh_port = ssh_info['ssh_port']

    logging.info("Fetching log info for instance ID: %s", instance_id)
    hours, minutes, seconds, normal_blocks, hash_rate, difficulty = get_log_info(ssh_host, ssh_port, username)
    
    if difficulty is not None and difficulty != 0:
        difficulties.append(difficulty)
    if hash_rate is not None and hash_rate != 0:
        hash_rates.append(hash_rate)        
    
    if hours is not None:
        runtime_hours = hours + minutes / 60 + seconds / 3600
        logging.info("Running Time: %d hours, %d minutes, %d seconds", hours, minutes, seconds)
        logging.info("Normal Blocks: %d", normal_blocks)
        logging.info("HashRate: %.2f", hash_rate)
        # Calculate Block/h and handle the case when runtime is zero
        block_per_hour = normal_blocks / runtime_hours if runtime_hours != 0 else 0

        # Calculate Blocks/$ and handle the case when the number of blocks is zero
        blocks_per_dollar = (runtime_hours * dph_total) / normal_blocks if normal_blocks != 0 else 0
        
        table_data.append([instance_id, gpu_name, num_gpus, round(hash_rate, 2), round(dph_total, 4), normal_blocks, round(runtime_hours, 2), round(block_per_hour, 2), round(blocks_per_dollar, 2)])
    else:
        logging.error("Failed to retrieve log information for instance ID: %s", instance_id)

    if difficulties:
        mean_difficulty = sum(difficulties) / len(difficulties)
        logging.info("Difficulty: %d", mean_difficulty)
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
        

# Sort the data by "Blocks/$" in increasing order
table_data.sort(key=lambda x: x[8] if x[8] is not None else float('-inf'))

# Print the table
print_table(table_data, mean_difficulty)

# Exit the script
sys.exit()
