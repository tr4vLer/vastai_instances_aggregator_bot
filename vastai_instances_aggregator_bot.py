import requests
import logging
import paramiko
import re
import sys
import datetime
import time
from prettytable import PrettyTable 
from collections import defaultdict
import numpy as np


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
private_key_path = r"C:/Users/your_username/.ssh/id_ed25519"

# If your private SSH key is protected by a passphrase, provide it here.
# If not, leave this as an empty string ("").
# Example: passphrase = "your_passphrase"
passphrase = ""

####### Table printout configuration ####### 

# Column index by which the table should be sorted.
# Note: Column indices start at 0. So, for example, to sort by the first column, set this value to 0.
# Default: 12 (Assumes "USD/Block" to sort by.)
sort_column_index = 11

# Order in which the table should be sorted.
# Options: 
#   - 'ascending': Sort from smallest to largest.
#   - 'descending': Sort from largest to smallest.
# Default: 'ascending'
sort_order = 'ascending'

####### Outliers configuration ####### 

# Think of the Z-Score as a "performance alert" level for your GPUs.
# It helps you spot GPUs that aren't performing as well as you expect, compared to the group average.
# The Z-Score measures how far a GPU's performance is from the average, in terms of group's standard deviation.
# Setting a lower threshold means you're tightening the criteria and will get alerts for smaller deviations from the average.
# A default threshold of 1 indicates GPUs that performing 2x standard deviations below the group average
# It's a way to catch the biggest concerns without too many false alarms. Adjust the threshold to find the best balance for your monitoring needs.
threshold = 1

####### Current balance printout for Vast.ai account ####### 

# Set 'print_balance_check' to 'False' if you do not wish to print your balance information.
# When set to 'True', the script will display the current balance from your Vast.ai account.
print_balance_check = True


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
    ssh_info_list = []
    total_dph_running_machines = 0  # Initialized at the start

    for attempt in range(3):  # Retrying up to 3 times
        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                response_json = response.json()

                if 'instances' not in response_json:
                    logging.error("'instances' key not found in response. Please check the API documentation for the correct structure.")
                    return ssh_info_list, total_dph_running_machines
                instances = response_json['instances']
                logging.info("Your Instances:")

                for instance in instances:
                    instance_id = instance.get('id', 'N/A')
                    gpu_name = instance.get('gpu_name', 'N/A')
                    dph_total = instance.get('dph_total', 'N/A')
                    ssh_host = instance.get('ssh_host', 'N/A')
                    ssh_port = instance.get('ssh_port', 'N/A')
                    num_gpus = instance.get('num_gpus', 'N/A')
                    gpu_util = instance.get('gpu_util', 'N/A')
                    label = instance.get('label', 'N/A')
                    actual_status = instance.get('actual_status', 'N/A')
                    if actual_status.lower() == 'running':
                        total_dph_running_machines += float(dph_total)

                    logging.info(f"Instance ID: {instance_id}")
                    logging.info(f"GPU Name: {gpu_name}")
                    logging.info(f"Dollars Per Hour (DPH): {dph_total}")
                    logging.info(f"SSH Command: ssh -p {ssh_port} root@{ssh_host} -L 8080:localhost:8080")
                    logging.info(f"Number of GPUs: {num_gpus}")
                    logging.info(f"Current state: {actual_status}")
                    logging.info("-" * 30)

                    ssh_info = {
                        'instance_id': instance_id,
                        'gpu_name': gpu_name,
                        'dph_total': dph_total,
                        'ssh_host': ssh_host,
                        'ssh_port': ssh_port,
                        'num_gpus': num_gpus,
                        'gpu_util': gpu_util,
                        'actual_status': actual_status,
                        'label': label
                    }
                    ssh_info_list.append(ssh_info)

                # Break out of the retry loop upon success
                break

            elif response.status_code == 429:
                logging.error("Too many requests, retrying in 10 seconds...")
                if attempt < 2:  # Wait only if we have retries left
                    time.sleep(10)
                else:
                    logging.error("Maximum retries reached. Please try again later.")
            
            elif response.status_code == 401:
                # Handle Unauthorized error
                logging.error("Failed to retrieve instances. Status code: 401. Response: %s", response.text)
                logging.error("This action requires a valid login. Please make sure that api_key.txt contains the correct API key and that the key is the only thing the file contains.")
                break  # No need to retry, authorization issues cannot be solved by retrying

            else:
                logging.error("Failed to retrieve instances. Status code: %s. Response: %s", response.status_code, response.text)
                break  # Exit loop if an unrelated error occurs

        except requests.exceptions.RequestException as e:
            logging.error("A requests exception occurred: %s", str(e))
            break  # Exit loop if a request-related exception occurs

        except Exception as e:
            logging.error("An unexpected error occurred: %s", str(e))
            break  # Exit loop for any other exception

    return ssh_info_list, total_dph_running_machines


