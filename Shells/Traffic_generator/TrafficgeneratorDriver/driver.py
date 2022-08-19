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

PDU_SCRIPT_NAME = 'pdu_v3.py'


class TrafficgeneratorDriver (ResourceDriverInterface):

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

        resource = Trafficgenerator.create_from_context(context)
        # resource.vendor = 'specify the shell vendor'
        # resource.model = 'specify the shell model'

        port = ResourcePort('connector')
        resource.add_sub_resource(0, port)

        return resource.create_autoload_details()

        '''
        resource = Trafficgenerator.create_from_context(context)
        resource.vendor = 'specify the shell vendor'
        resource.model = 'specify the shell model'

        port1 = ResourcePort('Port 1')
        port1.ipv4_address = '192.168.10.7'
        resource.add_sub_resource('1', port1)

        return resource.create_autoload_details()
        '''
        #return AutoLoadDetails([], [])

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

      # See below an example implementation, here we use jsonpickle for serialization,
      # to use this sample, you'll need to add jsonpickle to your requirements.txt file
      # The JSON schema is defined at:
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/saved_artifact_info.schema.json
      # You can find more information and examples examples in the spec document at
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/save%20%26%20restore%20standard.md
      '''
            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.

            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.
            identifier = created_date.strftime('%y_%m_%d %H_%M_%S_%f')

            orchestration_saved_artifact = OrchestrationSavedArtifact('REPLACE_WITH_ARTIFACT_TYPE', identifier)

            saved_artifacts_info = OrchestrationSavedArtifactInfo(
                resource_name="some_resource",
                created_date=created_date,
                restore_rules=OrchestrationRestoreRules(requires_same_resource=True),
                saved_artifact=orchestration_saved_artifact)

            return OrchestrationSaveResult(saved_artifacts_info)
      '''
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
        '''
        # The saved_details JSON will be defined according to the JSON Schema and is the same object returned via the
        # orchestration save function.
        # Example input:
        # {
        #     "saved_artifact": {
        #      "artifact_type": "REPLACE_WITH_ARTIFACT_TYPE",
        #      "identifier": "16_08_09 11_21_35_657000"
        #     },
        #     "resource_name": "some_resource",
        #     "restore_rules": {
        #      "requires_same_resource": true
        #     },
        #     "created_date": "2016-08-09T11:21:35.657000"
        #    }

        # The example code below just parses and prints the saved artifact identifier
        saved_details_object = json.loads(saved_details)
        return saved_details_object[u'saved_artifact'][u'identifier']
        '''
        pass

    def powerThisLF(self, context, cmd='on'):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                resource = Trafficgenerator.create_from_context(context)
                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to power {} {}.'.format(cmd, context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                for resource in api_session.GetReservationDetails(reservationId=res_id).ReservationDescription.Resources:
                    if resource.ResourceModelName == "Controller Vm":
                        terminal_ip = api_session.GetResourceDetails(resourceFullPath=resource.Name).Address
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
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'command 1 executed')

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
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, '{} Powered {}.'.format(context.resource.name, cmd))

                (stdin3, stdout3, stderr3) = s.exec_command(command3)
                s.close()

    def safepowerThisLF(self, context, cmd='on'):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to safe power {} {}.'.format(cmd, context.resource.name))

                if cmd=="off":
                    cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                    lf_ip = api_session.GetResourceDetails(context.resource.name).Address
                    lf_user = api_session.GetAttributeValue(context.resource.name,
                                                            "{}.User".format(cloudshell_model_name)).Value
                    lf_pass = api_session.GetAttributeValue(context.resource.name,
                                                            "{}.Password".format(cloudshell_model_name)).Value
                    lf_pass = api_session.DecryptPassword(lf_pass).Value
                    s = paramiko.SSHClient()
                    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    s.connect(hostname=lf_ip, username=lf_user,password=lf_pass)
                    command = "init 0"
                    s.exec_command(command)
                    s.close()
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'init 0 executed')
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Sleep Timer started for a minute')
                    time.sleep(60)
                    self.powerThisLF(context,cmd = "off")
                elif cmd=="on":
                    self.powerThisLF(context,cmd= "on")
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Sleep Timer started for a minute for LF to turn on')
                    time.sleep(60)
                else:
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Invalid cmd input')

    def rebootLF(self, context):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting to reboot {}.'.format(context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                lf_ip = api_session.GetResourceDetails(context.resource.name).Address
                lf_user = api_session.GetAttributeValue(context.resource.name, "{}.User".format(cloudshell_model_name)).Value
                lf_pass = api_session.GetAttributeValue(context.resource.name, "{}.Password".format(cloudshell_model_name)).Value
                lf_pass = api_session.DecryptPassword(lf_pass).Value
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=lf_ip, username=lf_user,
                          password=lf_pass)
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=lf_ip, username=lf_user,
                          password=lf_pass)

                command = "reboot"
                s.exec_command(command)
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,'reboot started')
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Waiting two minutes for reboot to complete...')
                time.sleep(120)
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id, 'Reboot complete!')
                s.close()

    def safepduPowerCycle(self, context):
        res_id = context.reservation.reservation_id
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting safe PDU Power Cycle on {}.'.format(context.resource.name))
                self.safepowerThisLF(context, cmd="off")
                self.safepowerThisLF(context, cmd="on")
                api_session.WriteMessageToReservationOutput(res_id, 'Safe PDU Power cycle completed ')
                
    def pduPowerCycle(self, context):
        res_id = context.reservation.reservation_id
        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Attempting PDU Power Cycle on {}.'.format(context.resource.name))
                self.powerThisLF(context, cmd="off")
                self.powerThisLF(context, cmd="on")
                api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                            'Sleep Timer started for a minute for LF to turn on')
                time.sleep(60)
                api_session.WriteMessageToReservationOutput(res_id, 'PDU Power cycle completed ')


    def checkUpTime(self, context):
        res_id = context.reservation.reservation_id

        with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
            with CloudShellSessionContext(context) as api_session:

                api_session.WriteMessageToReservationOutput(res_id, 'Finding uptime of {}.'.format(context.resource.name))
                cloudshell_model_name = api_session.GetResourceDetails(context.resource.name).ResourceModelName
                lf_ip = api_session.GetResourceDetails(context.resource.name).Address
                lf_user = api_session.GetAttributeValue(context.resource.name, "{}.User".format(cloudshell_model_name)).Value
                lf_pass = api_session.GetAttributeValue(context.resource.name, "{}.Password".format(cloudshell_model_name)).Value
                lf_pass = api_session.DecryptPassword(lf_pass).Value
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(hostname=lf_ip, username=lf_user,
                          password=lf_pass)
                command = "uptime"
                (stdin, stdout, stderr)=s.exec_command(command)
                for line in stdout.readlines():
                    api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,line)
                s.close()


    # </editor-fold>
