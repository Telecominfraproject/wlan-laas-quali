from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext
from data_model import *  # run 'shellfoundry generate' to generate data model classes
import time
from datetime import datetime, timedelta
import pytz
from cloudshell.shell.core.session.logging_session import LoggingSessionContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.core.context.error_handling_context import ErrorHandlingContext
import paramiko
global default_perfecto_url
default_perfecto_url = "tip"





class PhoneDriver (ResourceDriverInterface):

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

        '''
        resource = Phone.create_from_context(context)
        resource.vendor = 'specify the shell vendor'
        resource.model = 'specify the shell model'

        port1 = ResourcePort('Port 1')
        port1.ipv4_address = '192.168.10.7'
        resource.add_sub_resource('1', port1)

        return resource.create_autoload_details()
        '''

        resource = Phone.create_from_context(context)

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

    def perfecto_phone_reserve(self,context,perfectoURL, securityToken, cancellation_context):

        def get_phone_reservation_times(reservation_time=6, start_offset=30):
            tz_pst = pytz.timezone('US/Pacific')
            now = datetime.now(tz_pst)
            start_time = now + timedelta(seconds=start_offset)
            end_time = now + timedelta(hours=reservation_time)
            start_string = start_time.strftime("%d.%m.%Y %H:%M:%S")
            end_string = end_time.strftime("%d.%m.%Y %H:%M:%S")
            return start_string, end_string

        try:
            with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
                with CloudShellSessionContext(context) as api_session:

                    logger.info("Start Perfecto Phone Reservation Script")

                    username = context.resource.attributes["{}.User".format(context.resource.model)]
                    password = context.resource.attributes["{}.Password".format(context.resource.model)]
                    phone_serial = context.resource.attributes["{}.serial".format(context.resource.model)]
                    if perfectoURL=="":
                        perfectoURL=default_perfecto_url
                    res_id = context.reservation.reservation_id

                    duration = api_session.GetReservationRemainingTime(reservationId=res_id).RemainingTimeInMinutes / 60

                    start_string, end_string = get_phone_reservation_times(duration)
                    api_session.WriteMessageToReservationOutput(res_id,"Phone reserved from: "+start_string)
                    api_session.WriteMessageToReservationOutput(res_id, "Phone reserved to: "+end_string)
                    s = paramiko.SSHClient()
                    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    s.connect(hostname=context.resource.address, username=username,
                              password=api_session.DecryptPassword(password).Value)
                    command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch modify-interop-tools --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x phone_tools.py'.format(
                        res_id, res_id)
                    command2 = 'cd /tmp/{}/wlan-testing/tools && python3 phone_tools.py --startTime {} --endTime {} --deviceId {} --securityToken {} --perfectoURL {} --action {} --reservationNumber {}'.format(
                        res_id, "'"+start_string+"'", "'"+end_string+"'", phone_serial,securityToken,perfectoURL, "reserve","0")
                    command3 = 'cd /tmp ; rm -rf {}'.format(res_id)

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
                    for line in stdout2.readlines():
                        output += line
                    # set reservationNumber in Perfecto for the phone
                    api_session.SetAttributeValue(context.resource.name, "Phone.reservationNumber", output.split("\n")[-2])
                    for line in stderr2.readlines():
                        errors += line
                    if stdout2.channel.recv_exit_status() != 0:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'Phone  reservation failed on {}: '.format(
                                                                        context.resource.address) + errors)
                        raise Exception('Error executing Script: ' + errors)
                    else:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'Perfecto Phone reservation Complete.')
                    (stdin3, stdout3, stderr3) = s.exec_command(command3)
                    s.close()

                    return output

        except Exception as e:
            logger.info("Error executing Script: {}".format(e.message))
            raise Exception('Error executing Script: ' + e.message)

    def phone_reboot(self,context, cancellation_context):

        try:
            with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
                with CloudShellSessionContext(context) as api_session:

                    logger.info("Start Perfecto Phone Reservation Script")

                    res_id = context.reservation.reservation_id


                    username = context.resource.attributes["{}.User".format(context.resource.model)]
                    password = context.resource.attributes["{}.Password".format(context.resource.model)]
                    phone_os = context.resource.attributes["{}.OS".format(context.resource.model)]
                    device_name = context.resource.attributes["{}.model".format(context.resource.model)]
                    #Device string format "{\"Galaxy S9\":\"Android\",\"Galaxy S20\":\"Android\"}"
                    device_string = "\"{\\\"" + device_name + "\\\":\\\"" + phone_os + "\\\"}" + "\""

                    duration = api_session.GetReservationRemainingTime(reservationId=res_id).RemainingTimeInMinutes / 60

                    api_session.WriteMessageToReservationOutput(res_id,"Phone reboot on: "+device_name)
                    s = paramiko.SSHClient()
                    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    s.connect(hostname=context.resource.address, username=username,
                              password=api_session.DecryptPassword(password).Value)
                    command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch modify-interop-tools --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x phone_tools.py'.format(
                        res_id, res_id)
                    command2 = 'cd /tmp/{}/wlan-testing/tools && python3 interop_tools.py --all_devices {}'.format(res_id,device_string)
                    command3 = 'cd /tmp ; rm -rf {}'.format(res_id)

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
                    for line in stdout2.readlines():
                        output += line

                    for line in stderr2.readlines():
                        errors += line
                    if stdout2.channel.recv_exit_status() != 0:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'Starting Phone  reboot on {}: '.format(
                                                                        device_name) + errors)
                        raise Exception('Error executing Script: ' + errors)
                    else:
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                    'Phone reboot complete')
                    (stdin3, stdout3, stderr3) = s.exec_command(command3)
                    s.close()

                    return output

        except Exception as e:
            logger.info("Error executing Script: {}".format(e.message))
            raise Exception('Error executing Script: ' + e.message)




    def perfecto_phone_unreserve(self,context,perfectoURL, securityToken, cancellation_context):

        try:
            with LoggingSessionContext(context) as logger, ErrorHandlingContext(logger):
                with CloudShellSessionContext(context) as api_session:

                    logger.info("Start Perfecto Phone Unreservation Script")

                    username = context.resource.attributes["{}.User".format(context.resource.model)]
                    password = context.resource.attributes["{}.Password".format(context.resource.model)]
                    phone_serial = context.resource.attributes["{}.serial".format(context.resource.model)]
                    reservationNumber = context.resource.attributes["{}.reservationNumber".format(context.resource.model)]
                    if reservationNumber == "":
                        api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,"Unable to unreserve: (might not have been reserved): " + context.resource.name)
                    else:
                        if perfectoURL=="":
                            perfectoURL=default_perfecto_url
                        res_id = context.reservation.reservation_id
                        s = paramiko.SSHClient()
                        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        s.connect(hostname=context.resource.address, username=username,
                                  password=api_session.DecryptPassword(password).Value)
                        command = 'cd /tmp ; mkdir {} ; cd {} ; git clone --single-branch --branch master --depth 1 https://github.com/Telecominfraproject/wlan-testing.git; cd wlan-testing && git checkout master && cd tools && chmod +x phone_tools.py'.format(
                            res_id, res_id)
                        command2 = 'cd /tmp/{}/wlan-testing/tools && python3 phone_tools.py --startTime {} --endTime {} --deviceId {} --securityToken {} --perfectoURL {} --action {} --reservationNumber {}'.format(
                            res_id, "0", "0", phone_serial,securityToken,perfectoURL, "unreserve",reservationNumber)
                        command3 = 'cd /tmp ; rm -rf {}'.format(res_id)

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
                        for line in stdout2.readlines():
                            output += line
                        for line in stderr2.readlines():
                            errors += line
                        if stdout2.channel.recv_exit_status() != 0:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                        'Phone  unreservation failed on {}: '.format(
                                                                            context.resource.address) + errors)
                            raise Exception('Error executing Script: ' + errors)
                        else:
                            api_session.WriteMessageToReservationOutput(context.reservation.reservation_id,
                                                                        'Perfecto Phone unreservation Complete.')

                        api_session.SetAttributeValue(resourceFullPath=context.resource.name, attributeName="Phone.reservationNumber",attributeValue="")

                        (stdin3, stdout3, stderr3) = s.exec_command(command3)
                        s.close()

                        return output

        except Exception as e:
            logger.info("Error executing Script: {}".format(e.message))
            raise Exception('Error executing Script: ' + e.message)
    # <editor-fold desc="Orchestration Save and Restore Standard">

    # </editor-fold>
