from cloudshell.workflow.orchestration.sandbox import Sandbox
from cloudshell.workflow.orchestration.setup.default_setup_orchestrator import DefaultSetupWorkflow
from cloudshell.api.cloudshell_api import InputNameValue, AttributeNameValue
from multiprocessing.pool import ThreadPool
import time

def rename_sandbox(sandbox,components):
    sandbox_name = sandbox.automation_api.GetReservationDetails(reservationId=sandbox.id).ReservationDescription.Name
    for resources in sandbox.automation_api.GetReservationDetails(reservationId=sandbox.id).ReservationDescription.Resources:
        if resources.ResourceModelName == "ApV2":
            res_name = sandbox_name + " : " + resources.Name.split("-")[-1]
            break
    sandbox.automation_api.UpdateReservationName(reservationId=sandbox.id, name=res_name)


def helm_install(sandbox, components):
    try:
        namespace = sandbox.global_inputs['Optional Existing SDK Namespace']
        if namespace == '':
            for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Services:
                if each.ServiceName == 'Helm Service V2':

                    namespace = AttributeNameValue(Name='Namespace', Value=sandbox.id.split('-')[0])
                    sandbox.automation_api.SetServiceAttributesValues(sandbox.id, each.ServiceName, [namespace])

                    chart_version = InputNameValue(Name='chart_version', Value=sandbox.global_inputs['Chart Version'])
                    owgw_version = InputNameValue(Name='owgw_version', Value=sandbox.global_inputs['owgw Version'])
                    owsec_version = InputNameValue(Name='owsec_version', Value=sandbox.global_inputs['owsec Version'])
                    owfms_version = InputNameValue(Name='owfms_version', Value=sandbox.global_inputs['owfms Version'])
                    owgwui_version = InputNameValue(Name='owgwui_version', Value=sandbox.global_inputs['owgwui Version'])
                    owprov_version = InputNameValue(Name='owprov_version', Value=sandbox.global_inputs['owprov Version'])
                    owprovui_version = InputNameValue(Name='owprovui_version', Value=sandbox.global_inputs['owprovui Version'])
                    owanalytics_version = InputNameValue(Name='owanalytics_version', Value=sandbox.global_inputs['owanalytics Version'])
                    owsub_version = InputNameValue(Name='owsub_version', Value=sandbox.global_inputs['owsub Version'])
                    owrrm_version = InputNameValue(Name='owrrm_version', Value=sandbox.global_inputs['owrrm Version'])
                    sandbox.automation_api.ExecuteCommand(sandbox.id, each.Alias, "Service", 'helm_install', [chart_version,
                                                                                                              owgw_version,
                                                                                                              owsec_version,
                                                                                                              owfms_version,
                                                                                                              owgwui_version,
                                                                                                              owprov_version,
                                                                                                              owprovui_version,owanalytics_version,owsub_version,owrrm_version])
        else:
            sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, 'Using Existing SDK')

    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "Failure in Helm Install: " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)


def ap_redirect(sandbox, components):
    try:
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == 'ApV2':
                sdk_namespace = sandbox.global_inputs['Optional Existing SDK Namespace']
                if sdk_namespace != '':
                    namespace = InputNameValue(Name='namespace', Value=sdk_namespace)
                    sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id,
                                                                           'Attempting AP Redirect to namespace: {}'.format(sdk_namespace))
                else:
                    namespace = InputNameValue(Name='namespace', Value=sandbox.id.split('-')[0])
                    sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id,
                                                                           'Attempting AP Redirect to namespace: {}'.format(sandbox.id.split('-')[0]))
                sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'apRedirect', [namespace], printOutput=True)
    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "AP Redirect Failed: " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

def power_off_other_aps(sandbox, components):
    try:
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == 'ApV2':
                cmd = InputNameValue(Name='cmd', Value='off')
                sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'powerOtherAPs', [cmd])
    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "Power Off Other AP's failed: " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

