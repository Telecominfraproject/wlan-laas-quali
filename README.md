# wlan-laas-quali

This Repo holds the code base related to the Quali CloudShell installation.<br><br>
The repo should be kept up to date with what is being run within CloudShell.<br>

## Orchestration

The Orchestration contains Generic scripts including Blueprint scripts, Resource Scrips, Setup scripts and Teardown scripts.
The type of script denotes when or from where the script can be run, either automatically or manually through the UI/API.<br><br>
Blueprint scripts will be run on the Sandbox level and will not be run automatically.<br><br>
Resource scripts will be run on the Resource level and will not be run automatically.<br><br>
Setup Scripts will be run on the Sandbox level and will be run automatically when reserving a Blueprint.<br><br>
Teardown Scripts will be run on the Sandbox level and will be run automatically when ending a resevation.<br><br>

## Scripts

The Scripts folder contains any CloudShell related scripts that need a repo to live in.<br>
These can include scripts that CloudShell will download and run from this repo or scripts to be run externally that interact with CloudShell through any of it's APIs.

The terminal_server_setup.py script can be run as follows:
1. SSH into the terminal server you want to setup
2. Make sure github is installed by running " git --version" , if it is not installed use "pip install git", "sudo yum install git" or "yum install git".
3. Run the following commands
git clone https://github.com/Telecominfraproject/wlan-laas-quali
python3 wlan-laas-quali/Scripts/terminal_server_setup.py

## Shells

The Shells folder contains any resource Shells created and used within CloudShell. Shells contain code to create an instance within CloudShell of any physical or virtual resource to be used within a Sandbox environment.
Shells will also define and set attributes on the created resource instance to be used within the various automated processes within CloudShell.
Shells are typically created for a specific OS to keep away from any command incompatibilities.

## Usage

All Scripts and shells are loading into CloudShell through the web UI, or shells can also be loaded through the shellfoundry cli tool.
Before loading, scripts and shells must be zipped. For shells specifically, the 'src' folder must be zipped with filename specified at the bottom of the 'shell-definition.yaml' as well.

## setup steps for dev environment
https://help.quali.com/Online%20Help/0.0/Portal/Content/DevGuide/Shells/Getting-Started.htm?tocpath=The%20CloudShell%20DevGuide%7CDeveloping%20Shells%7C_____1

`$ pip3 install shellfoundry`
`$ shellfoundry config` : This command returns something like this:


`key`              | `value`      

 host              | localhost    * 
 password          | [encrypted]  * 
 template_location | Empty        * 
 username          | admin        * 
 port              | 9000         *                                                                                                                                                                                
 github_password   | [encrypted]  *                                                                                                                                                                                
 github_login      |              *                                                                                                                                                                                
 domain            | Global       *                                                                                                                                                                                
 author            | Anonymous    *                                                                                                                                                                                
 online_mode       | True         *                                                                                                                                                                                
 defaultview       | gen2         *                                                                                                                                                                                
                                                                                                                                                                                                                  

    * Value marked with '*' is actually the default value and has not been override by the user.

To set value  :
    `$ shellfoundry config <key> <Value>`

To set the value of host to the IP address (or hostname) of the Windows Server:
    `$ shellfoundry config host <IP of Server>`

To set the value of password:
    `$ shellfoundry config password <password of Server>`

Run `$ shellfoundry list`  to check if server configuration is successful
Use `$ shellfoundry new <shell name> --python 3 --template gen2/resource` : This will create a new shell called <shell name> which uses python3 based on a gen2/resource template  

Server configuration is needed to access templates. If server is not configured, you will see this error
    Error: Cannot retrieve standards list. Error: Connection to CloudShell Server failed. Please make sure it is up and running properly.

`$ cd <shell name>`
`$ sudo apt install python3.9-venv` //For virtual environment 
`$ python3 -m venv <venv-name> `   //For virtual environment
`$ source <venv-name>/bin/activate`
`$ python3 -m pip install -r src/requirements.txt` //Ensure all basic shell dependencies are installed


To reflect changes from local setup to CloudShell
Run `$ shellfoundry install`  within <shell name> dir. Make sure Windows server is configured and reachable for this step
Local shell changes should be reflected in CloudShell now: 
    Click on inventory 
    Select `+ Add New`
    The newly installed shell i.e. <shell name> should now be visible



