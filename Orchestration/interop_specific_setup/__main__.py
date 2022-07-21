from cloudshell.workflow.orchestration.sandbox import Sandbox
from cloudshell.workflow.orchestration.setup.default_setup_orchestrator import DefaultSetupWorkflow
from cloudshell.api.cloudshell_api import InputNameValue, AttributeNameValue
from multiprocessing.pool import ThreadPool
import time


def add_reserved_resources(sandbox,components):

    # Iterating through all reservation Inputs to find Phone Input and AP Input
    try:
        for inp in sandbox.automation_api.GetReservationInputs(reservationId=sandbox.id).GlobalInputs:
            if inp.ParamName == "Phone ID(s)":
                phones_in_res = inp.Value
            if inp.ParamName == "AP ID(s)":
                aps_in_res = inp.Value
            if inp.ParamName == "Include a LANForge?":
                inc_lanforge = inp.Value

        e_msg = ""
        if phones_in_res== "":
            e_msg += "No input given for phone "

        if aps_in_res == "":
            e_msg += "No input given for aps"

        if e_msg != "":
            raise Exception(e_msg)


    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

    sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "Phones in reservation: " + phones_in_res)
    sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "APs in reservation: " + aps_in_res)

    # Generate possible attributes

    def generate_poss_attributes(resource_model_name, attribute_name):
        poss_inp = ""
        for resource in sandbox.automation_api.FindResources(resourceFamily="CS_GenericResource",
                                              resourceModel=resource_model_name).Resources:
            for attribute in sandbox.automation_api.GetResourceDetails(resource.Name).ResourceAttributes:
                if attribute.Name == attribute_name:
                    poss_inp += attribute.Value + ","
        return poss_inp[:-1]

    poss_inp_phone = generate_poss_attributes("Phone", "Phone.Phone_ID")
    poss_inp_aps = generate_poss_attributes("ApV2", "ApV2.Ap_ID")



    # Function to validate input to Blueprint
    def validate_input(inp, possible_inp):
        flag = False
        try:
            if len(set(inp.split(",")))!=len(inp.split(",")):
                raise Exception("ERROR: Repeated ID's in input")
            if len(set(inp.split(",")))>len(possible_inp.split(",")):
                raise Exception("ERROR: Too many Input ID's")
            if all(i.isdigit() for i in inp.split(",")):
                if set(inp.split(",")).issubset(possible_inp.split(",")):
                    flag = True
                else:
                    raise Exception("ERROR: Invalid ID(s) in input")
            else:
                raise Exception("ERROR: Input string not comma separated / string does not have digits, Please check input")
        except Exception as e:
            sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, e.message)
            sandbox.automation_api.EndReservation(sandbox.id)
        return flag


    #Validating Input
    #print(validate_input(phones_in_res,poss_inp_phone))
    #print(validate_input(aps_in_res,poss_inp_aps))
    def get_center_position(sandbox):
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == "Controller Vm":
                break

        for position in sandbox.automation_api.GetReservationResourcesPositions(reservationId=sandbox.id).ResourceDiagramLayouts:
            if position.ResourceName == each.Name:
                return position.X, position.Y

    def get_all_reservations(r_name,sandbox,family_name_list = ["CS_GenericResource"]):
        for r in sandbox.automation_api.GetResourceAvailability(resourcesNames=[r_name]).Resources:
            if r.ResourceFamilyName in family_name_list:
                reservations_list = []
                for k in r.Reservations:
                    reservations_list.append(k.ReservationId)
        return reservations_list


    def add_connected_resources(sandbox, resource, x,y,shared_flag=False):
        res_details = sandbox.automation_api.GetResourceDetails(resource.Name)
        ports = res_details.ChildResources

        for port in ports:
            if len(port.Connections) > 0:
                for conn in port.Connections:
                    connected_resource = conn.FullPath.split("/")[0]
                    for res in sandbox.automation_api.FindResources(resourceFamily = "CS_GenericResource",resourceFullName=connected_resource).Resources:
                        if res.ReservedStatus == "Not In Reservations" or (res.ReservedStatus == "Shared" and sandbox.id not in get_all_reservations(res.Name,sandbox)):
                            sandbox.automation_api.AddResourcesToReservation(reservationId=sandbox.id, resourcesFullPath=[connected_resource],shared=shared_flag)
                            sandbox.automation_api.SetReservationResourcePosition(reservationId=sandbox.id,resourceFullName=connected_resource, x=x,y=y)


    def connect_all_resources(sandbox):
        try:
            res_list = []
            shared_status = {}
            resources_in_reservation = sandbox.automation_api.GetReservationDetails(reservationId=sandbox.id).ReservationDescription.Resources
            for resource_reserved in resources_in_reservation:
                if resource_reserved.ResourceFamilyName == "CS_GenericResource":
                    res_list.append(resource_reserved.Name)
                    shared_status[resource_reserved.Name] = resource_reserved.Shared

                connection_set = []
            for resource in sandbox.automation_api.GetReservationDetails(reservationId=sandbox.id).ReservationDescription.Resources:
                if resource.ResourceFamilyName == "CS_GenericResource":
                    print(resource.Name)
                    res_details = sandbox.automation_api.GetResourceDetails(resource.Name)
                    ports = res_details.ChildResources
                    for port in ports:
                        if len(port.Connections) > 0:
                            for conn in port.Connections:
                                connected_resource = conn.FullPath.split("/")[0]
                                con_set = set([conn.FullPath, port.Name])
                                if connected_resource in res_list and con_set not in connection_set:
                                    if shared_status[conn.FullPath.split("/")[0]] and shared_status[port.Name.split("/")[0]]:
                                        sandbox.automation_api.AddRoutesToReservation(reservationId=sandbox.id, sourceResourcesFullPath=[port.Name],targetResourcesFullPath=[conn.FullPath],mappingType="bi",isShared = True)
                                    else:
                                        sandbox.automation_api.AddRoutesToReservation(reservationId=sandbox.id, sourceResourcesFullPath=[port.Name],targetResourcesFullPath=[conn.FullPath],mappingType="bi",isShared = False)
                                    connection_set.append(con_set)
                                    sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id,"Connected: " + port.Name + " and " + conn.FullPath)
        except Exception as e:
            sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: Connecting Resources failed: " + e.message)
            sandbox.automation_api.EndReservation(sandbox.id)


    try:
        reserved_resource_string = ""
        c_x, c_y = get_center_position(sandbox)
        d = 200
        if validate_input(phones_in_res,poss_inp_phone):
            phone_x = c_x+4*d
            phone_y = c_y
            offset = -1
            iter = 1
            for phone_id in phones_in_res.split(","):
                for resource in sandbox.automation_api.FindResources(resourceFamily="CS_GenericResource", resourceModel="Phone", \
                                                      attributeValues=[
                                                          AttributeNameValue(Name="Phone.Phone_ID", Value=phone_id)]).Resources:
                    if resource.ReservedStatus != "Reserved":
                        sandbox.automation_api.AddResourcesToReservation(reservationId=sandbox.id,
                                                                         resourcesFullPath=[resource.Name], shared=False)
                        sandbox.automation_api.SetReservationResourcePosition(reservationId=sandbox.id,
                                                               resourceFullName=resource.Name, x=phone_x, y= phone_y)
                        offset = offset*-1
                        phone_y += offset*d*iter/2
                        iter+=1

                        add_connected_resources(sandbox, resource, c_x +2*d, c_y, True)

                    else:
                        reserved_resource_string += resource.Name + ", "



        if validate_input(aps_in_res,poss_inp_aps):
            ap_x = c_x + 2 * d
            ap_y = c_y - 3 * d
            for ap_id in aps_in_res.split(","):
                for resource in sandbox.automation_api.FindResources(resourceFamily="CS_GenericResource", resourceModel="ApV2", \
                                                      attributeValues=[
                                                          AttributeNameValue(Name="ApV2.Ap_ID", Value=ap_id)]).Resources:
                    if resource.ReservedStatus != "Reserved":
                        sandbox.automation_api.AddResourcesToReservation(reservationId=sandbox.id,
                                                                         resourcesFullPath=[resource.Name], shared=False)
                        sandbox.automation_api.SetReservationResourcePosition(reservationId=sandbox.id,
                                                               resourceFullName=resource.Name, x=ap_x, y= ap_y)
                        add_connected_resources(sandbox, resource, ap_x, ap_y+d, True)
                        ap_x = ap_x - 2*d
                    else:
                        reserved_resource_string += resource.Name + ", "


        if inc_lanforge == "Yes":
            lf_x = c_x - d
            lf_y = c_y - d
            for resource in sandbox.automation_api.FindResources(resourceFamily="CS_GenericResource", resourceModel="Trafficgenerator", \
                                                  attributeValues=[AttributeNameValue(Name="Lab Type", Value="InterOp")]).Resources:

                sandbox.automation_api.AddResourcesToReservation(reservationId=sandbox.id, resourcesFullPath=[resource.Name], shared=True)
                sandbox.automation_api.SetReservationResourcePosition(reservationId=sandbox.id,
                                                                      resourceFullName=resource.Name, x=lf_x,
                                                                      y=lf_y)
                add_connected_resources(sandbox, resource, lf_x+d, lf_y-d, True )


        if reserved_resource_string != "":
            raise Exception("ERROR: The following resources are currently reserved, please reserve later or choose different resources: "+ reserved_resource_string[:-2])
        else:
             connect_all_resources(sandbox)

    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, e.message)
        sandbox.automation_api.EndReservation(sandbox.id)



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
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: Failure in Helm Install: " + e.message)
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
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: AP Redirect Failed: " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

