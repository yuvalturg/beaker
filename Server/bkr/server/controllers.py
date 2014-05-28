
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, widgets, validate, error_handler, validators, paginate, url
from turbogears import redirect, config
import bkr
import bkr.server.stdvars
import bkr.server.search_utility as su
from bkr.server.model import (TaskBase, Device, System, SystemGroup,
        SystemActivity, Key, OSMajor, DistroTree, Arch, TaskPriority,
        Group, GroupActivity, RecipeSet, RecipeSetActivity, User, LabInfo,
        ReleaseAction, LabController, Hypervisor, KernelType,
        SystemType, Distro, Note, Job, InstallOptions, ExcludeOSMajor,
        ExcludeOSVersion, OSVersion, Provision, ProvisionFamily,
        ProvisionFamilyUpdate, SystemStatus, Key_Value_Int, Key_Value_String,
        SystemAccessPolicy, SystemPermission, MachineRecipe, DistroTag)
from bkr.server.power import PowerTypes
from bkr.server.keytypes import KeyTypes
from bkr.server.CSV_import_export import CSV
from bkr.server.group import Groups
from bkr.server.configuration import Configuration
from bkr.server.tag import Tags
from bkr.server.osversion import OSVersions
from bkr.server.distro_family import DistroFamily
from bkr.server.labcontroller import LabControllers
from bkr.server.user import Users
from bkr.server.distro import Distros
from bkr.server.distrotrees import DistroTrees
from bkr.server.activity import Activities
from bkr.server.reports import Reports
from bkr.server.job_matrix import JobMatrix
from bkr.server.reserve_workflow import ReserveWorkflow
from bkr.server.retention_tags import RetentionTag as RetentionTagController
from bkr.server.watchdog import Watchdogs
from bkr.server.systems import SystemsController
from bkr.server.system_action import SystemAction as SystemActionController
from bkr.server.widgets import TaskSearchForm, SearchBar, \
    SystemInstallOptions, SystemGroups, \
    SystemNotes, SystemKeys, SystemExclude, SystemDetails, \
    LabInfoForm, myPaginateDataGrid
from bkr.server.preferences import Preferences
from bkr.server.authentication import Auth
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.jobs import Jobs
from bkr.server.recipes import Recipes
from bkr.server.recipesets import RecipeSets
from bkr.server.tasks import Tasks
from bkr.server.task_actions import TaskActions
from bkr.server.kickstart import KickstartController
from bkr.server.controller_utilities import Utility, \
    restrict_http_method
from bkr.server.bexceptions import BeakerException, BX
from cherrypy import request, response
from cherrypy.lib.cptools import serve_file
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from bkr.server.helpers import make_link
from bkr.server import metrics, identity
from bkr.server.needpropertyxml import XmlHost
from decimal import Decimal
import bkr.server.recipes
import bkr.server.rdf
import kid
import cherrypy
import re
import os
import pkg_resources
import rdflib.graph
from sqlalchemy import and_, join
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import InvalidRequestError
import time
from datetime import datetime

import logging
log = logging.getLogger("bkr.server.controllers")

# This ridiculous hack gets us an HTML5 doctype in our Kid template output.
config.update({'kid.outputformat': kid.HTMLSerializer(doctype=('html',))})

class Arches:
    @expose(format='json')
    def by_name(self,name):
        name = name.lower()
        search = Arch.list_by_name(name)
        arches = [match.arch for match in search]
        return dict(arches=arches)

