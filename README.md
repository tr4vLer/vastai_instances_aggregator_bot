# vastai_performance_bot

**How to make it work?**

0. make sure you run script on machine with ssh key that is entered on your vastai account: https://cloud.vast.ai/account/
1. sudo git clone https://github.com/tr4vLer/vastai_performance_bot.git && cd ../vastai_performance_bot && sudo chmod 600 api_key.txt && sudo chmod +x check_gpu_perf_bot_1.py
2. sudo nano api_key.txt
3. sudo sh -c 'nohup python3 check_gpu_perf_bot_1.py > debug_output.log 2>&1 &' && tail -f debug_output.log

**Requirments**
requests
logging
paramiko
re
sys
datetime

**Notes**
1. Am not porgrammer and code is far from perfect. Its just for fun.
2. You might want edit script (line 91) with diffent location for your private ssh key, especially with diffrent username. Am using Ed25519Key that is located at /home/admin/.ssh/id_ed25519
3. You might also want to change Ed25519Key to diffrent auth method (line 99)


**If you want to buy me a coffe (ERC20):  0x7aeEaB74451ab483dc82199597Fd4261ba0BF499**
