# VASTAI GPU Performance Aggregator for XENGPUMiners

## I greatly appreciate any donation (ERC20): 0x7aeEaB74451ab483dc82199597Fd4261ba0BF499

![image](https://github.com/tr4vLer/vastai_performance_bot/assets/149298759/03ae681b-98e0-4114-a4aa-5e2b3033c240)

## Prerequisites
Using Jozef's oneliner is highly recommended for building your miner on a Vast.ai instance. Follow his guidelines [here](https://github.com/JozefJarosciak/xgpu). 
Otherwise, the script won't work unless you log your miner job into `miner.log`. To do so, connect to each instance and execute: `sudo nohup python3 miner.py --gpu=true > miner.log 2>&1 &`.

## How to prepare?

### Install Python
You need to have Python installed. Find the installation guide [here](https://wiki.python.org/moin/BeginnersGuide/Download).

### Install Dependencies
Use your terminal or PowerShell to install the following requirements:

- **Linux/MacOS:**
  ```sh
  sudo apt update
  pip install requests paramiko prettytable numpy defaultdict
  
- **Windows:**
     ```sh
    python -m pip install --upgrade pip setuptools wheel
    pip install requests paramiko prettytable numpy defaultdict

   
## Generate SSH Key and Configure Vast.ai Account

- Open a terminal (Linux/Mac) or Command Prompt/Powershell (Windows).
- Run the following command to generate a new SSH key pair:
  ```shell
  ssh-keygen -t ed25519
- When prompted, press Enter to save the key pair into the default directory. If you prefer a different location, provide the path.
- If you wish, provide a passphrase for additional security when prompted; otherwise, press Enter to skip.
- Your private key will be saved to a file (by default, it's id_ed25519 in your ~/.ssh/ directory).
- Your public key will be saved to a file with the same name but with a .pub extension (by default, it's id_ed25519.pub).
- Open the public key file with a text editor, copy its content, and paste it into the SSH Keys section on Vast.ai account. Make sure to copy your existing key and store it safely for a potential rollback.
- The content of the public key should look something like this example:
  
  ```shell
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK0
- Ensure that you keep your private key secure and do not share it.


# How to Run VASTAI GPU Performance Aggregator?

### For Windows:
1. Download and unpack this repository.
2. Open `vastai_instances_aggregator_bot.py` in a text editor (e.g., Notepad++) and edit **Line 41** with the path for your SSH key. Follow the detailed instructions included there.
3. Edit `api_key.txt` with your Vast.ai API key. The key should be all the file contains. Find your API key on [https://cloud.vast.ai/account/](https://cloud.vast.ai/account/).
4. Open PowerShell, navigate to the folder with the repository (Example command: `cd C:\Users\user_name\Desktop\vastai_instances_aggregator_bot-main`), and press Enter.
5. Run the script with the command:
   
   ```powershell
   python vastai_instances_aggregator_bot.py

### For MacOS/Linux:
1. Open your command line and execute the following to download the repository and set permissions:

   ```sh
   git clone https://github.com/tr4vLer/vastai_instances_aggregator_bot.git && cd vastai_instances_aggregator_bot && chmod 600 api_key.txt && chmod +x vastai_instances_aggregator_bot.py
2. Open `vastai_instances_aggregator_bot.py` in a text editor and edit **Line 41** with the path for your SSH key. Follow the detailed instructions included there.
3. Edit api_key.txt with your Vast.ai API key. The key should be all the file contains. Find your API key on https://cloud.vast.ai/account/. Optionally, use `sudo nano api_key.txt` from the command line.
4. Run the script with the command:

   ```sh
    sudo sh -c 'nohup python3 vastai_instances_aggregator_bot.py > debug_output.log 2>&1 &' && tail -f debug_output.log

### Disclaimer
Am not porgrammer and code is far from perfect. Its just for fun. 

## If you want to buy me a coffe (ERC20):  0x7aeEaB74451ab483dc82199597Fd4261ba0BF499
