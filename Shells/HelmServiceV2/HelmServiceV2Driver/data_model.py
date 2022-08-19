from cloudshell.shell.core.driver_context import ResourceCommandContext, AutoLoadDetails, AutoLoadAttribute, \
    AutoLoadResource
from collections import defaultdict


class LegacyUtils(object):
    def __init__(self):
        self._datamodel_clss_dict = self.__generate_datamodel_classes_dict()

    def migrate_autoload_details(self, autoload_details, context):
        model_name = context.resource.model
        root_name = context.resource.name
        root = self.__create_resource_from_datamodel(model_name, root_name)
        attributes = self.__create_attributes_dict(autoload_details.attributes)
        self.__attach_attributes_to_resource(attributes, '', root)
        self.__build_sub_resoruces_hierarchy(root, autoload_details.resources, attributes)
        return root

    def __create_resource_from_datamodel(self, model_name, res_name):
        return self._datamodel_clss_dict[model_name](res_name)

    def __create_attributes_dict(self, attributes_lst):
        d = defaultdict(list)
        for attribute in attributes_lst:
            d[attribute.relative_address].append(attribute)
        return d

    def __build_sub_resoruces_hierarchy(self, root, sub_resources, attributes):
        d = defaultdict(list)
        for resource in sub_resources:
            splitted = resource.relative_address.split('/')
            parent = '' if len(splitted) == 1 else resource.relative_address.rsplit('/', 1)[0]
            rank = len(splitted)
            d[rank].append((parent, resource))

        self.__set_models_hierarchy_recursively(d, 1, root, '', attributes)

    def __set_models_hierarchy_recursively(self, dict, rank, manipulated_resource, resource_relative_addr, attributes):
        if rank not in dict: # validate if key exists
            pass

        for (parent, resource) in dict[rank]:
            if parent == resource_relative_addr:
                sub_resource = self.__create_resource_from_datamodel(
                    resource.model.replace(' ', ''),
                    resource.name)
                self.__attach_attributes_to_resource(attributes, resource.relative_address, sub_resource)
                manipulated_resource.add_sub_resource(
                    self.__slice_parent_from_relative_path(parent, resource.relative_address), sub_resource)
                self.__set_models_hierarchy_recursively(
                    dict,
                    rank + 1,
                    sub_resource,
                    resource.relative_address,
                    attributes)

    def __attach_attributes_to_resource(self, attributes, curr_relative_addr, resource):
        for attribute in attributes[curr_relative_addr]:
            setattr(resource, attribute.attribute_name.lower().replace(' ', '_'), attribute.attribute_value)
        del attributes[curr_relative_addr]

    def __slice_parent_from_relative_path(self, parent, relative_addr):
        if parent is '':
            return relative_addr
        return relative_addr[len(parent) + 1:] # + 1 because we want to remove the seperator also

    def __generate_datamodel_classes_dict(self):
        return dict(self.__collect_generated_classes())

    def __collect_generated_classes(self):
        import sys, inspect
        return inspect.getmembers(sys.modules[__name__], inspect.isclass)