def power_off_other_aps(sandbox, components):
    try:
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == 'ApV2':
                cmd = InputNameValue(Name='cmd', Value='off')
                sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'powerOtherAPs', [cmd])
    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: Power Off Other AP's failed: " + e.message)
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
        api.WriteMessageToReservationOutput(sandbox.id, 'ERROR: Failed to Factory Reset {}'.format(ap_res.Name))
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
                    if async_results[i].successful() == False:
                        raise Exception('Caught exception in Factory Reset')

            except Exception as e:
                sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, 'Failed: '+ e.message)
                sandbox.automation_api.EndReservation(sandbox.id)

    else:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: No Terminal Server in reservation")


def check_lab_type(sandbox):
    flag = False
    ap_found = False
    return_val = ""
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

    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, e.message)
        sandbox.automation_api.EndReservation(sandbox.id)

    if return_val in ["Basic", "Advanced"]:
        flag = True

    return flag


def phone_reservation(sandbox, components):
    try:
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == 'Phone':
                perfectoURL_value = InputNameValue(Name='perfectoURL', Value=sandbox.global_inputs['perfectoURL'])
                securityToken_value = InputNameValue(Name='securityToken', Value=sandbox.global_inputs['securityToken'])
                res = sandbox.automation_api.ExecuteCommand(sandbox.id, each.Name, 'Resource', 'perfecto_phone_reserve',[perfectoURL_value,securityToken_value], printOutput=True)
                sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id,"Perfecto Phone Reservation Complete")
    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: Phone Reservation Failed (check input values): " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)
        