# Function to calculate time covered by balance
def calculate_time_covered_by_balance(balance, total_dph):
    # Calculate the total daily cost by multiplying the hourly cost by 24
    daily_cost = total_dph * 24
    # Add a 1% fee disk space cost to the total daily cost
    daily_cost_with_fee = daily_cost * 1.01  # 1% fee
    # Calculate the number of days the balance will last
    days_covered = balance / daily_cost_with_fee
    # Extract the whole days
    whole_days = int(days_covered)
    # Calculate the remaining hours after whole days
    remaining_hours = (days_covered - whole_days) * 24
    # Extract the whole hours
    whole_hours = int(remaining_hours)
    # Calculate the remaining minutes after whole hours
    remaining_minutes = (remaining_hours - whole_hours) * 60
    # Extract the whole minutes
    whole_minutes = int(remaining_minutes)

    return whole_days, whole_hours, whole_minutes

# Function to check Vast.ai balance
def check_vastai_balance(api_key, total_dph_running_machines):
    url = f'https://console.vast.ai/api/v0/users/current?api_key={api_key}'
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        balance = data.get('credit', None)
        if balance is not None:
            balance = float(balance)  # Ensure the balance is a float
            hourly_cost = total_dph_running_machines
            daily_cost = hourly_cost * 24
            daily_cost_with_fee = daily_cost * 1.01  
            # Display the balance and estimated spend rate
            print(f"Your Vast.ai balance is: ${balance:.2f}")
            print(f"Your estimated spend rate: ${daily_cost_with_fee:.2f}/day")
            # Calculate the time covered by balance
            days, hours, minutes = calculate_time_covered_by_balance(balance, hourly_cost)
            print(f"Your balance with current total DPH value will last for approximately {days} days, {hours} hours, and {minutes} minutes.")
        else:
            print("Balance information was not available in the response.")
    else:
        print(f"Failed to retrieve data: {response.status_code}")

# Function to remove ANSI escape codes
def clean_ansi_codes(input_string):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.IGNORECASE)
    return ansi_escape.sub('', input_string)