def factory_reset(api,res_id,ap_res,terminal_server):

    try:
        ap_user = api.GetAttributeValue(ap_res.Name, "{}.uname".format(ap_res.ResourceModelName)).Value
        ap_password = api.GetAttributeValue(ap_res.Name,"{}.passkey".format(ap_res.ResourceModelName)).Value
        ap_tty = api.GetAttributeValue(ap_res.Name, "{}.jumphost_tty".format(ap_res.ResourceModelName)).Value
        ap_ip = api.GetResourceDetails(ap_res.Name).Address
        ap_jumphost = api.GetAttributeValue(ap_res.Name, "{}.jumphost".format(ap_res.ResourceModelName)).Value
        ap_port = api.GetAttributeValue(ap_res.Name, "{}.port".format(ap_res.ResourceModelName)).Value

        inputs = [InputNameValue("ap_user", ap_user),
                  InputNameValue("ap_password", ap_password),
                  InputNameValue("ap_tty", ap_tty),
                  InputNameValue("ap_ip", ap_ip),
                  InputNameValue("ap_jumphost", ap_jumphost),
                  InputNameValue("ap_port", ap_port)]

        api.WriteMessageToReservationOutput(sandbox.id, "Running on {}".format(ap_res.Name))
        res = api.ExecuteCommand(res_id,terminal_server,'Resource',"Run_Ap_Factory_Reset",inputs,printOutput = True)
        api.WriteMessageToReservationOutput(sandbox.id, "Sleep timer started after AP Factory Reset for 3 minutes...")
        time.sleep(180)
        api.WriteMessageToReservationOutput(sandbox.id, "Sleep timer ended")


     #   res = api.ExecuteResourceConnectedCommand(res_id, ap_res.Name,"Run_Script",inputs)

    except Exception as e:
        api.WriteMessageToReservationOutput(sandbox.id, 'Failed to Factory Reset {}'.format(ap_res.Name))
        raise Exception('Failed to Factory Reset {}'.format(ap_res.Name))
        sandbox.automation_api.EndReservation(sandbox.id)



def execute_terminal_script(sandbox, components):

    resources = sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources
    #Find The terminal Server resource
    terminal_server = None
    for resource in resources:
        if resource.ResourceModelName == "Controller Vm":
            terminal_server = resource.Name
            break

    if terminal_server:
    #Find all Access points resources in the reservation
        ap_resources =  [resource for resource in resources
                     if resource.ResourceModelName == "ApV2"]

        if ap_resources:
            sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, 'Running Factory Reset on all Access Points')
            try:
                pool = ThreadPool(len(ap_resources))

                async_results = [pool.apply_async(factory_reset, (sandbox.automation_api, sandbox.id,ap_res,terminal_server)) for ap_res in
                    ap_resources]

                pool.close()
                pool.join()

                for i in range(len(ap_resources)):
                    if not async_results[i].successful():
                        raise Exception('Caught exception in Factory Reset')

            except Exception as e:
                sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, 'Failed: '+ e.message)
                sandbox.automation_api.EndReservation(sandbox.id)

    else:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "No Terminal Server in reservation")


def check_lab_type(sandbox):
    flag = False
    ap_found = False
    try:
        for resource in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if resource.ResourceModelName == 'ApV2':
                details = sandbox.automation_api.GetResourceDetails(resource.Name)
                ap_found= True
                break

        if ap_found:
            for attribute in details.ResourceAttributes:
                if attribute.Name == "Lab Type":
                    return_val = attribute.Value
                    break
        else:
            raise Exception("Failed: No AP resource in the blueprint")

    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

    if return_val in ["Basic", "Advanced"]:
        flag = True

    return flag


sandbox = Sandbox()
DefaultSetupWorkflow().register(sandbox)
if check_lab_type(sandbox):
    sandbox.workflow.add_to_provisioning(rename_sandbox, [])
sandbox.workflow.add_to_provisioning(helm_install, [])
sandbox.workflow.on_provisioning_ended(ap_redirect, [])
sandbox.workflow.on_provisioning_ended(execute_terminal_script, [])
if check_lab_type(sandbox):
    sandbox.workflow.on_provisioning_ended(power_off_other_aps, [])

sandbox.execute_setup()