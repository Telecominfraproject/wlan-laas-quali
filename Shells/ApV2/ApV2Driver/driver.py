import os
import shutil
import subprocess
import tempfile
import paramiko
import requests
import time

from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext

from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from data_model import *  # run 'shellfoundry generate' to generate data model classes

# Vars for PDU functions
GITHUB_REPO = 'https://github.com/Telecominfraproject/wlan-testing.git'
GITHUB_REPO_Branch = 'master'
GITHUB_REPO_NAME = 'wlan-testing'
PDU_REPO_PATH = 'tools'
PDU_SCRIPT_NAME = 'pdu_v3.py'

# Vars for ap redirect
SCRIPT_URL = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-change-ap-redirector.sh'
SCRIPT_URL2 = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-library.sh'
SCRIPT_URL3 = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-config.sh'
URL_TEMPLATE = 'gw-{}.cicd.lab.wlan.tip.build'

def onerror(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)


class ApV2Driver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        # See below some example code demonstrating how to return the resource structure and attributes
        # In real life, this code will be preceded by SNMP/other calls to the resource details and will not be static
        # run 'shellfoundry generate' in order to create classes that represent your data model

        resource = ApV2.create_from_context(context)
        # resource.vendor = 'specify the shell vendor'
        # resource.model = 'specify the shell model'

        for i in range(2):
            port = ResourcePort('connector' + str(i))
            resource.add_sub_resource(str(i), port)

        return resource.create_autoload_details()

    # </editor-fold>

    # <editor-fold desc="Orchestration Save and Restore Standard">
    def orchestration_save(self, context, cancellation_context, mode, custom_params):
      """
      Saves the Shell state and returns a description of the saved artifacts and information
      This command is intended for API use only by sandbox orchestration scripts to implement
      a save and restore workflow
      :param ResourceCommandContext context: the context object containing resource and reservation info
      :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
      :param str mode: Snapshot save mode, can be one of two values 'shallow' (default) or 'deep'
      :param str custom_params: Set of custom parameters for the save operation
      :return: SavedResults serialized as JSON
      :rtype: OrchestrationSaveResult
      """
      pass

    def orchestration_restore(self, context, cancellation_context, saved_artifact_info, custom_params):
        """
        Restores a saved artifact previously saved by this Shell driver using the orchestration_save function
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
        :param str saved_artifact_info: A JSON string representing the state to restore including saved artifacts and info
        :param str custom_params: Set of custom parameters for the restore operation
        :return: None
        """
        pass

    # </editor-fold>

    def apRedirect(self, context, namespace):
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                resource = ApV2.create_from_context(context)
                res_id = context.reservation.reservation_id
                #redirect_url = URL_TEMPLATE.format(context.reservation.reservation_id.split('-')[0])
                if "." in namespace:
                    redirect_url = namespace
                else:
                    redirect_url = URL_TEMPLATE.format(namespace)



                os.environ['DIGICERT_API_KEY'] = api_session.DecryptPassword(resource.attributes['Digicert API Key']).Value
                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to Digicert AP Redirect {}.'.format(context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                terminal_ip = api_session.GetAttributeValue(context.resource.name, "{}.ip".format(cloudshell_model_name)).Value
                terminal_user = api_session.GetAttributeValue(context.resource.name, "{}.uname".format(cloudshell_model_name)).Value
                terminal_pass = api_session.GetAttributeValue(context.resource.name, "{}.passkey".format(cloudshell_model_name)).Value
                terminal_pass = api_session.DecryptPassword(terminal_pass).Value

                ap_user = api_session.GetAttributeValue(context.resource.name, "{}.User".format(cloudshell_model_name)).Value
                ap_password = api_session.GetAttributeValue(context.resource.name, "{}.Password".format(cloudshell_model_name)).Value
                ap_tty = api_session.GetAttributeValue(context.resource.name, "{}.jumphost_tty".format(cloudshell_model_name)).Value
                ap_ip = api_session.GetResourceDetails(context.resource.name).Address
                ap_jumphost = api_session.GetAttributeValue(context.resource.name, "{}.jumphost".format(cloudshell_model_name)).Value
                ap_port = api_session.GetAttributeValue(context.resource.name, "{}.port".format(cloudshell_model_name)).Value
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=terminal_ip, username=terminal_user,password=terminal_pass)

                unique_dir_name = res_id + ap_tty.split("/")[-1]
                command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing/tools && git checkout master && chmod +x digicert-change-ap-redirector.sh'.format(
                    unique_dir_name, unique_dir_name)
                serial_no = resource.attributes['{}.serial'.format(resource.cloudshell_model_name)]
                command2 = 'cd /tmp/{}/wlan-testing/tools && export DIGICERT_API_KEY={} && ./digicert-change-ap-redirector.sh {} {}'.format(unique_dir_name,api_session.DecryptPassword(resource.attributes['Digicert API Key']).Value,serial_no , redirect_url)
                command3 = 'cd /tmp ; rm -rf {}'.format(unique_dir_name)
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'AP Redirect started started')
                (stdin, stdout, stderr) = s.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 1 executed: Created github repo wlan testing, ready to run ap redirector script for AP {}'.format(context.resource.name))
                (stdin2, stdout2, stderr2) = s.exec_command(command2)
                exit_status = stdout2.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 2 executed: Script digicert-change-ap-redirector.sh was executed for AP : {}'.format(context.resource.name))

                output = ''
                errors = ''
                for line in stdout2.readlines():
                    output += line
                for line in stderr2.readlines():
                    errors += line
                if stdout2.channel.recv_exit_status() != 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'AP Redirect failed on address {} and AP {}: '.format(context.resource.address, context.resource.name) + errors)
                    raise Exception('Error executing Script digicert-change-ap-redirector.sh: ' + errors)
                else:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,output)
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'AP Redirect Executed successfully on AP: {}'.format(context.resource.name))
                (stdin3, stdout3, stderr3) = s.exec_command(command3)
                exit_status = stdout3.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'command 3 executed: removed wlan testing repo for AP: {}'.format(context.resource.name))
                s.close()

    def powerOtherAPs(self, context, cmd='on'):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                resource = ApV2.create_from_context(context)

                other_aps = []

                for each in api_session.FindResources(resourceModel=resource.cloudshell_model_name).Resources:
                    if context.resource.name != each.Name and context.resource.name.split(' - ')[-1] == each.Name.split(' - ')[-1]:
                        other_aps.append(each)

                if other_aps:
                    for each in other_aps:
                        api_session.WriteMessageToReservationOutput(res_id, 'Attempting to power {} {}.'.format(cmd, each.Name))

                        terminal_ip = api_session.GetResourceDetails(each.Name).Address
                        terminal_user = api_session.GetAttributeValue(each.Name, "{}.uname".format(each.ResourceModelName)).Value
                        terminal_pass = api_session.GetAttributeValue(each.Name, "{}.passkey".format(each.ResourceModelName)).Value
                        terminal_pass = api_session.DecryptPassword(terminal_pass).Value
                        hostname = api_session.GetAttributeValue(each.Name, "{}.PDU Host".format(each.ResourceModelName)).Value
                        username = api_session.GetAttributeValue(each.Name, "{}.PDU User".format(each.ResourceModelName)).Value
                        password = api_session.GetAttributeValue(each.Name, "{}.PDU Password".format(each.ResourceModelName)).Value
                        password = api_session.DecryptPassword(password).Value
                        port = api_session.GetAttributeValue(each.Name, "{}.PDU Port".format(each.ResourceModelName)).Value

                        s = paramiko.SSHClient()
                        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        s.connect(hostname=terminal_ip, username=terminal_user,
                                  password=terminal_pass)
                        command = "cd /tmp && mkdir {} && cd {} && git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master".format(
                            res_id, res_id)

                        command2 = "cd /tmp/{}/wlan-testing/tools && python3 {} --host {} --user {} --password {} --action {} --port {}".format(
                            res_id, PDU_SCRIPT_NAME, hostname, username, password, cmd, port)

                        command3 = 'cd /tmp && rm -rf {}'.format(res_id)

                        (stdin, stdout, stderr) = s.exec_command(command)
                        exit_status = stdout.channel.recv_exit_status()
                        if exit_status == 0:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 1 executed: Created github repo wlan testing, ready to run PDU script for AP {}'.format(context.resource.name))

                        (stdin2, stdout2, stderr2) = s.exec_command(command2)
                        exit_status = stdout2.channel.recv_exit_status()
                        if exit_status == 0:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 2 executed: Script {} was executed for AP {}'.format(PDU_SCRIPT_NAME,context.resource.name))
                        output = ''
                        errors = ''
                        for line in stdout.readlines():
                            output += line
                        for line in stderr.readlines():
                            errors += line
                        if stdout2.channel.recv_exit_status() != 0:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'PDU Power command failed on AP: {}. Check script {}'.format(context.resource.name,PDU_SCRIPT_NAME) + errors)
                            raise Exception(errors)
                        else:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, '{} Powered {}.'.format(each.Name, cmd))

                        (stdin3, stdout3, stderr3) = s.exec_command(command3)
                        exit_status = stdout3.channel.recv_exit_status()
                        if exit_status == 0:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                        'command 3 executed: removed wlan testing repo for AP: {}'.format(
                                                                            context.resource.name))
                        s.close()

                else:
                    api_session.WriteMessageToReservationOutput(res_id, 'No APs to power {}.'.format(cmd))

    def powerThisAP(self, context, cmd='on'):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                resource = ApV2.create_from_context(context)
                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to power {} {}.'.format(cmd, context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                terminal_ip = api_session.GetResourceDetails(context.resource.name).Address
                terminal_user = api_session.GetAttributeValue(context.resource.name, "{}.uname".format(cloudshell_model_name)).Value
                terminal_pass = api_session.GetAttributeValue(context.resource.name, "{}.passkey".format(cloudshell_model_name)).Value
                terminal_pass = api_session.DecryptPassword(terminal_pass).Value
                hostname = api_session.GetAttributeValue(context.resource.name, "{}.PDU Host".format(cloudshell_model_name)).Value
                username = api_session.GetAttributeValue(context.resource.name, "{}.PDU User".format(cloudshell_model_name)).Value
                password = api_session.GetAttributeValue(context.resource.name, "{}.PDU Password".format(cloudshell_model_name)).Value
                password = api_session.DecryptPassword(password).Value
                port = api_session.GetAttributeValue(context.resource.name, "{}.PDU Port".format(cloudshell_model_name)).Value

                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=terminal_ip, username=terminal_user,
                          password=terminal_pass)
                command = "cd /tmp && mkdir {} && cd {} && git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master".format(
                    res_id, res_id)

                command2 = "cd /tmp/{}/wlan-testing/tools && python3 {} --host {} --user {} --password {} --action {} --port {}".format(
                    res_id, PDU_SCRIPT_NAME, hostname, username, password, cmd, port)

                command3 = 'cd /tmp && rm -rf {}'.format(res_id)

                (stdin, stdout, stderr) = s.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 1 executed: Created github repo wlan testing')

                (stdin2, stdout2, stderr2) = s.exec_command(command2)
                exit_status = stdout2.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 2 executed')

                output = ''
                errors = ''
                for line in stdout.readlines():
                    output += line
                for line in stderr.readlines():
                    errors += line
                if stdout2.channel.recv_exit_status() != 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'PDU Power command failed: ' + errors)
                    raise Exception(errors)
                else:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Waiting for a minute to power {} {}'.format(cmd,context.resource.name))
                    time.sleep(60)
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, '{} Powered {}.'.format(context.resource.name, cmd))

                (stdin3, stdout3, stderr3) = s.exec_command(command3)
                exit_status = stdout3.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 3 executed: removed wlan testing repo for AP: {}'.format(
                                                                    context.resource.name))
                s.close()

    def rebootAP(self, context):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to reboot {}.'.format(context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                terminal_ip = api_session.GetAttributeValue(context.resource.name, "{}.ip".format(cloudshell_model_name)).Value
                terminal_user = api_session.GetAttributeValue(context.resource.name, "{}.uname".format(cloudshell_model_name)).Value
                terminal_pass = api_session.GetAttributeValue(context.resource.name, "{}.passkey".format(cloudshell_model_name)).Value
                terminal_pass = api_session.DecryptPassword(terminal_pass).Value

                ap_user = api_session.GetAttributeValue(context.resource.name, "{}.User".format(cloudshell_model_name)).Value
                ap_password = api_session.GetAttributeValue(context.resource.name, "{}.Password".format(cloudshell_model_name)).Value
                ap_tty = api_session.GetAttributeValue(context.resource.name, "{}.jumphost_tty".format(cloudshell_model_name)).Value
                ap_ip = api_session.GetResourceDetails(context.resource.name).Address
                ap_jumphost = api_session.GetAttributeValue(context.resource.name, "{}.jumphost".format(cloudshell_model_name)).Value
                ap_port = api_session.GetAttributeValue(context.resource.name, "{}.port".format(cloudshell_model_name)).Value
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=terminal_ip, username=terminal_user,
                          password=terminal_pass)
                unique_dir_name = res_id + ap_tty[-1]
                command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x ap_tools.py'.format(
                    unique_dir_name, unique_dir_name)
                command2 = 'cd /tmp/{}/wlan-testing/tools && python3 ap_tools.py --host {} --jumphost {} --tty {} --port {} --username {} --password {} --cmd "reboot"'.format(
                    unique_dir_name, ap_ip, ap_jumphost, ap_tty, ap_port, ap_user,
                    api_session.DecryptPassword(ap_password).Value)
                command3 = 'cd /tmp ; rm -rf {}'.format(unique_dir_name)
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'reboot started')
                (stdin, stdout, stderr) = s.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 1 executed')
                (stdin2, stdout2, stderr2) = s.exec_command(command2)
                exit_status = stdout2.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 2 executed')

                output = ''
                errors = ''
                for line in stdout2.readlines():
                    output += line
                for line in stderr2.readlines():
                    errors += line
                if stdout2.channel.recv_exit_status() != 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'AP Reboot failed on address {}: '.format(
                                                                    context.resource.address) + errors)
                    raise Exception('Error executing Script: ' + errors)
                else:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'AP Reboot Executed.')
                (stdin3, stdout3, stderr3) = s.exec_command(command3)
                exit_status = stdout3.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'command 3 executed: removed wlan testing repo for AP: {}'.format(context.resource.name))


                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Waiting two minutes for reboot to complete...')
                time.sleep(120)
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Reboot complete!')
                s.close()

    def pduPowerCycle(self, context):
        res_id = context.reservation.reservation_id
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting PDU Power Cycle on {}.'.format(context.resource.name))
                self.powerThisAP(context, cmd="off")
                self.powerThisAP(context, cmd="on")
                api_session.WriteMessageToReservationOutput(res_id, 'PDU Power cycle completed ')


    def checkUpTime(self, context):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Finding uptime of {}.'.format(context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                terminal_ip = api_session.GetAttributeValue(context.resource.name, "{}.ip".format(cloudshell_model_name)).Value
                terminal_user = api_session.GetAttributeValue(context.resource.name, "{}.uname".format(cloudshell_model_name)).Value
                terminal_pass = api_session.GetAttributeValue(context.resource.name, "{}.passkey".format(cloudshell_model_name)).Value
                terminal_pass = api_session.DecryptPassword(terminal_pass).Value

                ap_user = api_session.GetAttributeValue(context.resource.name, "{}.User".format(cloudshell_model_name)).Value
                ap_password = api_session.GetAttributeValue(context.resource.name, "{}.Password".format(cloudshell_model_name)).Value
                ap_tty = api_session.GetAttributeValue(context.resource.name, "{}.jumphost_tty".format(cloudshell_model_name)).Value
                ap_ip = api_session.GetResourceDetails(context.resource.name).Address
                ap_jumphost = api_session.GetAttributeValue(context.resource.name, "{}.jumphost".format(cloudshell_model_name)).Value
                ap_port = api_session.GetAttributeValue(context.resource.name, "{}.port".format(cloudshell_model_name)).Value
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=terminal_ip, username=terminal_user,
                          password=terminal_pass)
                unique_dir_name = res_id + ap_tty[-1]
                command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x ap_tools.py'.format(
                    unique_dir_name, unique_dir_name)
                command2 = 'cd /tmp/{}/wlan-testing/tools && python3 ap_tools.py --host {} --jumphost {} --tty {} --port {} --username {} --password {} --cmd "uptime"'.format(
                    unique_dir_name, ap_ip, ap_jumphost, ap_tty, ap_port, ap_user,
                    api_session.DecryptPassword(ap_password).Value)
                command3 = 'cd /tmp ; rm -rf {}'.format(unique_dir_name)
                (stdin, stdout, stderr) = s.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 1 executed')
                (stdin2, stdout2, stderr2) = s.exec_command(command2)
                exit_status = stdout2.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'command 2 executed')

                output = ''
                errors = ''
                for line in stdout2.readlines():
                    output += line
                for line in stderr2.readlines():
                    errors += line
                if stdout2.channel.recv_exit_status() != 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'Finding uptime failed on address {}: '.format(
                                                                    context.resource.address) + errors)
                    raise Exception('Error executing Script: ' + errors)
                else:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                'Finding uptime complete')
                (stdin3, stdout3, stderr3) = s.exec_command(command3)
                exit_status = stdout3.channel.recv_exit_status()
                if exit_status == 0:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'command 3 executed: removed wlan testing repo for AP: {}'.format(context.resource.name))
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Uptime output below:')
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,output)
                s.close()



