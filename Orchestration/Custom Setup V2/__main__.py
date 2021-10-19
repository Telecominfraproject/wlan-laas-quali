from cloudshell.workflow.orchestration.sandbox import Sandbox
from cloudshell.workflow.orchestration.setup.default_setup_orchestrator import DefaultSetupWorkflow
from cloudshell.api.cloudshell_api import InputNameValue
from multiprocessing.pool import ThreadPool


def helm_install(sandbox, components):
    for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Services:
        if each.ServiceName == 'Helm Service V2':
            chart_version = InputNameValue(Name='chart_version', Value=sandbox.global_inputs['Chart Version'])
            owgw_version = InputNameValue(Name='owgw_version', Value=sandbox.global_inputs['owgw Version'])
            owsec_version = InputNameValue(Name='owsec_version', Value=sandbox.global_inputs['owsec Version'])
            owfms_version = InputNameValue(Name='owfms_version', Value=sandbox.global_inputs['owfms Version'])
            owgwui_version = InputNameValue(Name='owgwui_version', Value=sandbox.global_inputs['owgwui Version'])
            owprov_version = InputNameValue(Name='owprov_version', Value=sandbox.global_inputs['owprov Version'])
            owprovui_version = InputNameValue(Name='owprovui_version', Value=sandbox.global_inputs['owprovui Version'])
            sandbox.automation_api.ExecuteCommand(sandbox.id, each.Alias, "Service", 'helm_install', [chart_version,
                                                                                                      owgw_version,
                                                                                                      owsec_version,
                                                                                                      owfms_version,
                                                                                                      owgwui_version,
                                                                                                      owprov_version,
                                                                                                      owprovui_version])

def ap_redirect(sandbox, components):
    for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
        if each.ResourceModelName == 'ApV2':
            namespace = InputNameValue(Name='namespace', Value=sandbox.id.split('-')[0])
            sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'apRedirect', [namespace])

def power_off_other_aps(sandbox, components):
    for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
        if each.ResourceModelName == 'ApV2':
            cmd = InputNameValue(Name='cmd', Value='off')
            sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'powerOtherAPs', [cmd])

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

     #   res = api.ExecuteResourceConnectedCommand(res_id, ap_res.Name,"Run_Script",inputs)

    except Exception as e:
        api.WriteMessageToReservationOutput(sandbox.id, e.message)


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

            except Exception as e:
                sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, 'Failed: '+ e.message)
                sandbox.report_error("Failed to run script, Error is: " + e.message, raise_error=True)
    else:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "No Terminal Server in reservation")

sandbox = Sandbox()

DefaultSetupWorkflow().register(sandbox)
sandbox.workflow.add_to_provisioning(helm_install, [])
sandbox.workflow.on_provisioning_ended(ap_redirect, [])
sandbox.workflow.on_provisioning_ended(execute_terminal_script, [])
sandbox.workflow.on_provisioning_ended(power_off_other_aps, [])

sandbox.execute_setup()