def phone_reboot(sandbox, components):
    try:
        for each in sandbox.automation_api.GetReservationDetails(sandbox.id).ReservationDescription.Resources:
            if each.ResourceModelName == 'Phone':
                res = sandbox.automation_api.ExecuteCommand(reservationId=sandbox.id,targetName= each.Name,targetType=  'Resource', commandName='phone_reboot',commandInputs=[], printOutput=True)
                sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id,"Perfecto Phone Reboot Complete")
    except Exception as e:
        sandbox.automation_api.WriteMessageToReservationOutput(sandbox.id, "ERROR: Phone Reboot Failed " + e.message)
        sandbox.automation_api.EndReservation(sandbox.id)


sandbox = Sandbox()
DefaultSetupWorkflow().register(sandbox)
sandbox.workflow.add_to_provisioning(add_reserved_resources, [])
sandbox.workflow.add_to_provisioning(helm_install, [])
sandbox.workflow.on_provisioning_ended(phone_reboot, [])
sandbox.workflow.on_provisioning_ended(phone_reservation, [])
sandbox.workflow.on_provisioning_ended(ap_redirect, [])
sandbox.workflow.on_provisioning_ended(execute_terminal_script, [])
if check_lab_type(sandbox):
    sandbox.workflow.on_provisioning_ended(power_off_other_aps, [])

sandbox.execute_setup()