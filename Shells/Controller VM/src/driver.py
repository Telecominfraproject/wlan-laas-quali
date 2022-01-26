from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext

from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from data_model import *
import paramiko


class ControllerVmDriver (ResourceDriverInterface):

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

        resource = ControllerVm.create_from_context(context)
        # resource.vendor = 'specify the shell vendor'
        # resource.model = 'specify the shell model'

        for i in range(10):
            port = ResourcePort('connector' + str(i))
            resource.add_sub_resource(str(i), port)

        return resource.create_autoload_details()

    # </editor-fold>
    #def Run_Script_Test(self,context,ports):
    #    return "Hello"

    def Run_Ap_Factory_Reset(self,context,ap_user,ap_password,ap_tty,ap_ip,ap_jumphost,ap_port,cancellation_context):
        """
        Discovers the resource structure and attributes.
        :param ResourceCommandContext context: the context the command runs on
        :param str ap_user
        :param str ap_password
        :param str ap_name
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        try:
            with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
                with CloudShellSessionContext(context) as api_session:

                    logger.info("Start AP Factory Reset Script")

                    username = context.resource.attributes["{}.User".format(context.resource.model)]
                    password = context.resource.attributes["{}.Password".format(context.resource.model)]

                    url = context.resource.attributes["{}.url".format(context.resource.model)]
                    logger.info("url: {}".format(url))

                    res_id = context.reservation.reservation_id
                    FQDN = res_id.split('-')[0]

                    s = paramiko.SSHClient()
                    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    s.connect(hostname=context.resource.address, username=username, password=api_session.DecryptPassword(password).Value)
                    command = 'cd /tmp && git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x ap_tools.py'

                    command2 = 'cd /tmp/wlan-testing/tools && python3 ap_tools.py --host {} --jumphost {} --tty {} --port {} --username {} --password {} --cmd "jffs2reset -y -r"'.format(
                              ap_ip, ap_jumphost, ap_tty, ap_port, ap_user, api_session.DecryptPassword(ap_password).Value)

                    (stdin, stdout, stderr) = s.exec_command(command)
                    (stdin2, stdout2, stderr2) = s.exec_command(command2)

                    output = ''
                    errors = ''
                    for line in stdout2.readlines():
                        output += line
                    for line in stderr2.readlines():
                        errors += line
                    if stdout2.channel.recv_exit_status() != 0:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'AP Factory Reset failed on {}: '.format(context.resource.address) + errors)
                        raise Exception('Error executing Script: ' + errors)
                    else:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'AP Factory Reset Complete.')
                    s.close()

                    return output

        except Exception as e:
            logger.info("Error executing Script: {}".format(e.message))
            raise Exception('Error executing Script: ' + e.message)


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