def get_log_info(ssh_host, ssh_port, username, private_key_path, passphrase=None):
    # Create an SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Attempt to load the private key with the provided passphrase
        try:
            key = paramiko.Ed25519Key(filename=private_key_path, password=passphrase)
        except paramiko.ssh_exception.PasswordRequiredException:
            logging.error("Private key file is encrypted and requires a passphrase.")
            return None, None, None, None, None, None, None, None
        except paramiko.ssh_exception.SSHException as e:
            logging.error("Failed to decrypt private key with provided passphrase: %s", e)
            return None, None, None, None, None, None, None, None

        # Connect to the server
        ssh.connect(ssh_host, port=ssh_port, username=username, pkey=key)
        
        # Execute the command to get the log information
        _, stdout, _ = ssh.exec_command('tail -n 1 /root/XENGPUMiner/miner.log')
        last_line = stdout.read().decode().strip()
        logging.info("Raw log line: %s", last_line)
        
        # Clean ANSI codes from the log line
        last_line = clean_ansi_codes(last_line)
        
        # Parse the last line to get the required information
        pattern = re.compile(r'Mining:.*\[(?:(\d+):)?(\d+):(\d+)(?:\.\d+)?,.*?(?:Details=(?:(?:super:(\d+)\s)?normal:(\d+)|xuni:(\d+)).*?)?HashRate:(\d+\.\d+).*Difficulty=(\d+)')
        match = pattern.search(last_line)
        if match:
            # Extracting the running time and blocks information
            hours, minutes, seconds, super_blocks, normal_blocks, xuni_blocks, hash_rate, difficulty = match.groups()
            
            hours = int(hours) if hours is not None else 0
            minutes = int(minutes)
            seconds = int(seconds)
            super_blocks = int(super_blocks) if super_blocks is not None else 0
            normal_blocks = int(normal_blocks) if normal_blocks is not None else 0
            xuni_blocks = int(xuni_blocks) if xuni_blocks is not None else 0
            hash_rate = float(hash_rate)
            difficulty = int(difficulty)
    
            return hours, minutes, seconds, super_blocks, normal_blocks, xuni_blocks, hash_rate, difficulty
        else:
            logging.error("Failed to parse the log line: %s", last_line)
            return None, None, None, None, None, None, None, None
        
    except Exception as e:
        logging.error("Failed to connect or retrieve log info: %s", e)
        return None, None, None, None, None, None, None, None
    
    finally:
        ssh.close()

     
def print_table(data, mean_difficulty, average_dollars_per_normal_block, total_dph_running_machines, usd_per_gpu, hash_rate_per_gpu, hash_rate_per_usd, label, sum_normal_block_per_hour, total_hash_rate, output_file='table_output.txt'):
    if not data:  # If data list is empty, do not proceed.
        print("No data to print.")
        return
    # Define the table and its columns
    table = PrettyTable()
    table.field_names = ["Instance ID", "GPU Name", "GPU's", "Util.%", "USD/h", "USD/GPU", "Inst.H/s", "GPU H/s", "XNM Blocks", "Runtime", "Block/h", "H/s/USD", "USD/Block", "Label"]

    # Add rows to the table
    for row in data:
        table.add_row(row)

    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Print the table
    try:
        if mean_difficulty is not None:
            difficulty = int(mean_difficulty)
        else:
            difficulty = "N/A"
        
        total_hash_rate_str = f"{total_hash_rate:.2f} h/s" if total_hash_rate is not None else "N/A"
        total_dph_running_machines_str = f"{total_dph_running_machines:.4f}$" if total_dph_running_machines is not None else "N/A"
        average_dollars_per_normal_block_str = f"{average_dollars_per_normal_block:.4f}$" if average_dollars_per_normal_block is not None else "N/A"
        sum_normal_block_per_hour_str = f"{sum_normal_block_per_hour:.2f}" if sum_normal_block_per_hour is not None else "N/A"
        
        print("")
        print(f"\nTimestamp: {timestamp}, Difficulty: {difficulty}, Total Hash: {total_hash_rate_str}, Total DPH: {total_dph_running_machines_str}, Avg_$/Block: {average_dollars_per_normal_block_str}, Total Blocks/h: {sum_normal_block_per_hour_str}")
        print(table)
    except TypeError as e:
        print(f"Error printing table: {e}")

    # Write the table and timestamp to a text file
    with open(output_file, 'a') as f:
        try:
            f.write(f"Timestamp: {timestamp}, Difficulty: {difficulty}, Total Hash: {total_hash_rate_str}, Total DPH: {total_dph_running_machines_str}, Avg_$/Block: {average_dollars_per_normal_block_str}, Total Blocks/h: {sum_normal_block_per_hour_str}\n{table}\n")
        except TypeError as e:
            print(f"Error writing to file: {e}")

    print(f"Table also written to {output_file}\n")


# Test API Connection
test_api_connection()

# List Instances and Get SSH Information
ssh_info_list, total_dph_running_machines = instance_list()
username = "root"