class Devices:

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='fqdn',limit=10)
    def view(self, id):
        device = session.query(Device).get(id)
        systems = System.all(identity.current.user).join('devices').filter_by(id=id).distinct()
        device_grid = myPaginateDataGrid(fields=[
                        ('System', lambda x: make_link("/view/%s" % x.fqdn, x.fqdn)),
                        ('Description', lambda x: device.description),
                       ])
        return dict(title="", 
                    grid = device_grid, 
                    search_bar=None,
                    list = systems)

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='description',limit=50)
    def default(self, *args, **kw):
        args = list(args)
        if len(args) == 1:
            devices = session.query(Device).join('device_class').filter_by(device_class=args[0])
                
        if len(args) != 1:
            devices = session.query(Device).join('device_class')
        devices_grid = myPaginateDataGrid(fields=[
                        widgets.PaginateDataGrid.Column(name='description', getter=lambda x: make_link("/devices/view/%s" % x.id, x.description), title='Description', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_class.device_class', getter=lambda x: x.device_class, title='Type', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='bus', getter=lambda x: x.bus, title='Bus', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='driver', getter=lambda x: x.driver, title='Driver', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='vendor_id', getter=lambda x: x.vendor_id, title='Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_id', getter=lambda x: x.device_id, title='Device ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_vendor_id', getter=lambda x: x.subsys_vendor_id, title='Subsys Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_device_id', getter=lambda x: x.subsys_device_id, title='Subsys Device ID', options=dict(sortable=True)),
                       ])
        return dict(title="Devices", 
                    grid = devices_grid, 
                    search_bar=None, 
                    list = devices)


class Root(RPCRoot): 
    powertypes = PowerTypes()
    keytypes = KeyTypes()
    devices = Devices()
    groups = Groups()
    configuration = Configuration()
    tags = Tags()
    distrofamily = DistroFamily()
    osversions = OSVersions()
    labcontrollers = LabControllers()
    distros = Distros()
    distrotrees = DistroTrees()
    activity = Activities()
    users = Users()
    arches = Arches()
    auth = Auth()
    csv = CSV()
    jobs = Jobs()
    recipesets = RecipeSets()
    recipes = Recipes()
    tasks = Tasks()
    taskactions = TaskActions()
    reports = Reports()
    matrix = JobMatrix()
    reserveworkflow = ReserveWorkflow()
    watchdogs = Watchdogs()
    retentiontag = RetentionTagController()
    system_action = SystemActionController()
    systems = SystemsController()
    kickstart = KickstartController()
    prefs = Preferences()

    for entry_point in pkg_resources.iter_entry_points('bkr.controllers'):
        controller = entry_point.load()
        log.info('Attaching root extension controller %s as %s',
                controller, entry_point.name)
        locals()[entry_point.name] = controller

    labinfo_form = LabInfoForm(name='labinfo')
    system_details = SystemDetails()
    system_exclude = SystemExclude(name='excluded_families')
    system_keys = SystemKeys(name='keys')
    system_notes = SystemNotes(name='notes')
    system_groups = SystemGroups(name='groups')
    system_installoptions = SystemInstallOptions(name='installoptions')
    task_form = TaskSearchForm(name='tasks')


    @expose(format='json')
    def get_keyvalue_search_options(self,**kw):
        return_dict = {}
        return_dict['keyvals'] = Key.get_all_keys()
        return return_dict

    @expose(format='json')
    def get_search_options_distros(self,table_field, *args, **kw):
        return su.Distro.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_recipe(self,table_field, *args, **kw):
        return su.Recipe.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_job(self,table_field, *args, **kw):
        return su.Job.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_task(self,table_field, *args, **kw):
        return su.Task.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_operators_keyvalue(self,keyvalue_field,*args,**kw):
        return su.Key.search.get_search_options(keyvalue_field, *args, **kw)

    @expose(format='json')
    def get_search_options(self,table_field, *args, **kw):
        return_dict = {}
        search =  su.System.search.search_on(table_field)
      
        #Determine what field type we are dealing with. If it is Boolean, convert our values to 0 for False
        # and 1 for True
        col_type = su.System.search.field_type(table_field)
       
        if col_type.lower() == 'boolean':
            search['values'] = { 0:'False', 1:'True'}
            
        #Determine if we have search values. If we do, then we should only have the operators
        # 'is' and 'is not'.
        if search['values']:
            search['operators'] = filter(lambda x: x == 'is' or x == 'is not', search['operators'])         

        search['operators'].sort()
        return_dict['search_by'] = search['operators'] 
        return_dict['search_vals'] = search['values'] 
        return return_dict

    @expose(format='json')
    def get_fields(self, table_name):
        return dict( fields = System.get_fields(table_name))
  
    @expose(format='json')
    def get_osversions(self, osmajor_id=None):
        osversions = [(0,u'All')]
        try:
            osmajor = OSMajor.by_id(osmajor_id)
            osversions.extend([(osversion.id,
                           osversion.osminor
                          ) for osversion in osmajor.osversions])
        except InvalidRequestError:
            pass
        return dict(osversions = osversions)
    
    @expose(format='json')
    def get_installoptions(self, system_id=None, distro_tree_id=None):
        try:
            system = System.by_id(system_id,identity.current.user)
        except NoResultFound:
            return dict(ks_meta=None)
        try:
            distro_tree = DistroTree.by_id(distro_tree_id)
        except NoResultFound:
            return dict(ks_meta=None)
        install_options = system.install_options(distro_tree)
        return install_options.as_strings()

    @expose(format='json')
    def change_priority_recipeset(self, priority, recipeset_id):
        user = identity.current.user
        if not user:
            return {'success' : None, 'msg' : 'Must be logged in' }

        try:
            recipeset = RecipeSet.by_id(recipeset_id)
        except NoResultFound as e:
            log.error('No rows returned for recipeset_id %s in change_priority_recipeset:%s' % (recipeset_id,e))
            return { 'success' : None, 'msg' : 'RecipeSet is not valid' }

        try: 
            priority = TaskPriority.from_string(priority)
        except ValueError:
            log.exception('Invalid priority')
            return { 'success' : None, 'msg' : 'Priority not found', 'current_priority' : recipeset.priority.value }

        if priority not in recipeset.allowed_priorities(user):
            return {'success' : None, 'msg' : 'Insufficient privileges for that priority', 'current_priority' : recipeset.priority.value }

        old_priority = recipeset.priority.value if recipeset.priority else None
        recipeset.priority = priority
        recipeset.record_activity(user=identity.current.user, service=u'WEBUI',
                                  field=u'Priority', action=u'Changed', old=old_priority,
                                  new=priority.value)
        return {'success' : True } 

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def index(self, *args, **kw): 
        return self._systems(systems=System.all(identity.current.user).
                             filter(System.status != SystemStatus.removed),
                             title=u'Systems', *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def available(self, *args, **kw):
        query = System.all(identity.current.user)\
                .filter(System.can_reserve(identity.current.user))\
                .filter(System.status.in_([SystemStatus.automated, SystemStatus.manual]))
        return self._systems(systems=query,
                title=u'Available Systems', *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def free(self, *args, **kw): 
        query = System.all(identity.current.user)\
                .filter(System.can_reserve(identity.current.user))\
                .filter(System.status.in_([SystemStatus.automated, SystemStatus.manual]))\
                .filter(System.is_free(identity.current.user))
        return self._systems(systems=query,
                title=u'Free Systems', *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def removed(self, *args, **kw): 
        query = System.all(identity.current.user)\
                .filter(System.status == SystemStatus.removed)
        return  self._systems(systems=query,
                              title=u'Removed Systems', exclude_status=True, 
                              *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list', default_order='fqdn', limit=20, max_limit=None)
    def mine(self, *args, **kw):
        systems = System.mine(identity.current.user).\
                  filter(System.status != SystemStatus.removed)
        return self._systems(systems=systems,
                             title=u'My Systems', *args, **kw)

      
    @expose(template='bkr.server.templates.grid') 
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn', limit=20)
    def reserve_system(self, *args,**kw):
        if kw.get('distro_tree_id'):
            try:
                distro_tree = DistroTree.by_id(kw['distro_tree_id'])
            except NoResultFound:
                flash(_(u'Invalid distro tree id %s') % kw['distro_tree_id'])
                redirect(url('/reserveworkflow/', **kw))
        else:
            distro_tree = None
        # XXX add force here when we support it
        query = MachineRecipe.hypothetical_candidate_systems(
                identity.current.user, distro_tree)\
                .order_by(None)
        warn = None
        if query.count() < 1:
            warn = u'No Systems compatible with %s' % distro_tree
        def reserve_link(x):
            href = url('/reserveworkflow/', system=x.fqdn, **kw)
            if x.is_free(identity.current.user):
                label = 'Reserve Now'
            else:
                label = 'Queue Reservation'
            a = kid.Element('a', href=href)
            a.attrib['class'] = 'btn'
            a.text = label
            return a
        direct_column = Utility.direct_column(title='Action', getter=reserve_link)
        return_dict = self._systems(systems=query,
                title=u'Reserve Systems', direct_columns=[(8, direct_column)],
                *args, **kw)
        return_dict['warn_msg'] = warn
        return_dict['tg_template'] = "bkr.server.templates.reserve_grid"
        return_dict['action'] = '/reserve_system'
        return return_dict

    def _history_search(self,activity,**kw):
        history_search = su.History.search(activity)
        for search in kw['historysearch']:
            col = search['table'] 
            history_search.append_results(search['value'],col,search['operation'],**kw)
        return history_search.return_results()

    def _system_search(self,kw,sys_search,use_custom_columns = False): 
        for search in kw['systemsearch']: 
	        #clsinfo = System.get_dict()[search['table']] #Need to change this
            class_field_list = search['table'].split('/')
            cls_ref = su.System.search.translate_name_to_class(class_field_list[0])
            col = class_field_list[1]              
            #If value id False or True, let's convert them to
            if class_field_list[0] != 'Key':
                sys_search.append_results(cls_ref,search['value'],col,search['operation'])
            else:
                sys_search.append_results(cls_ref,search['value'],col,search['operation'],keyvalue=search['keyvalue'])

        return sys_search.return_results()
              

    def histories(self,activity,**kw):  
       
        return_dict = {}                    
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['historysearch'] = [{'table' : 'Field Name',   
                                    'operation' : 'contains', 
                                    'value' : kw['simplesearch']}] 
                    
        else:
            simplesearch = None
        return_dict.update({'simplesearch':simplesearch})

        if kw.get("historysearch"):
            searchvalue = kw['historysearch']  
            activities_found = self._history_search(activity,**kw)
            return_dict.update({'activities_found':activities_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict
 
    def _systems(self, systems, title, *args, **kw):
        # To exclude search on System/Status for the "Removed" Systems
        # page
        if kw.get('exclude_status', None):
            exclude_fields = ['Status']
        else:
            exclude_fields = []

        # Added for group.get_systems()
        if kw.has_key('group_id'):
            extra_hiddens={'group_id':kw['group_id']}
        else:
            extra_hiddens = {}

        search_bar = SearchBar(name='systemsearch',
                               label=_(u'System Search'),
                               enable_custom_columns = True,
                               extra_selects = [ { 'name': 'keyvalue', 
                                                   'column':'key/value',
                                                   'display':'none',
                                                   'pos' : 2,
                                                   'callback':url('/get_operators_keyvalue') }],
                               table=su.System.search.create_complete_search_table(\
                                    [{su.System:{'exclude':exclude_fields}},
                                    {su.Cpu:{'all':[]}},
                                    {su.Device:{'all':[]}},
                                    {su.Disk:{'all':[]}},
                                    {su.Key:{'all':[]}}]),
                               search_controller=url("/get_search_options"),
                               date_picker = ['system/added', 'system/lastinventoried'],
                               table_search_controllers = {'key/value':url('/get_keyvalue_search_options')},)

        if 'quick_search' in kw:
            table,op,value = kw['quick_search'].split('-')
            kw['systemsearch'] = [{'table' : table,
                                'operation' : op,
                                'keyvalue': None,
                                'value' : value}]
            simplesearch = kw['simplesearch']
        elif 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['systemsearch'] = [{'table' : 'System/Name',   
                                   'operation' : 'contains',
                                   'keyvalue' : None,
                                   'value' : kw['simplesearch']}]
        else:
            simplesearch = None

        # Short cut search by type
        if 'type' in kw:
            kw['systemsearch'] = [{'table' : 'System/Type',
                                   'operation' : 'is',
                                   'value' : kw['type']}]      
            #when we do a short cut type search, result column args are not passed
            #we need to recreate them here from our cookies 
            if 'column_values' in request.simple_cookie: 
                text = request.simple_cookie['column_values'].value
                vals_to_set = text.split(',')
                for elem in vals_to_set:
                    kw['systemsearch_column_%s' % elem] = elem 
       
        default_result_columns = ('System/Name', 'System/Status', 'System/Vendor',
                                  'System/Model','System/Arch', 'System/User', 'System/Type') 

        if kw.get('xmlsearch'):
            try:
                systems = XmlHost.from_string('<and>%s</and>' % kw['xmlsearch']).apply_filter(systems)
            except ValueError,e:
                response.status = 400
                return e.message

        if kw.get("systemsearch"):
            searchvalue = kw['systemsearch']
            sys_search = su.System.search(systems)
            columns = []
            for elem in kw:
                if re.match('systemsearch_column_',elem):
                    columns.append(kw[elem])

            if columns.__len__() == 0:  #If nothing is selected, let's give them the default
                for elem in default_result_columns:
                    key = 'systemsearch_column_',elem
                    kw[key] = elem
                    columns.append(elem)
            use_custom_columns = False
            for column in columns:
                table,col = column.split('/')
                if sys_search.translate_name_to_class(table) is not su.System:
                    use_custom_columns = True
                    break
            sys_search.add_columns_desc(columns)
            systems = self._system_search(kw,sys_search)
            system_columns_desc = sys_search.get_column_descriptions()
            my_fields = Utility.custom_systems_grid(system_columns_desc, use_custom_columns)
        else:
            columns = None
            searchvalue = None
            my_fields = Utility.custom_systems_grid(default_result_columns)
        if 'direct_columns' in kw: #Let's add our direct columns here
            for index,col in kw['direct_columns']:
                my_fields.insert(index - 1, col)
        add_script = None
        if not identity.current.anonymous:
            add_script = 'new SystemAddModal();'
        display_grid = myPaginateDataGrid(fields=my_fields,
                add_script=add_script)
        col_data = Utility.result_columns(columns)
        return dict(title=title,
                    grid = display_grid,
                    list = systems,
                    searchvalue = searchvalue,
                    options =  {'simplesearch' : simplesearch,
                                'columns':col_data,
                                'result_columns' : default_result_columns,
                                'col_defaults' : col_data['default'],
                                'col_options' : col_data['options'],
                                'extra_hiddens' : extra_hiddens
                                },
                    action = '',
                    search_bar = search_bar,
                    atom_url='?tg_format=atom&list_tgp_order=-date_modified&'
                       + cherrypy.request.query_string,
                    )

    @expose(format='json')
    def by_fqdn(self, input):
        input = input.lower()
        search = System.list_by_fqdn(input,identity.current.user).all()
        matches =  [match.fqdn for match in search]
        return dict(matches = matches)

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def key_remove(self, system_id=None, key_type=None, key_value_id=None):
        removed = None
        if system_id and key_value_id and key_type:
            try:
                system = System.by_id(system_id,identity.current.user)
            except NoResultFound:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id, key_value_id and key_type must be provided"))
            redirect("/")
        
        if system.can_edit(identity.current.user):
            if key_type == 'int':
                key_values = system.key_values_int
            else:
                key_values = system.key_values_string
            for key_value in key_values:
                if key_value.id == int(key_value_id):
                    if key_type == 'int':
                        system.key_values_int.remove(key_value)
                    else:
                        system.key_values_string.remove(key_value)
                    removed = key_value
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Key/Value', "%s/%s" % (removed.key.key_name, removed.key_value), "")
                    system.activity.append(activity)
        
        if removed:
            system.date_modified = datetime.utcnow()
            flash(_(u"removed %s/%s" % (removed.key.key_name,removed.key_value)))
        else:
            flash(_(u"Key_Value_Id not Found"))
        redirect("./view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def group_remove(self, system_id=None, group_id=None):
        removed = None
        if system_id and group_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except NoResultFound:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and group_id must be provided"))
            redirect("/")
        if system.can_edit(identity.current.user):
            for group in system.groups:
                if group.group_id == int(group_id):
                    system.groups.remove(group)
                    removed = group
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Group', group.display_name, "")
                    gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Removed', 'System', "", system.fqdn)
                    group.activity.append(gactivity)
                    system.activity.append(activity)
        if removed:
            system.date_modified = datetime.utcnow()
            flash(_(u"%s Removed" % removed.display_name))
        else:
            flash(_(u"Group ID not found"))
        redirect("./view/%s" % system.fqdn)

    @expose(template="bkr.server.templates.system")
    def _view_system_as_html(self, fqdn=None, **kw):
        if fqdn: 
            try:
                system = System.by_fqdn(fqdn,identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find %s" % fqdn) )
                redirect("/")
        elif kw.get('id'):
            try:
                system = System.by_id(kw['id'],identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find system with id of %s" % kw['id']) )
                redirect("/")
        else:
            flash( _(u"No given system to view") )
            redirect("/")
        our_user = identity.current.user
        if our_user:
            readonly = not system.can_edit(our_user)
            is_user = (system.user == our_user)
            has_loan = (system.loaned == our_user)
            can_reserve = system.can_reserve(our_user)
        else:
            readonly = True
            is_user = False
            has_loan = False
            can_reserve = False
        title = system.fqdn
        distro_picker_options = {
            'tag': [tag.tag for tag in DistroTag.used()],
            'osmajor': [osmajor.osmajor for osmajor in
                OSMajor.ordered_by_osmajor(OSMajor.in_lab(system.lab_controller))],
        }

        if readonly:
            attrs = dict(readonly = 'True')
        else:
            attrs = dict()
        options = {}
        options['readonly'] = readonly
        options['reprovision_distro_tree_id'] = [(dt.id, unicode(dt)) for dt in
                system.distro_trees().order_by(Distro.name,
                    DistroTree.variant, DistroTree.arch_id)]
        #Excluded Family options
        options['excluded_families'] = []
        for arch in system.arch:
            options['excluded_families'].append((arch.arch,
                    [(osmajor.id, osmajor.osmajor,
                     [(osversion.id, '%s' % osversion, attrs)
                      for osversion in osmajor.osversions],
                     attrs) for osmajor in OSMajor.query]))

        # If you have anything in your widgets 'javascript' variable,
        # do not return the widget here, the JS will not be loaded,
        # return it as an arg in return()
        widgets = dict(
                        details   = self.system_details,
                        exclude   = self.system_exclude,
                        keys      = self.system_keys,
                        notes     = self.system_notes,
                      )
        # Lab Info is deprecated, only show it if the system has existing data
        widgets['labinfo'] = self.labinfo_form if system.labinfo else None

        return dict(
            title           = title,
            readonly        = readonly,
            value           = system,
            options         = options,
            task_widget     = self.task_form,
            groups_widget   = self.system_groups,
            install_widget  = self.system_installoptions,
            widgets         = widgets,
            widgets_action  = dict( labinfo   = url('/save_labinfo'),
                                    exclude   = url('/save_exclude'),
                                    keys      = url('/save_keys'),
                                    notes     = url('/save_note'),
                                    groups    = url('/save_group'),
                                    install   = url('/save_install'),
                                    tasks     = '/tasks/do_search',
                                  ),
            widgets_options = dict(labinfo   = options,
                                   exclude   = options,
                                   keys      = dict(readonly = readonly,
                                                key_values_int = system.key_values_int,
                                                key_values_string = system.key_values_string),
                                   notes     = dict(readonly = readonly,
                                                notes = system.notes),
                                   groups    = dict(readonly = readonly,
                                                group_assocs = system.group_assocs,
                                                system_id = system.id),
                                   install   = dict(readonly = readonly,
                                                provisions = system.provisions,
                                                prov_arch = [(arch.id, arch.arch) for arch in system.arch]),
                                   tasks      = dict(system_id = system.id,
                                                     arch = [(0, 'All')] + [(arch.id, arch.arch) for arch in system.arch],
                                                     hidden = dict(system = 1)),
                                   distro_picker=distro_picker_options,
                                  ),
        )
    _view_system_as_html.exposed = False # exposed indirectly by view()

    def _view_system_as_rdf(self, fqdn, **kwargs):
        try:
            system = System.by_fqdn(fqdn, identity.current.user)
        except InvalidRequestError:
            raise cherrypy.NotFound(fqdn)
        graph = rdflib.graph.Graph()
        bkr.server.rdf.describe_system(system, graph)
        bkr.server.rdf.bind_namespaces(graph)
        if kwargs['tg_format'] == 'turtle':
            cherrypy.response.headers['Content-Type'] = 'application/x-turtle'
            return graph.serialize(format='turtle')
        else:
            cherrypy.response.headers['Content-Type'] = 'application/rdf+xml'
            return graph.serialize(format='pretty-xml')

    @cherrypy.expose
    def view(self, fqdn=None, **kwargs):
        if isinstance(fqdn, str):
            fqdn = fqdn.decode('utf8') # for virtual paths like /view/asdf.example.com
        # XXX content negotiation too?
        tg_format = kwargs.get('tg_format', 'html')
        if tg_format in ('rdfxml', 'turtle'):
            return self._view_system_as_rdf(fqdn, **kwargs)
        else:
            return self._view_system_as_html(fqdn, **kwargs)

    @cherrypy.expose
    def delete_note(self, id=None):
        id = int(id)
        try:
            system = System.query.join(System.notes).filter(Note.id == id).one()
        except InvalidRequestError, e:
            log.exception(e)
            return ('0',)
        if not system.can_edit(identity.current.user):
            log.error('User does not have the correct permission to delete this note')
            return ('0',)
        note = Note.query.filter_by(id=id).one()
        note.deleted = datetime.utcnow()
        session.flush()
        return ('1',)

    @error_handler(view)
    @expose()
    @identity.require(identity.not_anonymous())
    @validate(form=labinfo_form)
    def save_labinfo(self, **kw):
        try:
            system = System.by_id(kw['id'],identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Lab Info for %s" % kw['id']) )
            redirect("/")
        if system.labinfo:
            labinfo = system.labinfo
        else:
            labinfo = LabInfo()

        for field in LabInfo.fields:
            if kw.get(field):
                orig_value = getattr(labinfo, field)
                # Convert to Decimal for Comparisons.
                if type(orig_value) == Decimal:
                    new_value = Decimal('%s' % kw[field])
                else:
                    new_value = kw[field]
                if new_value != orig_value:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, '%s' % orig_value, kw[field] )
                    setattr(labinfo, field, kw[field])
                    system.activity.append(activity) 
        system.labinfo = labinfo
        system.date_modified = datetime.utcnow()
        flash( _(u"Saved Lab Info") )
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_keys(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Key for %s" % id) )
            redirect("/")
        # Add a Key/Value Pair
        if kw.get('key_name') and kw.get('key_value'):
            try:
                key = Key.by_name(kw['key_name'])
            except InvalidRequestError:
                #FIXME allow user to create new keys
                flash(_(u"Invalid key %s" % kw['key_name']))
                redirect("/view/%s" % system.fqdn)
            if key.numeric:
                key_value = Key_Value_Int(key,kw['key_value'])
                system.key_values_int.append(key_value)
            else:
                key_value = Key_Value_String(key,kw['key_value'])
                system.key_values_string.append(key_value)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Key/Value', "", "%s/%s" % (kw['key_name'],kw['key_value']) )
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_group(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Group for %s" % id) )
            redirect("/")
        # Add a Group
        if kw.get('group').get('text'):
            try:
                group = Group.by_name(kw['group']['text'])
            except InvalidRequestError:
                flash(_(u"%s is an Invalid Group" % kw['group']['text']))
                redirect("/view/%s" % system.fqdn)
            if group in system.groups:
                flash(_(u"System '%s' is already in group '%s'" % (system.fqdn, group.group_name)))
                redirect("/view/%s" % system.fqdn)
            system.groups.append(group)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Group', "", kw['group']['text'])
            gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Added', 'System', "", system.fqdn)
            group.activity.append(gactivity)
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_note(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Note for %s" % id) )
            redirect("/")
        # Add a Note
        if kw.get('note'):
            system.add_note(text=kw['note'],
                            user=identity.current.user,
                            service='WEBUI')
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_exclude(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Exclude flags for %s" % id) )
            redirect("/")
        for arch in system.arch:
        # Update Excluded Families
            if kw.get('excluded_families') and \
             kw['excluded_families'].has_key(arch.arch):
                if isinstance(kw['excluded_families'][arch.arch], list):
                    excluded_osmajor = [int(i) for i in kw['excluded_families'][arch.arch]]
                else:
                    excluded_osmajor = [int(kw['excluded_families'][arch.arch])]
                for new_families in excluded_osmajor:
                    if new_families not in [osmajor.osmajor.id for osmajor in system.excluded_osmajor_byarch(arch)]:
                        new_excluded_osmajor = ExcludeOSMajor(osmajor=OSMajor.by_id(new_families),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osmajor.osmajor, arch))
                        system.excluded_osmajor.append(new_excluded_osmajor)
                        system.activity.append(activity)
            else:
                excluded_osmajor = []
            for old_families in system.excluded_osmajor_byarch(arch):
                if old_families.osmajor.id not in excluded_osmajor:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_families.osmajor, arch), "")
                    session.delete(old_families)
                    system.activity.append(activity)
                    
            if kw.get('excluded_families_subsection') and \
             kw['excluded_families_subsection'].has_key(arch.arch):
                if isinstance(kw['excluded_families_subsection'][arch.arch], list):
                    excluded_osversion = [int(i) for i in kw['excluded_families_subsection'][arch.arch]]
                else:
                    excluded_osversion = [int(kw['excluded_families_subsection'][arch.arch])]
                for new_osversion in excluded_osversion:
                    if new_osversion not in [osversion.osversion.id for osversion in system.excluded_osversion_byarch(arch)]:
                        new_excluded_osversion = ExcludeOSVersion(osversion=OSVersion.by_id(new_osversion),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osversion.osversion, arch))
                        system.excluded_osversion.append(new_excluded_osversion)
                        system.activity.append(activity)
            else:
                excluded_osversion = []
            for old_osversion in system.excluded_osversion_byarch(arch):
                if old_osversion.osversion.id not in excluded_osversion:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_osversion.osversion, arch), "")
                    session.delete(old_osversion)
                    system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def remove_install(self, system_id, arch_id, **kw):
        try:
            system = System.by_id(system_id, identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to remove Install Option for %s" % system_id) )
            redirect("/")
        try:
            arch = Arch.by_id(arch_id)
        except InvalidRequestError:
            flash( _(u"Unable to lookup arch for %s" % arch_id) )
            redirect("/")
        
        if kw.get('osversion_id'):
            # remove osversion option
            osversion = OSVersion.by_id(int(kw['osversion_id']))
            prov = system.provisions[arch].provision_families[osversion.osmajor]\
                    .provision_family_updates[osversion]
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:ks_meta:%s/%s' % (arch, osversion),
                    old_value=prov.ks_meta, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options:%s/%s' % (arch, osversion),
                    old_value=prov.kernel_options, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options_post:%s/%s' % (arch, osversion),
                    old_value=prov.kernel_options_post, new_value=None))
            del system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion]
        elif kw.get('osmajor_id'):
            # remove osmajor option
            osmajor = OSMajor.by_id(int(kw['osmajor_id']))
            prov = system.provisions[arch].provision_families[osmajor]
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:ks_meta:%s/%s' % (arch, osmajor),
                    old_value=prov.ks_meta, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options:%s/%s' % (arch, osmajor),
                    old_value=prov.kernel_options, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options_post:%s/%s' % (arch, osmajor),
                    old_value=prov.kernel_options_post, new_value=None))
            del system.provisions[arch].provision_families[osmajor]
        else:
            # remove arch option
            prov = system.provisions[arch]
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:ks_meta:%s' % arch,
                    old_value=prov.ks_meta, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options:%s' % arch,
                    old_value=prov.kernel_options, new_value=None))
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Removed',
                    field_name=u'InstallOption:kernel_options_post:%s' % arch,
                    old_value=prov.kernel_options_post, new_value=None))
            del system.provisions[arch]
        system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_install(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Install Options for %s" % id) )
            redirect("/")
        # Add an install option
        if kw.get('prov_ksmeta') or kw.get('prov_koptions') or \
           kw.get('prov_koptionspost'):
            arch = Arch.by_id(int(kw['prov_arch']))
            if int(kw['prov_osversion']) != 0:
                osversion = OSVersion.by_id(int(kw['prov_osversion']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osversion.osmajor):
                        if system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates.has_key(osversion):
                            provision = system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion]
                            action = "Changed"
                        else:
                            provision = ProvisionFamilyUpdate()
                            action = "Added"
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osversion), provision.ks_meta, kw['prov_ksmeta']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osversion), provision.kernel_options, kw['prov_koptions']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osversion), provision.kernel_options_post, kw['prov_koptionspost']))
                        provision.ks_meta=kw['prov_ksmeta']
                        provision.kernel_options=kw['prov_koptions']
                        provision.kernel_options_post=kw['prov_koptionspost']
                        provision.osversion = osversion
                        system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion] = provision
                
            elif int(kw['prov_osmajor']) != 0:
                osmajor = OSMajor.by_id(int(kw['prov_osmajor']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osmajor):
                        provision = system.provisions[arch].provision_families[osmajor]
                        action = "Changed"
                    else:
                        provision = ProvisionFamily()
                        action = "Added"
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osmajor), provision.ks_meta, kw['prov_ksmeta']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osmajor), provision.kernel_options, kw['prov_koptions']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osmajor), provision.kernel_options_post, kw['prov_koptionspost']))
                    provision.ks_meta=kw['prov_ksmeta']
                    provision.kernel_options=kw['prov_koptions']
                    provision.kernel_options_post=kw['prov_koptionspost']
                    provision.osmajor=osmajor
                    system.provisions[arch].provision_families[osmajor] = provision
            else:
                if system.provisions.has_key(arch):
                    provision = system.provisions[arch]
                    action = "Changed"
                else:
                    provision = Provision()
                    action = "Added"
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s' % arch, provision.ks_meta, kw['prov_ksmeta']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s' % arch, provision.kernel_options, kw['prov_koptions']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s' % arch, provision.kernel_options_post, kw['prov_koptionspost']))
                provision.ks_meta=kw['prov_ksmeta']
                provision.kernel_options=kw['prov_koptions']
                provision.kernel_options_post=kw['prov_koptionspost']
                provision.arch=arch
                system.provisions[arch] = provision
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @cherrypy.expose
    def lab_controllers(self):
        query = LabController.query.filter(LabController.removed == None)
        return [lc.fqdn for lc in query]

    @cherrypy.expose
    def legacypush(self, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")

        try:
            system = System.query.filter(System.fqdn == fqdn.decode('ascii')).one()
        except InvalidRequestError:
            raise BX(_('No such system %s') % fqdn)
        return system.update_legacy(inventory)

    @expose()
    def to_xml(self, taskid, to_screen=False, pretty=True, *args, **kw):
        try:
            task = TaskBase.get_by_t_id(taskid)
        except Exception:
            flash(_('Invalid Task: %s' % taskid))
            redirect(url('/'))
        xml = task.to_xml()
        if pretty:
            xml_text = xml.toprettyxml()
        else:
            xml_text = xml.toxml()
      
        if to_screen: #used for testing contents of XML
            cherrypy.response.headers['Content-Disposition'] = ''
            cherrypy.response.headers['Content-Type'] = 'text/plain'
        else:
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename=%s.xml' % taskid
            cherrypy.response.headers['Content-Type'] = 'text/xml'

        return xml_text


    @cherrypy.expose
    def push(self, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")
        try:
            system = System.query.filter(System.fqdn == fqdn.decode('ascii')).one()
        except InvalidRequestError:
            raise BX(_('No such system %s') % fqdn)
        return system.update(inventory)

    @expose(template='bkr.server.templates.forbidden')
    def forbidden(self, reason=None, **kwargs):
        response.status = 403
        return dict(reason=reason)

    @expose(template="bkr.server.templates.login")
    def login(self, forward_url=None, **kwargs):
        if not forward_url:
            forward_url = request.headers.get('Referer', url('/'))
        # If the container is doing authentication for us, we might have 
        # already been authenticated through REMOTE_USER.
        if not identity.current.anonymous:
            raise cherrypy.HTTPRedirect(forward_url)
        # Is this a login attempt?
        if cherrypy.request.method == 'POST':
            user = User.by_user_name(kwargs.get('user_name'))
            if user is not None and user.can_log_in() and \
                    user.check_password(kwargs.get('password')):
                # Attempt successful
                identity.set_authentication(user)
                raise cherrypy.HTTPRedirect(forward_url)
            else:
                msg = _('The credentials you supplied were not correct or '
                        'did not grant access to this resource.')
        else:
            msg = _('Please log in.')
        response.status = 403
        return dict(message=msg, action='', forward_url=forward_url)

    @expose()
    def logout(self):
        identity.clear_authentication()
        raise redirect("/")

    @expose()
    def robots_txt(self):
        return "User-agent: *\nDisallow: /\n"

    @expose()
    def favicon_ico(self):
        static_dir = config.get('static_filter.dir', path="/static")
        filename = join(os.path.normpath(static_dir), 'images', 'favicon.ico')
        return serve_file(filename)

#    @expose(template='bkr.server.templates.activity')
#    def activity(self, *args, **kw):
# TODO This is mainly for testing
# if it hangs around it should check for admin access
#        return dict(title="Activity", search_bar=None, activity = Activity.all())
#

_startup_time = None
def startup_time_start():
    global _startup_time
    _startup_time = time.time()
def startup_time_end():
    duration = time.time() - _startup_time
    log.info('Server startup in %s seconds' % duration)
    metrics.measure('durations.cherrypy_startup', duration)
    metrics.increment('counters.cherrypy_startup')
cherrypy.server.on_start_server_list.insert(0, startup_time_start)
cherrypy.server.on_start_server_list.append(startup_time_end)
