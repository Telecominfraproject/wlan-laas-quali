import sys
import os
#install packages
package_list = ['paramiko','dlipower','pytest','scp']
for package_name in package_list:
    try:
os.system('sudo pip install '+package_name)
print("------------INSTALLED: "+package_name+"-------------")
    except:
print("Cannot install "+package_name)

#copy openwrt_ctl.py file
os.system('cd cicd-git/;git clone https://github.com/Telecominfraproject/wlan-testing/; cp /home/lanforge/cicd-git/wlan-testing/libs/apnos/openwrt_ctl.py .;rm -rf wlan-testing/;cd ../')
print("openwrt_ctl.py file copied")