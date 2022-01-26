import os
import shutil
import subprocess
import tempfile
import paramiko
import requests

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
PDU_SCRIPT_NAME = 'pdu_automation.py'

# Vars for ap redirect
SCRIPT_URL = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-change-ap-redirector.sh'
SCRIPT_URL2 = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-library.sh'
SCRIPT_URL3 = 'https://raw.githubusercontent.com/Telecominfraproject/wlan-pki-cert-scripts/master/digicert-config.sh'
URL_TEMPLATE = 'gw-ucentral-{}.cicd.lab.wlan.tip.build'


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


class ApDriver (ResourceDriverInterface):

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

        resource = Ap.create_from_context(context)
        # resource.vendor = 'specify the shell vendor'
        # resource.model = 'specify the shell model'

        for i in range(2):
            port = ResourcePort('connector' + str(i))
            resource.add_sub_resource(str(i), port)

        return resource.create_autoload_details()

        # return AutoLoadDetails([], [])

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

                resource = Ap.create_from_context(context)
                #redirect_url = URL_TEMPLATE.format(context.reservation.reservation_id.split('-')[0])
                redirect_url = URL_TEMPLATE.format(namespace)

                working_dir = tempfile.mkdtemp()

                script_path = os.path.join(working_dir, 'digicert-change-ap-redirector.sh')
                script_path2 = os.path.join(working_dir, 'digicert-library.sh')
                script_path3 = os.path.join(working_dir, 'digicert-config.sh')

                response = requests.get(SCRIPT_URL)
                response2 = requests.get(SCRIPT_URL2)
                response3 = requests.get(SCRIPT_URL3)

                temp = str(response.content.decode('utf-8'))
                fout = open(script_path, "wt")
                fout.write(temp)
                fout.close()
                os.chmod(script_path, 0o777)

                temp = str(response2.content.decode('utf-8'))
                fout = open(script_path2, "wt")
                fout.write(temp)
                fout.close()
                os.chmod(script_path2, 0o777)

                temp = str(response3.content.decode('utf-8'))
                fout = open(script_path3, "wt")
                fout.write(temp)
                fout.close()
                os.chmod(script_path3, 0o777)

                result = subprocess.Popen('dos2unix digicert-change-ap-redirector.sh', cwd=working_dir, shell=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, errors = result.communicate(' ')
                if errors:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, repr(errors))

                result = subprocess.Popen('dos2unix digicert-library.sh', cwd=working_dir, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                output, errors = result.communicate(' ')
                if errors:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, repr(errors))

                result = subprocess.Popen('dos2unix digicert-config.sh', cwd=working_dir, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                output, errors = result.communicate(' ')
                if errors:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, repr(errors))

                os.environ['DIGICERT_API_KEY'] = api_session.DecryptPassword(
                    resource.attributes['Digicert API Key']).Value

                result = subprocess.Popen(
                    './digicert-change-ap-redirector.sh {} {}'.format(resource.attributes['Ap.serial'], redirect_url),
                    cwd=working_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, errors = result.communicate(' ')
                if errors:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, repr(errors))

                shutil.rmtree(working_dir, onerror=onerror)

                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, "Digicert AP Redirect Successful.")

    def powerOtherAPs(self, context, cmd='on'):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                other_aps = []

                for each in api_session.FindResources(resourceModel='Ap').Resources:
                    if context.resource.name != each.Name and context.resource.name.split(' - ')[1] == each.Name .split(' - ')[1]:
                        other_aps.append(each)

                if other_aps:
                    for each in other_aps:
                        terminal_ip = api_session.GetResourceDetails(each.Name).Address
                        terminal_user = context.resource.attributes["{}.uname".format(each.Model)]
                        terminal_pass = context.resource.attributes["{}.passkey".format(each.Model)]
                        #terminal_pass = api_session.DecryptPassword(terminal_pass).Value
                        hostname = context.resource.attributes["{}.PDU Host".format(each.Model)]
                        username = context.resource.attributes["{}.PDU User".format(each.Model)]
                        password = context.resource.attributes["{}.PDU Password".format(each.Model)]
                        #password = api_session.DecryptPassword(password).Value
                        port = context.resource.attributes["{}.PDU Port".format(each.Model)]

                        s = paramiko.SSHClient()
                        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        s.connect(hostname=terminal_ip, username=terminal_user,
                                  password=terminal_pass)
                        command = "cd /tmp && git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing/tools && python3 {} --host {} --user {} --password {} --action {} --port '{}'; cd /tmp && rm -f -r wlan-testing".format(
                            PDU_SCRIPT_NAME, hostname, username, password, cmd, port)

                        (stdin, stdout, stderr) = s.exec_command(command)
                        output = ''
                        errors = ''
                        for line in stdout.readlines():
                            output += line
                        for line in stderr.readlines():
                            errors += line
                        if errors != '':
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, errors)
                        else:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                        '{} Powered {}.'.format(each.Name, cmd))
                        s.close()

                else:
                    api_session.WriteMessageToReservationOutput(res_id, 'No APs to power {}.'.format(cmd))
