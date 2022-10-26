import sys
import os
#install packages
package_list1 = ['paramiko','dlipower','pytest','scp']
package_list2 = ['git','jq']
for package_name in package_list1:
    try:
        os.system('sudo pip install '+package_name)
        print("------------INSTALLED: "+package_name+"-------------")
    except Exception as e:
        print("Cannot install "+package_name)
        print("Try running: sudo yum install "+package_name)
        print(e)

for package_name in package_list2:
    try:
        os.system('sudo yum install '+package_name)
        print("------------INSTALLED: "+package_name+"-------------")
    except Exception as e:
        print("Cannot install "+package_name)
        print("Try running: sudo pip install "+package_name)
        print(e)


#copy openwrt_ctl.py file
try:
    os.system('cd cicd-git/;git clone https://github.com/Telecominfraproject/wlan-testing/; cp wlan-testing/libs/apnos/openwrt_ctl.py .;rm -rf wlan-testing/;cd ../')
    print("openwrt_ctl.py file copied")
except Exception as e:
    print(e)
    print("Check with lab admin if terminal server can be connected to")