# Initialize Data Storage
gpu_hash_rates = defaultdict(list)
dph_values = []
difficulties = []
hash_rates = []
dollars_per_normal_block_values = []
sum_normal_block_per_hour = 0
table_data = []
mean_difficulty = None
average_dollars_per_normal_block = None
usd_per_gpu = None
hash_rate_per_gpu = None
hash_rate_per_usd = None
label = None
total_hash_rate = sum(hash_rates)
gpu_util = None
gpu_util_warnings_set = set()
# Fetch Log Information for Each Instance
for ssh_info in ssh_info_list:
    instance_id = ssh_info['instance_id']
    gpu_name = ssh_info['gpu_name']
    num_gpus = ssh_info['num_gpus']
    gpu_util = ssh_info['gpu_util']
    actual_status = ssh_info['actual_status']
    label = ssh_info['label'] if ssh_info['label'] is not None else ''       
    dph_total = float(ssh_info['dph_total'])  # Convert DPH to float for calculations
    dph_values.append(dph_total)
    ssh_host = ssh_info['ssh_host']
    ssh_port = ssh_info['ssh_port']

    logging.info("Fetching log info for instance ID: %s", instance_id)
    hours, minutes, seconds, super_blocks, normal_blocks, xuni_blocks, hash_rate, difficulty = get_log_info(ssh_host, ssh_port, username, private_key_path, passphrase)

    # Warning if instance is running but GPU not fully utilized
    if actual_status == "running" and gpu_util is not None and gpu_util < 85:  # Check if gpu_util is below 90%
        warning_message = f"GPU Utilization for instance {instance_id} is at {gpu_util:.2f}% - Make sure XENGPUMiner is working!"
        if warning_message not in gpu_util_warnings_set:
            gpu_util_warnings_set.add(warning_message)

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

        # Calculate Block/h, sum it and handle the case when runtime is zero
        if runtime_hours != 0:
            normal_block_per_hour = normal_blocks / runtime_hours
            # Update sum
            sum_normal_block_per_hour += normal_block_per_hour
        else:
            normal_block_per_hour = 0

        # Calculate $/Blocks and handle the case when the number of blocks is zero
        if normal_blocks != 0:
            dollars_per_normal_block = (runtime_hours * dph_total) / normal_blocks
            dollars_per_normal_block_values.append(dollars_per_normal_block)
        else:
            dollars_per_normal_block = 0
        
        hash_rate_per_gpu = hash_rate / float(num_gpus) if num_gpus != 'N/A' and hash_rate is not None else 'N/A'
        
        if hash_rate is not None and hash_rate != 0 and num_gpus != 'N/A':
            hash_rate_per_gpu = hash_rate / float(num_gpus)
            gpu_hash_rates[gpu_name].append(hash_rate_per_gpu)
        else:
            hash_rate_per_gpu = 'N/A'
        
        table_data.append([instance_id, gpu_name, num_gpus, round(gpu_util, 2), round(dph_total, 4), round(usd_per_gpu, 4), hash_rate, hash_rate_per_gpu, normal_blocks, round(runtime_hours, 2), round(normal_block_per_hour, 2), round(hash_rate_per_usd, 2), round(dollars_per_normal_block, 2), label])        
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

# Sort the data by "<column_name>" in asc or desc order
    if not table_data:
        print("Error: table_data is empty!")
    elif sort_column_index < 0 or (table_data and sort_column_index >= len(table_data[0])):
        print("Invalid sort_column_index: {}. Must be between 0 and {}.".format(sort_column_index, len(table_data[0])-1 if table_data else 'N/A'))
    else:
        # Ensure all rows have the same number of columns
        num_columns = len(table_data[0])
        if all(len(row) == num_columns for row in table_data):
            try:
                # Convert the sort column to float if possible for proper numeric sorting
                table_data.sort(key=lambda x: (float(x[sort_column_index]) if x[sort_column_index] not in (None, 'N/A') else float('-inf'), x), 
                                reverse=(sort_order == 'descending'))
            except ValueError:
                # Fallback to string sorting if conversion to float is not possible
                table_data.sort(key=lambda x: (x[sort_column_index] if x[sort_column_index] not in (None, 'N/A') else '', x), 
                                reverse=(sort_order == 'descending'))
        else:
            print("Error: Not all rows have the same number of columns.")