class HelmServiceV2(object):
    def __init__(self, name):
        """
        
        """
        self.attributes = {}
        self.resources = {}
        self._cloudshell_model_name = 'Helm Service V2'
        self._name = name

    def add_sub_resource(self, relative_path, sub_resource):
        self.resources[relative_path] = sub_resource

    @classmethod
    def create_from_context(cls, context):
        """
        Creates an instance of NXOS by given context
        :param context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :type context: cloudshell.shell.core.driver_context.ResourceCommandContext
        :return:
        :rtype HelmServiceV2
        """
        result = HelmServiceV2(name=context.resource.name)
        for attr in context.resource.attributes:
            result.attributes[attr] = context.resource.attributes[attr]
        return result

    def create_autoload_details(self, relative_path=''):
        """
        :param relative_path:
        :type relative_path: str
        :return
        """
        resources = [AutoLoadResource(model=self.resources[r].cloudshell_model_name,
            name=self.resources[r].name,
            relative_address=self._get_relative_path(r, relative_path))
            for r in self.resources]
        attributes = [AutoLoadAttribute(relative_path, a, self.attributes[a]) for a in self.attributes]
        autoload_details = AutoLoadDetails(resources, attributes)
        for r in self.resources:
            curr_path = relative_path + '/' + r if relative_path else r
            curr_auto_load_details = self.resources[r].create_autoload_details(curr_path)
            autoload_details = self._merge_autoload_details(autoload_details, curr_auto_load_details)
        return autoload_details

    def _get_relative_path(self, child_path, parent_path):
        """
        Combines relative path
        :param child_path: Path of a model within it parent model, i.e 1
        :type child_path: str
        :param parent_path: Full path of parent model, i.e 1/1. Might be empty for root model
        :type parent_path: str
        :return: Combined path
        :rtype str
        """
        return parent_path + '/' + child_path if parent_path else child_path

    @staticmethod
    def _merge_autoload_details(autoload_details1, autoload_details2):
        """
        Merges two instances of AutoLoadDetails into the first one
        :param autoload_details1:
        :type autoload_details1: AutoLoadDetails
        :param autoload_details2:
        :type autoload_details2: AutoLoadDetails
        :return:
        :rtype AutoLoadDetails
        """
        for attribute in autoload_details2.attributes:
            autoload_details1.attributes.append(attribute)
        for resource in autoload_details2.resources:
            autoload_details1.resources.append(resource)
        return autoload_details1

    @property
    def cloudshell_model_name(self):
        """
        Returns the name of the Cloudshell model
        :return:
        """
        return 'HelmServiceV2'

    @property
    def github_repo_url(self):
        """
        :rtype: str
        """
        return self.attributes['Helm Service V2.Github Repo URL'] if 'Helm Service V2.Github Repo URL' in self.attributes else None

    @github_repo_url.setter
    def github_repo_url(self, value):
        """
        GitHub URL to helm files.
        :type value: str
        """
        self.attributes['Helm Service V2.Github Repo URL'] = value

    @property
    def github_repo_branch(self):
        """
        :rtype: str
        """
        return self.attributes['Helm Service V2.Github Repo branch'] if 'Helm Service V2.Github Repo branch' in self.attributes else None

    @github_repo_branch.setter
    def github_repo_branch(self, value):
        """
        Github Repo Branch.
        :type value: str
        """
        self.attributes['Helm Service V2.Github Repo branch'] = value

    @property
    def github_repo_path_to_chart(self):
        """
        :rtype: str
        """
        return self.attributes['Helm Service V2.Github Repo Path to Chart'] if 'Helm Service V2.Github Repo Path to Chart' in self.attributes else None

    @github_repo_path_to_chart.setter
    def github_repo_path_to_chart(self, value):
        """
        Path to Helm chart within GitHub repo.
        :type value: str
        """
        self.attributes['Helm Service V2.Github Repo Path to Chart'] = value

    @property
    def helm_deploy_script_url(self):
        """
        :rtype: str
        """
        return self.attributes['Helm Service V2.Helm Deploy Script URL'] if 'Helm Service V2.Helm Deploy Script URL' in self.attributes else None

    @helm_deploy_script_url.setter
    def helm_deploy_script_url(self, value):
        """
        URL to windows batch file to prep and run Helm Install.
        :type value: str
        """
        self.attributes['Helm Service V2.Helm Deploy Script URL'] = value

    @property
    def rtty_token(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.RTTY_TOKEN'] if 'Helm Service V2.RTTY_TOKEN' in self.attributes else None

    @rtty_token.setter
    def rtty_token(self, value):
        """
        RTTY_TOKEN
        :type value: string
        """
        self.attributes['Helm Service V2.RTTY_TOKEN'] = value

    @property
    def ucentralgw_auth_username(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.UCENTRALGW_AUTH_USERNAME'] if 'Helm Service V2.UCENTRALGW_AUTH_USERNAME' in self.attributes else None

    @ucentralgw_auth_username.setter
    def ucentralgw_auth_username(self, value):
        """
        UCENTRALGW_AUTH_USERNAME
        :type value: string
        """
        self.attributes['Helm Service V2.UCENTRALGW_AUTH_USERNAME'] = value

    @property
    def ucentralgw_auth_password(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.UCENTRALGW_AUTH_PASSWORD'] if 'Helm Service V2.UCENTRALGW_AUTH_PASSWORD' in self.attributes else None

    @ucentralgw_auth_password.setter
    def ucentralgw_auth_password(self, value):
        """
        UCENTRALGW_AUTH_PASSWORD
        :type value: string
        """
        self.attributes['Helm Service V2.UCENTRALGW_AUTH_PASSWORD'] = value

    @property
    def ucentralfms_s3_secret(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.UCENTRALFMS_S3_SECRET'] if 'Helm Service V2.UCENTRALFMS_S3_SECRET' in self.attributes else None

    @ucentralfms_s3_secret.setter
    def ucentralfms_s3_secret(self, value):
        """
        UCENTRALFMS_S3_SECRET
        :type value: string
        """
        self.attributes['Helm Service V2.UCENTRALFMS_S3_SECRET'] = value

    @property
    def ucentralfms_s3_key(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.UCENTRALFMS_S3_KEY'] if 'Helm Service V2.UCENTRALFMS_S3_KEY' in self.attributes else None

    @ucentralfms_s3_key.setter
    def ucentralfms_s3_key(self, value):
        """
        UCENTRALFMS_S3_KEY
        :type value: string
        """
        self.attributes['Helm Service V2.UCENTRALFMS_S3_KEY'] = value

    @property
    def owgw_auth_username(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.OWGW_AUTH_USERNAME'] if 'Helm Service V2.OWGW_AUTH_USERNAME' in self.attributes else None

    @owgw_auth_username.setter
    def owgw_auth_username(self, value):
        """
        OWGW_AUTH_USERNAME
        :type value: string
        """
        self.attributes['Helm Service V2.OWGW_AUTH_USERNAME'] = value

    @property
    def owgw_auth_password(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.OWGW_AUTH_PASSWORD'] if 'Helm Service V2.OWGW_AUTH_PASSWORD' in self.attributes else None

    @owgw_auth_password.setter
    def owgw_auth_password(self, value):
        """
        OWGW_AUTH_PASSWORD
        :type value: string
        """
        self.attributes['Helm Service V2.OWGW_AUTH_PASSWORD'] = value

    @property
    def owfms_s3_secret(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.OWFMS_S3_SECRET'] if 'Helm Service V2.OWFMS_S3_SECRET' in self.attributes else None

    @owfms_s3_secret.setter
    def owfms_s3_secret(self, value):
        """
        OWFMS_S3_SECRET
        :type value: string
        """
        self.attributes['Helm Service V2.OWFMS_S3_SECRET'] = value

    @property
    def owfms_s3_key(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.OWFMS_S3_KEY'] if 'Helm Service V2.OWFMS_S3_KEY' in self.attributes else None

    @owfms_s3_key.setter
    def owfms_s3_key(self, value):
        """
        OWFMS_S3_KEY
        :type value: string
        """
        self.attributes['Helm Service V2.OWFMS_S3_KEY'] = value

    @property
    def user(self):
        """
        :rtype: str
        """
        return self.attributes['Helm Service V2.User'] if 'Helm Service V2.User' in self.attributes else None

    @user.setter
    def user(self, value):
        """
        SDK username
        :type value: str
        """
        self.attributes['Helm Service V2.User'] = value

    @property
    def password(self):
        """
        :rtype: string
        """
        return self.attributes['Helm Service V2.Password'] if 'Helm Service V2.Password' in self.attributes else None

    @password.setter
    def password(self, value):
        """
        SDK Password
        :type value: string
        """
        self.attributes['Helm Service V2.Password'] = value

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        
        :type value: str
        """
        self._name = value

    @property
    def cloudshell_model_name(self):
        """
        :rtype: str
        """
        return self._cloudshell_model_name

    @cloudshell_model_name.setter
    def cloudshell_model_name(self, value):
        """
        
        :type value: str
        """
        self._cloudshell_model_name = value