if print_balance_check:
    print("\n" + "-" * 60 + "\n")
    check_vastai_balance(api_key, total_dph_running_machines)
    print("\n" + "-" * 60)

# Print the table
print_table(table_data, mean_difficulty, average_dollars_per_normal_block, total_dph_running_machines, usd_per_gpu, hash_rate_per_gpu, hash_rate_per_usd, label, sum_normal_block_per_hour, total_hash_rate)
   
    
# Calculate Outliers
outliers = defaultdict(list)
performances = defaultdict(lambda: {'bottom': []})
highlighted_outliers = defaultdict(list)

# Calculating mean and standard deviation for each GPU type
stats = {}

instance_gpu_mapping = {row[0]: (row[1], row[6]) for row in table_data}
for gpu_type, hash_rates in gpu_hash_rates.items():
    if len(hash_rates) > 1:
        average_hash_rate = np.mean(hash_rates)
        std_dev_hash_rate = np.std(hash_rates, ddof=1)  # Set 'ddof=1' for sample standard deviation
        stats[gpu_type] = {"mean": average_hash_rate, "std_dev": std_dev_hash_rate}

        # Calculate outliers and performances based on actual data per GPU type
        for instance_id, (instance_gpu_type, instance_hash_rate) in instance_gpu_mapping.items():
            if instance_gpu_type == gpu_type and instance_hash_rate != 'N/A':
                instance_hash_rate = float(instance_hash_rate)
                z_score = (instance_hash_rate - average_hash_rate) / std_dev_hash_rate
                if z_score < -threshold:
                    highlighted_outliers[gpu_type].append((instance_id, instance_hash_rate, z_score))


# Print Warnings if GPU not fully utilized
for warning in gpu_util_warnings_set:
    logging.warning(warning)
print("\n" + "-" * 60 )  # Print a blank line for visual separation if there were any warnings     

# Print Outliers and Stats
insufficient_data_messages = []  # List to store messages for insufficient data
for gpu_type in gpu_hash_rates.keys():  # Iterate through all GPU types

    if gpu_type in stats:
        mean = stats[gpu_type]["mean"]
        std_dev = stats[gpu_type]["std_dev"]
        print(f"\n** {gpu_type} Performance Stats: **")
        print(f"- Average hash rate: {mean:.2f} H/s, Standard deviation: {std_dev:.2f} H/s")

        if gpu_type in highlighted_outliers and highlighted_outliers[gpu_type]:
            # Sort the highlighted outliers by Z-Score from lowest to highest (worst to best)
            sorted_outliers = sorted(highlighted_outliers[gpu_type], key=lambda x: x[2])
            
            print("- Note: Some instances are below the average hash rate:")
            for ID, h_rate, z_score in sorted_outliers:
                percent_from_mean = (mean - h_rate) / mean * 100  # Calculate the percentage from the mean here
                print(f"  - Instance ID {ID}: {h_rate:.2f}H/s, {percent_from_mean:.2f}% below average, Variance: {z_score:.2f} Z-Score")
            print()
        else:
            # Check the standard deviation and print an additional message if needed
            print("- All instances are performing within expected range.")
            if std_dev > 50:
                print(f"  (!) Warning: Alarming deviation for {gpu_type} above 50 H/s! Consider lowering the Z-Score threshold in User configuration and re-run script for more details.")
    else:
        insufficient_data_messages.append(f"** {gpu_type}: ** Not enough data to measure performance stats.")

# Print messages for insufficient data at the end
print("\n" + "-" * 60 + "\n")
for message in insufficient_data_messages:
    print(message)

# Exit the script
sys.exit()
