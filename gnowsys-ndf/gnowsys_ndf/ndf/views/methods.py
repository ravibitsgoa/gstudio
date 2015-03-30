''' -- imports from installed packages -- '''
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.shortcuts import render_to_response  # , render
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from mongokit import paginator
import mongokit

''' -- imports from application folders/files -- '''
from gnowsys_ndf.settings import META_TYPE
from gnowsys_ndf.settings import DEFAULT_GAPPS_LIST, WORKING_GAPPS, BENCHMARK
from gnowsys_ndf.ndf.models import db, node_collection, triple_collection
from gnowsys_ndf.ndf.models import *
from gnowsys_ndf.ndf.org2any import org2html
from gnowsys_ndf.mobwrite.models import TextObj
from gnowsys_ndf.ndf.models import HistoryManager, Benchmark
from gnowsys_ndf.notification import models as notification

''' -- imports from python libraries -- '''
# import os -- Keep such imports here
import datetime
import time
import sys
import subprocess
import re
import ast
import string
import json
import locale
from datetime import datetime, timedelta, date
# import csv
# from collections import Counter
from collections import OrderedDict

col = db[Benchmark.collection_name]

history_manager = HistoryManager()
theme_GST = node_collection.one({'_type': 'GSystemType', 'name': 'Theme'})
theme_item_GST = node_collection.one({'_type': 'GSystemType', 'name': 'theme_item'})
topic_GST = node_collection.one({'_type': 'GSystemType', 'name': 'Topic'})

# C O M M O N   M E T H O D S   D E F I N E D   F O R   V I E W S

grp_st = node_collection.one({'$and': [{'_type': 'GSystemType'}, {'name': 'Group'}]})
ins_objectid = ObjectId()

def get_execution_time(f):
   if BENCHMARK == 'ON': 

  
	    def wrap(*args,**kwargs):
	        time1 = time.time()
	        total_parm_size = 0
	        for key, value in kwargs.iteritems():
	           total_parm_size = total_parm_size + sys.getsizeof(value)
	        total_param = len(kwargs)
	        ret = f(*args,**kwargs)
	        t2 = time.clock()
	        time2 = time.time()
	        time_diff = time2 - time1
	        benchmark_node =  col.Benchmark()
	        benchmark_node.time_taken = unicode(str(time_diff))
	        benchmark_node.name = unicode(f.func_name)
	        benchmark_node.parameters = unicode(total_param)
	        benchmark_node.size_of_parameters = unicode(total_parm_size)
	        benchmark_node.last_update = datetime.today()
	        #benchmark_node.functionOplength = unicode(sys.getsizeof(ret))
	        try:
	        	benchmark_node.calling_url = unicode(args[0].path)
	        except:	
	        	pass 
	        benchmark_node.save()
	        return ret
   if BENCHMARK == 'ON': 
    	return wrap
   if BENCHMARK == 'OFF':
        return f


@get_execution_time
def get_group_name_id(group_name_or_id, get_obj=False):
    '''
      - This method takes possible group name/id as an argument and returns (group-name and id) or group object.
      
      - If no second argument is passed, as method name suggests, returned result is "group_name" first and "group_id" second.

      - When we need the entire group object, just pass second argument as (boolian) True. In the case group object will be returned.  

      Example 1: res_group_name, res_group_id = get_group_name_id(group_name_or_id)
      - "res_group_name" will contain name of the group.
      - "res_group_id" will contain _id/ObjectId of the group.

      Example 2: res_group_obj = get_group_name_id(group_name_or_id, True)
      - "res_group_obj" will contain entire object.
    '''

    # case-1: argument - "group_name_or_id" is ObjectId
    if ObjectId.is_valid(group_name_or_id):
        group_obj = node_collection.one({"_id": ObjectId(group_name_or_id)})

        # checking if group_obj is valid
        if group_obj:
            # if (group_name_or_id == group_obj._id):
            group_id = group_name_or_id
            group_name = group_obj.name

            if get_obj:
                return group_obj
            else:
                return group_name, group_id

    # case-2: argument - "group_name_or_id" is group name
    else:
        group_obj = node_collection.one({"_type": {"$in": ["Group", "Author"] }, "name": unicode(group_name_or_id)})

        # checking if group_obj is valid
        if group_obj:
            # if (group_name_or_id == group_obj.name):
            group_name = group_name_or_id
            group_id = group_obj._id

            if get_obj:
                return group_obj
            else:
                return group_name, group_id

    if get_obj:
        return None
    else:
        return None, None


@get_execution_time
def check_delete(main):
  try:


    def check(*args, **kwargs):
      relns=""
      node_id=kwargs['node_id']
      ins_objectid  = ObjectId()
      if ins_objectid.is_valid(node_id) :
        node = node_collection.one({'_id': ObjectId(node_id)})
        relns=node.get_possible_relations(node.member_of)
        attrbts=node.get_possible_attributes(node.member_of)
        return main(*args, **kwargs)
      else:
        print "Not a valid id"
    return check 
  except Exception as e:
    print "Error in check_delete "+str(e)

@get_execution_time
def get_all_resources_for_group(group_id):
  if ins_objectid.is_valid(group_id):
    obj_resources = node_collection.find({'$and': [{'$or': [{'_type': 'GSystem'}, {'_type': 'File'}]}, {'group_set': {'$all': [ObjectId(group_id)]}}, {'member_of': {'$nin': [grp_st._id]}}]})
    return obj_resources


@get_execution_time
def get_gapps(default_gapp_listing=False, already_selected_gapps=[]):
    """Returns list of GApps.

    Arguments:
    default_gapp_listing -- (Optional argument)
        - This is to decide which list should be considered for listing GAPPs;
        that is, in menu-bar and GAPPs selection menu for a given group
        - True: DEFAULT_GAPPS (menu-bar)
            - At present used in listing GAPPS whenever a new group is created
        - False: WORKING_GAPPS (selection-menu)
            - At present used in listing GAPPS for setting-up GAPPS for a group

    already_selected_gapps -- (Optional argument)
        - List of GApps already set for a given group in form of
        dictionary variable
        - If specified, then these listed GApps are excluded from
        the list of GApps returned by this function

    Returns:
        - List of GApps where each GApp is in form of node/dictionary
    """
    gapps_list = []

    global DEFAULT_GAPPS_LIST
    gapps_list = DEFAULT_GAPPS_LIST

    if not gapps_list or not default_gapp_listing:
        # If DEFAULT_GAPPS_LIST not set (i.e. empty)
        # Or we need to setup list for selection purpose of GAPPS
        # for a group
        gapps_list = WORKING_GAPPS

        # If already_selected_gapps is non-empty,
        # Then append their names in list of GApps to be excluded
        if already_selected_gapps:
            gapps_list_remove = gapps_list.remove
            for each_gapp in already_selected_gapps:
                gapp_name = each_gapp["name"]

                if gapp_name in gapps_list:
                    gapps_list_remove(gapp_name)

    # Find all GAPPs
    meta_type = node_collection.one({
        "_type": "MetaType", "name": META_TYPE[0]
    })
    gapps_cur = None
    gapps_cur = node_collection.find({
        "_type": "GSystemType", "member_of": meta_type._id,
        "name": {"$in": gapps_list}
    }).sort("created_at")

    return list(gapps_cur)


@get_execution_time
def forum_notification_status(group_id,user_id):
  """Checks forum notification turn off for an author object
  """
  try:
    grp_obj = node_collection.one({'_id': ObjectId(group_id)})
    auth_obj = node_collection.one({'_id': ObjectId(user_id)})
    at_user_pref = node_collection.one({'$and': [{'_type': 'AttributeType'}, {'name': 'user_preference_off'}]})
    list_at_pref=[]
    if at_user_pref:
      poss_attrs=auth_obj.get_possible_attributes(at_user_pref._id)
      if poss_attrs:
        if 'user_preference_off' in poss_attrs:
          list_at_pref=poss_attrs['user_preference_off']['object_value']
        if grp_obj in list_at_pref:
          return False
        else:
          return True
    return True
  except Exception as e:
    print "Exception in forum notification status check "+str(e)


@get_execution_time
def get_forum_repl_type(forrep_id):
  forum_st = node_collection.one({'$and': [{'_type': 'GSystemType'}, {'name': GAPPS[5]}]})
  obj = node_collection.one({'_id': ObjectId(forrep_id)})
  if obj:
    if forum_st._id in obj.member_of:
      return "Forum"
    else:
      return "Reply"
  else:
    return "None"


@get_execution_time
def check_existing_group(group_name):
  if type(group_name) == 'unicode':
    colg = node_collection.find({'_type': u'Group', "name": group_name})
    if colg.count()>0:
      return True
    if ins_objectid.is_valid(group_name):    #if group_name holds group_id
      colg = node_collection.find({'_type': u'Group', "_id": ObjectId(group_name)})
    if colg.count()>0:
      return True
    else:
      colg = node_collection.find({'_type': {'$in':['Group', 'Author']}, "_id": ObjectId(group_name)})
      if colg.count()>0:
        return True      
  else:
    if ins_objectid.is_valid(group_name):     #if group_name holds group_id
      colg = node_collection.find({'_type': u'Group', "_id": ObjectId(group_name)})
      if colg.count()>0:
        return True
      colg = node_collection.find({'_type': {'$in':['Group', 'Author']}, "_id": ObjectId(group_name)})
      if colg.count()>0:
        return True
    else:
      colg = node_collection.find({'_type': {'$in':['Group', 'Author']}, "_id": group_name._id})
  if colg.count() >= 1:
    return True
  else:
    return False



@get_execution_time
def filter_drawer_nodes(nid, group_id=None):
  page_gst = node_collection.one({'_type': 'GSystemType', 'name': 'Page'})
  file_gst = node_collection.one({'_type': 'GSystemType', 'name': 'File'})
  Pandora_video_gst = node_collection.one({'_type': 'GSystemType', 'name': 'Pandora_video'})
  quiz_gst = node_collection.one({'_type': 'GSystemType', 'name': 'Quiz'})
  quizItem_gst = node_collection.one({'_type': "GSystemType", 'name': "QuizItem"})
  query = None

  if group_id:
    query = {'_type': {'$in': ['GSystem', 'File']}, 'group_set': ObjectId(group_id), 
                'collection_set': {'$exists': True, '$not': {'$size': 0}, '$in':[ObjectId(nid)]},
                'member_of': {'$in': [page_gst._id,file_gst._id,Pandora_video_gst._id,quiz_gst._id,quizItem_gst._id] }
            }

  else:
    query = {'_type': {'$in': ['GSystem', 'File']},'collection_set': {'$exists': True, '$not': {'$size': 0}, '$in':[ObjectId(nid)]},
            'member_of': {'$in': [page_gst._id,file_gst._id,Pandora_video_gst._id,quiz_gst._id,quizItem_gst._id] }
            }                   

  nodes = node_collection.find(query)

  # Remove parent nodes in which current node exists

  
  def filter_nodes(parents, group_id=None):  
    length = []
    if parents:
      length.extend(parents)

      inner_parents = []
      for each in parents:
        if group_id:
          query = {'_type': {'$in': ['GSystem', 'File']}, 'group_set': ObjectId(group_id), 
                    'collection_set': {'$exists': True, '$not': {'$size': 0}, '$in':[ObjectId(each)]},
                    'member_of': {'$in': [page_gst._id,file_gst._id,Pandora_video_gst._id,quiz_gst._id,quizItem_gst._id] }
                  }
        else:
          query = {'_type': {'$in': ['GSystem', 'File']},
                    'collection_set': {'$exists': True, '$not': {'$size': 0}, '$in':[ObjectId(each)]},
                    'member_of': {'$in': [page_gst._id,file_gst._id,Pandora_video_gst._id,quiz_gst._id,quizItem_gst._id] }
                  }

        nodes = node_collection.find(query)
        if nodes.count() > 0:
          for k in nodes:
            inner_parents.append(k._id) 
   
      for each in inner_parents:
        if each not in parents:
          parents.append(each)

      if set(length) != set(parents):
        parents = filter_nodes(parents, group_id)
        return parents        
      else:
        return parents

  parents_list = []
  if nodes.count() > 0: 
    for each in nodes:
      parents_list.append(each._id)

    parents = filter_nodes(parents_list, group_id)    
    return parents 
  else:
    return parents_list


@get_execution_time
def get_drawers(group_id, nid=None, nlist=[], page_no=1, checked=None, **kwargs):
    """Get both drawers-list.
    """
    dict_drawer = {}
    dict1 = {}
    dict2 = []  # Changed from dictionary to list so that it's content are reflected in a sequential-order
    filtering = []

    drawer = None    
    if checked:
      if nid:
        filtering = filter_drawer_nodes(nid, group_id)

      if checked == "Page":
        gst_page_id = node_collection.one({'_type': "GSystemType", 'name': "Page"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$all':[gst_page_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})
        
      elif checked == "File":         
        drawer = node_collection.find({'_type': u"File", '_id': {'$nin': filtering},'group_set': {'$all': [ObjectId(group_id)]}})
        
      elif checked == "Image":
        gst_image_id = node_collection.one({'_type': "GSystemType", 'name': "Image"})._id
        drawer = node_collection.find({'_type': u"File", '_id': {'$nin': filtering},'member_of': {'$in':[gst_image_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "Video":         
        gst_video_id = node_collection.one({'_type': "GSystemType", 'name': "Video"})._id
        drawer = node_collection.find({'_type': u"File", '_id': {'$nin': filtering},'member_of': {'$in':[gst_video_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "Quiz":
        # For prior-node-list
        drawer = node_collection.find({'_type': {'$in' : [u"GSystem", u"File"]}, '_id': {'$nin': filtering},'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "QuizObj" or checked == "assesses":
        # For collection-list
        gst_quiz_id = node_collection.one({'_type': "GSystemType", 'name': "Quiz"})._id
        gst_quiz_item_id = node_collection.one({'_type': "GSystemType", 'name': "QuizItem"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$in':[gst_quiz_id, gst_quiz_item_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "OnlyQuiz":
        gst_quiz_id = node_collection.one({'_type': "GSystemType", 'name': "Quiz"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$all':[gst_quiz_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "QuizItem":
        gst_quiz_item_id = node_collection.one({'_type': "GSystemType", 'name': "QuizItem"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$all':[gst_quiz_item_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "Group":
        drawer = node_collection.find({'_type': u"Group", '_id': {'$nin': filtering} })

      elif checked == "Forum":
        gst_forum_id = node_collection.one({'_type': "GSystemType", 'name': "Forum"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$all':[gst_forum_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "Module":
        gst_module_id = node_collection.one({'_type': "GSystemType", 'name': "Module"})._id
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$all':[gst_module_id]}, 'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "Pandora Video":
        gst_pandora_video_id = node_collection.one({'_type': "GSystemType", 'name': "Pandora_video"})._id
        drawer = node_collection.find({'_type': u"File", '_id': {'$nin': filtering},'member_of': {'$all':[gst_pandora_video_id]}, 'group_set': {'$all': [ObjectId(group_id)]}}).limit(50)

      elif checked == "Theme":
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$in':[theme_GST._id, topic_GST._id]}, 'group_set': {'$all': [ObjectId(group_id)]}}) 

      elif checked == "theme_item":
        drawer = node_collection.find({'_type': u"GSystem", '_id': {'$nin': filtering},'member_of': {'$in':[theme_item_GST._id, topic_GST._id]}, 'group_set': {'$all': [ObjectId(group_id)]}}) 

      elif checked == "Topic":
        drawer = node_collection.find({'_type': {'$in' : [u"GSystem", u"File"]}, '_id': {'$nin': filtering},'member_of':{'$nin':[theme_GST._id, theme_item_GST._id, topic_GST._id]},'group_set': {'$all': [ObjectId(group_id)]}})

      elif checked == "RelationType" or checked == "CourseUnits":
        # Special case used while dealing with RelationType widget
        if kwargs.has_key("left_drawer_content"):
          drawer = kwargs["left_drawer_content"]
    else:
      # For heterogeneous collection
      if checked == "RelationType" or checked == "CourseUnits":
        # Special case used while dealing with RelationType widget
        drawer = checked

      else:
        filtering = filter_drawer_nodes(nid, group_id)
        Page = node_collection.one({'_type': 'GSystemType', 'name': 'Page'})
        File = node_collection.one({'_type': 'GSystemType', 'name': 'File'})
        Quiz = node_collection.one({'_type': "GSystemType", 'name': "Quiz"})
        drawer = node_collection.find({'_type': {'$in' : [u"GSystem", u"File"]}, 
                                       '_id': {'$nin': filtering},'group_set': {'$all': [ObjectId(group_id)]}, 
                                       'member_of':{'$in':[Page._id,File._id,Quiz._id]}
                                      })
    if checked != "RelationType" and checked != "CourseUnits":
        paged_resources = paginator.Paginator(drawer, page_no, 10)
        drawer.rewind()

    if (nid is None) and (not nlist):
      for each in drawer:
        dict_drawer[each._id] = each

    elif (nid is None) and (nlist):
      for each in drawer:
        if each._id not in nlist:
          dict1[each._id] = each

      for oid in nlist:
        obj = node_collection.one({'_id': oid})
        dict2.append(obj)

      dict_drawer['1'] = dict1
      dict_drawer['2'] = dict2

    else:
      for each in drawer:

        if each._id != nid:
          if each._id not in nlist:
            dict1[each._id] = each
          
      for oid in nlist: 
        obj = node_collection.one({'_id': oid})
        dict2.append(obj)

      dict_drawer['1'] = dict1
      dict_drawer['2'] = dict2

    if checked == "RelationType" or checked == "CourseUnits":
      return dict_drawer

    else:
      return dict_drawer, paged_resources


# get type of resourc
@get_execution_time
def get_resource_type(request,node_id):
  get_resource_type=collection.Node.one({'_id':ObjectId(node_id)})
  get_type=get_resource_type._type
  return get_type 
                          


@get_execution_time
def get_translate_common_fields(request, get_type, node, group_id, node_type, node_id):
  """ retrive & update the common fields required for translation of the node """

  usrid = int(request.user.id)
  content_org = request.POST.get('content_org')
  tags = request.POST.get('tags')
  name = request.POST.get('name')
  tags = request.POST.get('tags')
  access_policy = request.POST.get('access_policy')
  usrid = int(request.user.id)
  language= request.POST.get('lan')
  if get_type == "File":
    get_parent_node = node_collection.one({'_id': ObjectId(node_id)})
    get_mime_type=get_parent_node.mime_type
    get_fs_file_ids=get_parent_node.fs_file_ids
    node.mime_type=get_mime_type
    node.fs_file_ids=get_fs_file_ids
 
  if not ('_id' in node):
    node.created_by = usrid
    if get_type == "File":
        get_node_type = node_collection.one({"_type": "GSystemType", 'name': get_type})
        node.member_of.append(get_node_type._id)
        if 'image' in get_mime_type:
          get_image_type = node_collection.one({"_type": "GSystemType", 'name': 'Image'})
          node.member_of.append(get_image_type._id)
        if 'video' in get_mime_type:
          get_video_type = node_collection.one({"_type": "GSystemType", 'name': 'Video'})
          node.member_of.append(get_video_type._id)
        
    else:
      node.member_of.append(node_type._id)
 
  node.name = unicode(name)
  node.language=unicode(language)
 
  node.modified_by = usrid
  if access_policy:
    node.access_policy = access_policy
 
  if usrid not in node.contributors:
    node.contributors.append(usrid)

  group_obj = node_collection.one({'_id': ObjectId(group_id)})
  if group_obj._id not in node.group_set:
    node.group_set.append(group_obj._id)
  if tags:
    node.tags = [unicode(t.strip()) for t in tags.split(",") if t != ""]

  if tags:
    node.tags = [unicode(t.strip()) for t in tags.split(",") if t != ""]

  if content_org:
    node.content_org = unicode(content_org)
    node.name=unicode(name)
    # Required to link temporary files with the current user who is modifying this document
    usrname = request.user.username
    filename = slugify(name) + "-" + usrname + "-" + ObjectId().__str__()
    node.content = org2html(content_org, file_prefix=filename)


@get_execution_time
def get_node_common_fields(request, node, group_id, node_type, coll_set=None):
  """Updates the retrieved values of common fields from request into the given node."""

  group_obj = node_collection.one({'_id': ObjectId(group_id)})
  # theme_item_GST = node_collection.one({'_type': 'GSystemType', 'name': 'theme_item'})
  # topic_GST = node_collection.one({'_type': 'GSystemType', 'name': 'Topic'})
  collection = None

  if coll_set:
      if "Theme" in coll_set.member_of_names_list:
        node_type = theme_GST
      if "theme_item" in coll_set.member_of_names_list:
        node_type = theme_item_GST
      if "Topic" in coll_set.member_of_names_list:
        node_type = topic_GST

      name = request.POST.get('name_'+ str(coll_set._id),"")
      content_org = request.POST.get(str(coll_set._id),"")
      tags = request.POST.get('tags'+ str(coll_set._id),"")
     
  else:    
    name =request.POST.get('name','').strip()
    content_org = request.POST.get('content_org')
    tags = request.POST.get('tags')

  language= request.POST.get('lan')
  sub_theme_name = request.POST.get("sub_theme_name", '')
  add_topic_name = request.POST.get("add_topic_name", '')
  is_changed = False
  sub_theme_name = unicode(request.POST.get("sub_theme_name", ''))
  add_topic_name = unicode(request.POST.get("add_topic_name", ''))
  usrid = int(request.user.id)
  usrname = unicode(request.user.username)
  access_policy = request.POST.get("login-mode", '')
  right_drawer_list = []
  checked = request.POST.get("checked", '') 
  check_collection = request.POST.get("check_collection", '') 
  if check_collection:
    if check_collection == "collection":
      right_drawer_list = request.POST.get('collection_list','')
    elif check_collection == "prior_node":    
      right_drawer_list = request.POST.get('prior_node_list','')
    elif check_collection == "teaches":    
      right_drawer_list = request.POST.get('teaches_list','')
    elif check_collection == "assesses":    
      right_drawer_list = request.POST.get('assesses_list','')
    elif check_collection == "module":    
      right_drawer_list = request.POST.get('module_list','')


  map_geojson_data = request.POST.get('map-geojson-data')
  user_last_visited_location = request.POST.get('last_visited_location')
  altnames = request.POST.get('altnames', '')
  featured = request.POST.get('featured', '')

  if map_geojson_data:
    map_geojson_data = map_geojson_data + ","
    map_geojson_data = list(ast.literal_eval(map_geojson_data))
  else:
    map_geojson_data = []
  
  # --------------------------------------------------------------------------- For create only
  if not node.has_key('_id'):
    
    node.created_by = usrid
    
    if node_type._id not in node.member_of:
      node.member_of.append(node_type._id)
      if node_type.name == "Term":
        node.member_of.append(topic_GST._id)
        
     
    if group_obj._id not in node.group_set:
      node.group_set.append(group_obj._id)

    if access_policy == "PUBLIC":
      node.access_policy = unicode(access_policy)
    else:
      node.access_policy = unicode(access_policy)

    node.status = "PUBLISHED"

    is_changed = True
          
    # End of if
    specific_url = set_all_urls(node.member_of)
    node.url = specific_url

  if name:
    if node.name != name:
      node.name = name
      is_changed = True
  
  if altnames or request.POST.has_key("altnames"):
    if node.altnames != altnames:
      node.altnames = altnames
      is_changed = True

  if (featured == True) or (featured == False) :
    if node.featured != featured:
      node.featured = featured
      is_changed = True

  if sub_theme_name:
    if node.name != sub_theme_name:
      node.name = sub_theme_name
      is_changed = True
  
  if add_topic_name:
    if node.name != add_topic_name:
      node.name = add_topic_name
      is_changed = True

  #  language
  if language:
      node.language = unicode(language) 
  else:
      node.language = u"en"

  #  access_policy

  if access_policy:
    # Policy will be changed only by the creator of the resource
    # via access_policy(public/private) option on the template which is visible only to the creator
    if access_policy == "PUBLIC" and node.access_policy != access_policy:
        node.access_policy = u"PUBLIC"
        # print "\n Changed: access_policy (pu 2 pr)"
        is_changed = True
    elif access_policy == "PRIVATE" and node.access_policy != access_policy:
        node.access_policy = u"PRIVATE"
        # print "\n Changed: access_policy (pr 2 pu)"
        is_changed = True
  else:
      node.access_policy = u"PUBLIC"

  # For displaying nodes in home group as well as in creator group.
  user_group_obj = node_collection.one({'$and': [{'_type': ObjectId(group_id)}, {'name': usrname}]})

  if group_obj._id not in node.group_set:
      node.group_set.append(group_obj._id)
  else:
      if user_group_obj:
          if user_group_obj._id not in node.group_set:
              node.group_set.append(user_group_obj._id)

  #  tags
  if tags:
    tags_list = []

    for tag in tags.split(","):
      tag = unicode(tag.strip())

      if tag:
        tags_list.append(tag)

    if set(node.tags) != set(tags_list):
      node.tags = tags_list
      is_changed = True

  #  Build collection, prior node, teaches and assesses lists
  if check_collection:
    changed = build_collection(node, check_collection, right_drawer_list, checked)  
    if changed == True:
      is_changed = True
    
  #  org-content
  if content_org:
    if node.content_org != content_org:
      node.content_org = content_org
      
      # Required to link temporary files with the current user who is modifying this document
      usrname = request.user.username
      filename = slugify(name) + "-" + usrname + "-" + ObjectId().__str__()
      node.content = org2html(content_org, file_prefix=filename)
      is_changed = True

  # visited_location in author class
  if node.location != map_geojson_data:
    node.location = map_geojson_data # Storing location data
    is_changed = True
  
  if user_last_visited_location:
    user_last_visited_location = list(ast.literal_eval(user_last_visited_location))

    author = node_collection.one({'_type': "GSystemType", 'name': "Author"})
    user_group_location = node_collection.one({'_type': "Author", 'member_of': author._id, 'created_by': usrid, 'name': usrname})

    if user_group_location:
      if node._type == "Author" and user_group_location._id == node._id:
        if node['visited_location'] != user_last_visited_location:
          node['visited_location'] = user_last_visited_location
          is_changed = True

      else:
        user_group_location['visited_location'] = user_last_visited_location
        user_group_location.save()

  if is_changed:
    node.status = unicode("DRAFT")

    node.modified_by = usrid

    if usrid not in node.contributors:
      node.contributors.append(usrid)
  return is_changed


# ============= END of def get_node_common_fields() ==============

@get_execution_time
def build_collection(node, check_collection, right_drawer_list, checked):
  is_changed = False

  if check_collection == "prior_node":
    if right_drawer_list != '':
      # prior_node_list = [ObjectId(each.strip()) for each in prior_node_list.split(",")]
      right_drawer_list = [ObjectId(each.strip()) for each in right_drawer_list.split(",")]

      if node.prior_node != right_drawer_list:
        i = 0
        node.prior_node=[]
        while (i < len(right_drawer_list)):
          node_id = ObjectId(right_drawer_list[i])
          node_obj = node_collection.one({"_id": node_id})
          if node_obj:
            node.prior_node.append(node_id)
          
          i = i+1
        # print "\n Changed: prior_node"
        is_changed = True
    else:
      node.prior_node = []
      is_changed = True

  elif check_collection == "collection":
    #  collection
    if right_drawer_list != '':
      right_drawer_list = [ObjectId(each.strip()) for each in right_drawer_list.split(",")]

      nlist = node.collection_set

      # if set(node.collection_set) != set(right_drawer_list):
      if node.collection_set != right_drawer_list:
        i = 0
        node.collection_set = []
        # checking if each _id in collection_list is valid or not
        while (i < len(right_drawer_list)):
          node_id = ObjectId(right_drawer_list[i])
          node_obj = node_collection.one({"_id": node_id})
          if node_obj:
            if node_id not in nlist:
              nlist.append(node_id)  
            else:
              node.collection_set.append(node_id)  
              # After adding it to collection_set also make the 'node' as prior node for added collection element
              node_collection.collection.update({'_id': ObjectId(node_id), 'prior_node': {'$nin':[node._id]} },{'$push': {'prior_node': ObjectId(node._id)}})
          
          i = i+1

        for each in nlist:
          if each not in node.collection_set:
            node.collection_set.append(each)
            # After adding it to collection_set also make the 'node' as prior node for added collection element
            node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$nin':[node._id]} },{'$push': {'prior_node': ObjectId(node._id)}})

        # For removing collection elements from heterogeneous collection drawer only
        if not checked: 
          if nlist:
            for each in nlist:
              if each not in right_drawer_list:
                node.collection_set.remove(each)
                # Also for removing prior node element after removing collection element
                node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})

        else:
          if nlist and checked:
            if checked == "QuizObj":
              quiz = node_collection.one({'_type': 'GSystemType', 'name': "Quiz" })
              quizitem = node_collection.one({'_type': 'GSystemType', 'name': "QuizItem" })
              for each in nlist:
                obj = node_collection.one({'_id': ObjectId(each) })
                if quiz._id in obj.member_of or quizitem._id in obj.member_of:
                  if obj._id not in right_drawer_list:
                    node.collection_set.remove(obj._id)
                    # Also for removing prior node element after removing collection element
                    node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})

            elif checked == "Pandora Video":
              check = node_collection.one({'_type': 'GSystemType', 'name': 'Pandora_video' })
              for each in nlist:
                obj = node_collection.one({'_id': ObjectId(each) })
                if check._id == obj.member_of[0]:
                  if obj._id not in right_drawer_list:
                    node.collection_set.remove(obj._id)
                    node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})
            else:
              check = node_collection.one({'_type': 'GSystemType', 'name': unicode(checked) })
              for each in nlist:
                obj = node_collection.one({'_id': ObjectId(each) })
                if len(obj.member_of) < 2:
                  if check._id == obj.member_of[0]:
                    if obj._id not in right_drawer_list:
                      node.collection_set.remove(obj._id)
                      node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})
                else:
                  if check._id == obj.member_of[1]: 
                    if obj._id not in right_drawer_list:
                      node.collection_set.remove(obj._id)
                      node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})

        is_changed = True

    else:
      if node.collection_set and checked:
        if checked == "QuizObj":
          quiz = node_collection.one({'_type': 'GSystemType', 'name': "Quiz" })
          quizitem = node_collection.one({'_type': 'GSystemType', 'name': "QuizItem" })
          for each in node.collection_set:
            obj = node_collection.one({'_id': ObjectId(each) })
            if quiz._id in obj.member_of or quizitem._id in obj.member_of:
              node.collection_set.remove(obj._id)
              node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})
        elif checked == "Pandora Video":
          check = node_collection.one({'_type': 'GSystemType', 'name': 'Pandora_video' })
          for each in node.collection_set:
            obj = node_collection.one({'_id': ObjectId(each) })
            if check._id == obj.member_of[0]:
              node.collection_set.remove(obj._id)
              node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})
        else:
          check = node_collection.one({'_type': 'GSystemType', 'name': unicode(checked) })
          for each in node.collection_set:
            obj = node_collection.one({'_id': ObjectId(each) })
            if len(obj.member_of) < 2:
              if check._id == obj.member_of[0]:
                node.collection_set.remove(obj._id)
                node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})
            else:
              if check._id == obj.member_of[1]: 
                node.collection_set.remove(obj._id)
                node_collection.collection.update({'_id': ObjectId(each), 'prior_node': {'$in':[node._id]} },{'$pull': {'prior_node': ObjectId(node._id)}})

      else:
        node.collection_set = []
      
      is_changed = True

  elif check_collection == "teaches":
    # Teaches
    if right_drawer_list != '':

      right_drawer_list = [ObjectId(each.strip()) for each in right_drawer_list.split(",")]

      relationtype = node_collection.one({"_type": "RelationType", "name": "teaches"})
      list_grelations = triple_collection.find({"_type": "GRelation", "subject": node._id, "relation_type.$id": relationtype._id})
      for relation in list_grelations:
        # nlist.append(ObjectId(relation.right_subject))
        relation.delete()

      if right_drawer_list:
        list_grelations.rewind()
        i = 0

        while (i < len(right_drawer_list)):
          node_id = ObjectId(right_drawer_list[i])
          node_obj = node_collection.one({"_id": node_id})
          if node_obj:
            create_grelation(node._id,relationtype,node_id)
          i = i+1      
        
        # print "\n Changed: teaches_list"
        is_changed = True
    else:
      relationtype = node_collection.one({"_type": "RelationType", "name": "teaches"})
      list_grelations = triple_collection.find({"_type": "GRelation", "subject": node._id, "relation_type.$id": relationtype._id})
      for relation in list_grelations:
        relation.delete()

      is_changed = True

  elif check_collection == "assesses":
    # Assesses
    if right_drawer_list != '':
      right_drawer_list = [ObjectId(each.strip()) for each in right_drawer_list.split(",")]

      relationtype = node_collection.one({"_type": "RelationType", "name": "assesses"})
      list_grelations = triple_collection.find({"_type": "GRelation", "subject": node._id, "relation_type.$id": relationtype._id})
      for relation in list_grelations:
        relation.delete()

      if right_drawer_list:
        list_grelations.rewind()
        i = 0

        while (i < len(right_drawer_list)):
          node_id = ObjectId(right_drawer_list[i])
          node_obj = node_collection.one({"_id": node_id})
          if node_obj:
            create_grelation(node._id,relationtype,node_id)
          i = i + 1

        # print "\n Changed: teaches_list"
        is_changed = True
    else:
      relationtype = node_collection.one({"_type": "RelationType", "name": "assesses"})
      list_grelations = triple_collection.find({"_type": "GRelation", "subject": node._id, "relation_type.$id": relationtype._id})
      for relation in list_grelations:
        relation.delete()

      is_changed = True

  # elif check_collection == "module":
    #  Module
    # if right_drawer_list != '':
    #   right_drawer_list = [ObjectId(each.strip()) for each in right_drawer_list.split(",")]

    #   if set(node.collection_set) != set(right_drawer_list):
    #     i = 0
    #     while (i < len(right_drawer_list)):
    #       node_id = ObjectId(right_drawer_list[i])
    #       node_obj = node_collection.one({"_id": node_id})
    #       if node_obj:
    #         if node_id not in node.collection_set:
    #           node.collection_set.append(node_id)
          
    #       i = i+1
        # print "\n Changed: module_list"
        # is_changed = True
    # else:
      # node.module_set = []
      # is_changed = True
  if is_changed == True:
    return True
  else:
    return False


@get_execution_time
def get_versioned_page(node):
    rcs = RCS()
    fp = history_manager.get_file_path(node)
    cmd= 'rlog  %s' % \
  (fp)
    rev_no =""
    proc1=subprocess.Popen(cmd,shell=True,
        stdout=subprocess.PIPE)
    for line in iter(proc1.stdout.readline,b''):
      if line.find('revision')!=-1 and line.find('selected') == -1:
          rev_no=string.split(line,'revision')
          rev_no=rev_no[1].strip( '\t\n\r')
          rev_no=rev_no.split()[0]
      if line.find('status')!=-1:
          up_ind=line.find('status')
          if line.find(('PUBLISHED'),up_ind) !=-1:
	       rev_no=rev_no.split()[0]
               node=history_manager.get_version_document(node,rev_no)
               proc1.kill()
               return (node,rev_no)    
      if rev_no == '1.1':
           node=history_manager.get_version_document(node,'1.1')
           proc1.kill()
           return(node,'1.1')



@get_execution_time
def get_user_page(request,node):
    ''' function gives the last docment submited by the currently logged in user either it
	can be drafted or published
'''
    rcs = RCS()
    fp = history_manager.get_file_path(node)
    cmd= 'rlog  %s' % \
	(fp)
    rev_no =""
    proc1=subprocess.Popen(cmd,shell=True,
				stdout=subprocess.PIPE)
    for line in iter(proc1.stdout.readline,b''):
       
       if line.find('revision')!=-1 and line.find('selected') == -1:

          rev_no=string.split(line,'revision')
          rev_no=rev_no[1].strip( '\t\n\r')
          rev_no=rev_no.strip(' ')
       if line.find('updated')!=-1:
          up_ind=line.find('updated')
          if line.find(str(request.user),up_ind) !=-1:
               rev_no=rev_no.strip(' ')
               node=history_manager.get_version_document(node,rev_no)
               proc1.kill()
               return (node,rev_no)    
       if rev_no == '1.1':
           node=history_manager.get_version_document(node,'1.1')
           proc1.kill()
           return(node,'1.1')

@get_execution_time
def get_page(request,node):
  ''' 
  function to filter between the page to be displyed to user 
  i.e which page to be shown to the user drafted or the published page
  if a user have some drafted content then he would be shown his own drafted contents 
  and if he has published his contents then he would be shown the current published contents
  '''
  username =request.user
  node1,ver1=get_versioned_page(node)
  node2,ver2=get_user_page(request,node)     
  
  if  ver2 != '1.1':                           
	    if node2 is not None:
                if node2.status == 'PUBLISHED':
                  
			if float(ver2) > float(ver1):			
				return (node2,ver2)
			elif float(ver2) < float(ver1):
				return (node1,ver1)
			elif float(ver2) == float(ver1):
				return(node1,ver1)
		elif node2.status == 'DRAFT':
                       #========== conditions for Group===============#

                        if   node._type == "Group":
			    
			    count=check_page_first_creation(request,node2)
                            if count == 1:
                                return (node1,ver1)
                            elif count == 2:
                               	return (node2,ver2)
                        
                        return (node2,ver2)  
	    else:
                        
			return(node1,ver1)		
	    
  else:
         
        # if node._type == "GSystem" and node1.status == "DRAFT":
        #     if node1.created_by ==request.user.id:
        #           return (node2,ver2)
        #      else:
	#	   return (node2,ver2)
         return (node1,ver1)

@get_execution_time
def check_page_first_creation(request,node):
    ''' function to check wheather the editing is performed by the user very first time '''
    rcs = RCS()
    fp = history_manager.get_file_path(node)
    cmd= 'rlog  %s' % \
	(fp)
    rev_no =""
    count=0
    proc1=subprocess.Popen(cmd,shell=True,
				stdout=subprocess.PIPE)
    for line in iter(proc1.stdout.readline,b''):
         if line.find('updated')!=-1 or line.find('created')!=-1:
          if line.find(str(request.user))!=-1:
               count =count+1
               if count ==2:
                proc1.kill()
               	return (count)
    proc1.kill()
    if count == 1:
	return(count)     


@get_execution_time
def tag_info(request, group_id, tagname = None):
    '''
    Function to get all the resources related to tag
    '''

    group_name, group_id = get_group_name_id(group_id)

    cur = None
    total = None
    total_length = None  
    yesterdays_result = []
    week_ago_result = []
    search_result = []
    group_cur_list = [] #for AutheticatedUser
    today = date.today()
    yesterdays_search = {date.today()-timedelta(days=1)}
    week_ago_search = {date.today()-timedelta(days=7)}
    locale.setlocale(locale.LC_ALL, '')
    userid = request.user.id
    collection = get_database()[Node.collection_name]

    if not tagname:
        tagname = request.GET["search"].lower()

    if request.user.is_superuser:  #Superuser can see private an public files 
        if tagname:
            cur = collection.Node.find( {'tags':{'$in':[tagname]},
                                          # '$or':[   {'access_policy':u'PUBLIC'},
                                          #           {'access_policy':u'PRIVATE'}
                                          #       ],   
                                         'status':u'PUBLISHED'
                                    }
                                 )
            for every in cur:
                search_result.append(every)

        total = len(search_result)
        total = locale.format("%d", total, grouping=True)
        if len(search_result) == 0:
            total_length = len(search_result)    

    elif request.user.is_authenticated():   #Autheticate user can see all public files  
        group_cur = collection.Node.find({'_type':'Group',
                                           '$or':[ {'created_by':userid},
                                                 {'group_admin':userid},
                                                 {'author_set':userid},
                                                 {'group_type':u'PUBLIC'},
                                               ]
                                    }      
                                )
        for each in group_cur:
            group_cur_list.append(each._id)

        if tagname and (group_id in group_cur_list):
            cur = collection.Node.find( {'tags':{'$in':[tagname]},
                                         'group_set':{'$in': [group_id]},
                                         'status':u'PUBLISHED'
                                    }
                             )
            for every in cur: 
                search_result.append(every)

        total = len(search_result)
        total = locale.format("%d", total, grouping=True)
        if len(search_result) == 0:
            total_length = len(search_result)

    else: #Unauthenticated user can see all public files.
        if tagname:
            cur = collection.Node.find( { 'tags':{'$in':[tagname]},
                                           'access_policy':u'PUBLIC',
                                           'status':u'PUBLISHED'
                                        }
                                 )
            for every in cur:
                search_result.append(every)

        total = len(search_result)
        total = locale.format("%d", total, grouping=True)
        if len(search_result) == 0:
            total_length = len(search_result)
    
    return render_to_response(
        "ndf/tag_browser.html",
        {'group_id': group_id, 'groupid': group_id, 'search_result':search_result ,'tagname':tagname,'total':total,'total_length':total_length},
        context_instance=RequestContext(request)
    )


#code for merging two text Documents
import difflib
@get_execution_time
def diff_string(original,revised):
        
        # build a list of sentences for each input string
        original_text = _split_with_maintain(original)
        new_text = _split_with_maintain(revised)
        a=original_text + new_text
        strings='\n'.join(a)
        #f=(strings.replace("*", ">").replace("-","="))
        #f=(f.replace("> 1 >",">").replace("= 1 =","="))

        
        return strings


STANDARD_REGEX = '[.!?]'
def _split_with_maintain(value, treat_trailing_spaces_as_sentence = True, split_char_regex = STANDARD_REGEX):
        result = []
        check = value
        
        # compile regex
        rx = re.compile(split_char_regex)
        
        # traverse the string
        while len(check) > 0:
            found  = rx.search(str(check))
            if found == None:
                result.append(check)
                break
            
            idx = found.start()
            result.append(str(check[:idx]))            # append the string
            result.append(str(check[idx:idx+1]))    # append the puncutation so changing ? to . doesn't invalidate the whole sentence
            check = check[idx + 1:]
            
            # group the trailing spaces if requested
            if treat_trailing_spaces_as_sentence:
                space_idx = 0
                while True:
                    if space_idx >= len(check):
                        break
                    if check[space_idx] != " ":
                        break
                    space_idx += 1
                
                if space_idx != 0:
                    result.append(check[0:space_idx])
            
                check = check[space_idx:]
            
        return result


@get_execution_time
def update_mobwrite_content_org(node_system):   
  '''
	on revert or merge of nodes,a content_org is synced to mobwrite object
	input : 
		node
  ''' 
  system = node_system
  filename = TextObj.safe_name(str(system._id))
  textobj = TextObj.objects.filter(filename=filename)
  content_org = system.content_org
  if textobj:
    textobj = TextObj.objects.get(filename=filename)
    textobj.text = content_org
    textobj.save()
  else:
    textobj = TextObj(filename=filename,text=content_org)
    textobj.save()
  return textobj



@get_execution_time
def cast_to_data_type(value, data_type):
    '''
    This method will cast first argument: "value" to second argument: "data_type" and returns catsed value.
    '''
    # print "\n\t\tin method: ", value, " == ", data_type

    value = value.strip()
    casted_value = value

    if data_type == "unicode":
        casted_value = unicode(value)

    elif data_type == "basestring":
        casted_value = str(value)

    elif (data_type == "int") and str(value):
        casted_value = int(value) if (str.isdigit(str(value))) else value

    elif (data_type == "float") and str(value):
        casted_value = float(value) if (str.isdigit(str(value))) else value

    elif (data_type == "long") and str(value):
        casted_value = long(value) if (str.isdigit(str(value))) else value

    elif data_type == "bool" and str(value): # converting unicode to int and then to bool
        if (str.isdigit(str(value))):
            casted_value = bool(int(value))
        elif unicode(value) in [u"True", u"False"]:
            if (unicode(value) == u"True"):
                casted_value = True
            elif (unicode(value) == u"False"):
                casted_value = False

    elif (data_type == "list") and (not isinstance(value, list)):
        value = value.replace("\n", "").split(",")
        
        # check for complex list type like: [int] or [unicode]
        if isinstance(data_type, list) and len(data_type) and isinstance(data_type[0], type):
            casted_value = [data_type[0](i.strip()) for i in value if i]

        else:  # otherwise normal list
            casted_value = [i.strip() for i in value if i]

    elif data_type == "datetime.datetime":
        # "value" should be in following example format
        # In [10]: datetime.datetime.strptime( "11/12/2014", "%d/%m/%Y")
        # Out[10]: datetime.datetime(2014, 12, 11, 0, 0)
        casted_value = datetime.datetime.strptime(value, "%d/%m/%Y")
        
    return casted_value



@get_execution_time
def get_node_metadata(request, node, **kwargs):
    '''
    Getting list of updated GSystems with kwargs arguments.
    Pass is_changed=True as last/third argument while calling this/get_node_metadata method.
    Example: 
      updated_ga_nodes = get_node_metadata(request, node_obj, GST_FILE_OBJ, is_changed=True)

    '''
    attribute_type_list = ["age_range", "audience", "timerequired",
                           "interactivitytype", "basedonurl", "educationaluse",
                           "textcomplexity", "readinglevel", "educationalsubject",
                           "educationallevel", "curricular", "educationalalignment",
                           "adaptation_of", "other_contributors", "creator", "source"
                          ]

    if "is_changed" in kwargs:
        updated_ga_nodes = []

    if('_id' in node):

        for atname in attribute_type_list:

            field_value = request.POST.get(atname, "")
            at = node_collection.one({"_type": "AttributeType", "name": atname})

            if at:

                field_value = cast_to_data_type(field_value, at["data_type"])

                if "is_changed" in kwargs:
                    temp_res = create_gattribute(node._id, at, field_value, is_changed=True)
                    if temp_res["is_changed"]:  # if value is true
                        updated_ga_nodes.append(temp_res)
              
                else:
                    create_gattribute(node._id, at, field_value)
    
    if "is_changed" in kwargs:
        return updated_ga_nodes



@get_execution_time
def create_grelation_list(subject_id, relation_type_name, right_subject_id_list):
    # function to create grelations for new ones and delete old ones.
    relationtype = node_collection.one({"_type": "RelationType", "name": unicode(relation_type_name)})
    # list_current_grelations = triple_collection.find({"_type":"GRelation","subject":subject_id,"relation_type":relationtype})
    # removes all existing relations given subject and relation type and then creates again.
    triple_collection.collection.remove({"_type": "GRelation", "subject": subject_id, "relation_type.$id": relationtype._id})

    for relation_id in right_subject_id_list:
        create_grelation(ObjectId(subject_id), relationtype, ObjectId(relation_id))
        # gr_node = triple_collection.collection.GRelation()
        # gr_node.subject = ObjectId(subject_id)
        # gr_node.relation_type = relationtype
        # gr_node.right_subject = ObjectId(relation_id)
        # gr_node.status = u"PUBLISHED"
        # gr_node.save()


	
	
	for relation_id in right_subject_id_list:
	    
	    gr_node = collection.GRelation()
            gr_node.subject = ObjectId(subject_id)
            gr_node.relation_type = relationtype
            gr_node.right_subject = ObjectId(relation_id)
	    gr_node.status = u"PUBLISHED"
            gr_node.save()
		

@get_execution_time
def get_widget_built_up_data(at_rt_objectid_or_attr_name_list, node, type_of_set=[]):
  """
  Returns data in list of dictionary format which is required for building html widget.
  This data is used by html_widget template-tag.
  """
  if not isinstance(at_rt_objectid_or_attr_name_list, list):
    at_rt_objectid_or_attr_name_list = [at_rt_objectid_or_attr_name_list]

  if not type_of_set:
    node["property_order"] = []
    gst_nodes = node_collection.find({'_type': "GSystemType", '_id': {'$in': node["member_of"]}}, {'type_of': 1, 'property_order': 1})
    for gst in gst_nodes:
      for type_of in gst["type_of"]:
        if type_of not in type_of_set:
          type_of_set.append(type_of)

      for po in gst["property_order"]:
        if po not in node["property_order"]:
          node["property_order"].append(po)

  BASE_FIELD_METADATA = {
    'name': {'name': "name", '_type': "BaseField", 'altnames': "Name", 'required': True},
    'content_org': {'name': "content_org", '_type': "BaseField", 'altnames': "Describe", 'required': False},
    # 'featured': {'name': "featured", '_type': "BaseField", 'altnames': "Featured"},
    'location': {'name': "location", '_type': "BaseField", 'altnames': "Location", 'required': False},
    'status': {'name': "status", '_type': "BaseField", 'altnames': "Status", 'required': False},
    'tags': {'name': "tags", '_type': "BaseField", 'altnames': "Tags", 'required': False}
  }

  widget_data_list = []
  for at_rt_objectid_or_attr_name in at_rt_objectid_or_attr_name_list:
    if type(at_rt_objectid_or_attr_name) == ObjectId: #ObjectId.is_valid(at_rt_objectid_or_attr_name):
      # For attribute-field(s) and/or relation-field(s)
      
      field = node_collection.one({'_id': ObjectId(at_rt_objectid_or_attr_name)}, {'_type': 1, 'subject_type': 1, 'object_type': 1, 'name': 1, 'altnames': 1, 'inverse_name': 1})

      altnames = u""
      value = None
      data_type = None
      if field._type == RelationType or field._type == "RelationType":
        # For RelationTypes
        if set(node["member_of"]).issubset(field.subject_type):
          # It means we are dealing with normal relation & 
          data_type = node.structure[field.name]
          value = node[field.name]
          if field.altnames:
            if ";" in field.altnames:
              altnames = field.altnames.split(";")[0]
            else:
              altnames = field.altnames

        elif set(node["member_of"]).issubset(field.object_type):
          # It means we are dealing with inverse relation
          data_type = node.structure[field.inverse_name]
          value = node[field.inverse_name]
          if field.altnames:
            if ";" in field.altnames:
              altnames = field.altnames.split(";")[1]
            else:
              altnames = field.altnames

        elif type_of_set:
          # If current node's GST is not in subject_type
          # Search for that GST's type_of field value in subject_type
          for each in type_of_set:
            if each in field.subject_type:
              data_type = node.structure[field.name]
              value = node[field.name]
              if field.altnames:
                if ";" in field.altnames:
                  altnames = field.altnames.split(";")[0]
                else:
                  altnames = field.altnames

            elif each in field.object_type:
              data_type = node.structure[field.inverse_name]
              value = node[field.inverse_name]
              if field.altnames:
                if ";" in field.altnames:
                  altnames = field.altnames.split(";")[0]
                else:
                  altnames = field.altnames

      else:
        # For AttributeTypes
        altnames = field.altnames
        data_type = node.structure[field.name]
        value = node[field.name]

      widget_data_list.append({ '_type': field._type, # It's only use on details-view template; overridden in ndf_tags html_widget()
                              '_id': field._id, 
                              'data_type': data_type,
                              'name': field.name, 'altnames': altnames,
                              'value': value
                            })

    else:
      # For node's base-field(s)

      # widget_data_list.append([node['member_of'], BASE_FIELD_METADATA[at_rt_objectid_or_attr_name], node[at_rt_objectid_or_attr_name]])
      widget_data_list.append({ '_type': BASE_FIELD_METADATA[at_rt_objectid_or_attr_name]['_type'],
                              'data_type': node.structure[at_rt_objectid_or_attr_name],
                              'name': at_rt_objectid_or_attr_name, 'altnames': BASE_FIELD_METADATA[at_rt_objectid_or_attr_name]['altnames'],
                              'value': node[at_rt_objectid_or_attr_name],
                              'required': BASE_FIELD_METADATA[at_rt_objectid_or_attr_name]['required']
                            })

  return widget_data_list



@get_execution_time
def get_property_order_with_value(node):
  new_property_order = []
  demo = None

  if '_id' in node:
    demo = node_collection.one({'_id': node._id})

  else:
    demo = eval("node_collection.collection"+"."+node['_type'])()
    demo["member_of"] = node["member_of"]

  if demo["_type"] not in ["MetaType", "GSystemType", "AttributeType", "RelationType"]:
    # If GSystems found, then only perform following statements
    
    demo["property_order"] = []
    type_of_set = []
    gst_nodes = node_collection.find({'_type': "GSystemType", '_id': {'$in': demo["member_of"]}}, {'type_of': 1, 'property_order': 1})
    for gst in gst_nodes:
      for type_of in gst["type_of"]:
        if type_of not in type_of_set:
          type_of_set.append(type_of)

      for po in gst["property_order"]:
        if po not in demo["property_order"]:
          demo["property_order"].append(po)

    demo.get_neighbourhood(node["member_of"])

    for tab_name, list_field_id_or_name in demo['property_order']:
      list_field_set = get_widget_built_up_data(list_field_id_or_name, demo, type_of_set)
      new_property_order.append([tab_name, list_field_set])

    demo["property_order"] = new_property_order
  
  else:
    # Otherwise (if GSystemType found) depending upon whether type_of exists or not returns property_order.
    if not demo["property_order"] and demo.has_key("_id"):
      type_of_nodes = node_collection.find({'_type': "GSystemType", '_id': {'$in': demo["type_of"]}}, {'property_order': 1})
      
      if type_of_nodes.count():
        demo["property_order"] = []
        for to in type_of_nodes:
          for po in to["property_order"]:
            demo["property_order"].append(po)

      node_collection.collection.update({'_id': demo._id}, {'$set': {'property_order': demo["property_order"]}}, upsert=False, multi=False)

  new_property_order = demo['property_order']

  if demo.has_key('_id'):
    node = node_collection.one({'_id': demo._id})

  else:
    node = eval("node_collection.collection"+"."+demo['_type'])()
    node["member_of"] = demo["member_of"]
  
  node['property_order'] = new_property_order

  return node['property_order']



@get_execution_time
def parse_template_data(field_data_type, field_value, **kwargs):
  """
  Parses the value fetched from request (GET/POST) object based on the data-type of the given field.

  Arguments:
  field_data_type -- data-type of the field
  field_value -- value of the field retrieved from GET/POST object

  Returns:
  Parsed value based on the data-type of the field
  """

  '''
  kwargs_keys_list = [
                    "date_format_string",     # date-format in string representation
                    "field_instance"          # dict-object reperesenting AT/RT node
                  ]
  '''
  DATA_TYPE_STR_CHOICES = [
                          "unicode", "basestring",
                          "int", "float", "long",
                          "list", "dict",
                          "datetime",
                          "bool",
                          "ObjectId"
                        ]
  try:
    if type(field_data_type) == type:
      field_data_type = field_data_type.__name__

      if not field_value:
        if field_data_type == "dict":
          return {}

        elif field_data_type == "list":
          return []

        else:
          return None

      if field_data_type == "unicode":
        field_value = unicode(field_value)

      elif field_data_type == "basestring":
        field_value = field_value

      elif field_data_type == "int":
        field_value = int(field_value)

      elif field_data_type == "float":
        field_value = float(field_value)

      elif field_data_type == "long":
        field_value = long(field_value)

      elif field_data_type == "list":
        if ("[" in field_value) and ("]" in field_value):
          field_value = json.loads(field_value)

        else:
          lr = field_value.replace(" ,", ",")
          rr = lr.replace(", ", ",")
          field_value = rr.split(",")

      elif field_data_type == "dict":
        field_value = "???"

      elif field_data_type == "datetime":
        field_value = datetime.strptime(field_value, kwargs["date_format_string"])

      elif field_data_type == "bool":
        if field_value == "Yes" or field_value == "yes" or field_value == "1":
          if field_value == "1":
            field_value = bool(int(field_value))
          else:
            field_value = True
        
        elif field_value == "No" or field_value == "no" or field_value == "0":
          if field_value == "0":
            field_value = bool(int(field_value))
          else:
            field_value = False

      elif field_data_type == "ObjectId":
        field_value = ObjectId(field_value)

      else:
        error_message = "Unknown data-type ("+field_data_type+") found"
        raise Exception(error_message)

    elif type(field_data_type) == list:

      if kwargs.has_key("field_instance"):
        if kwargs["field_instance"]["_type"] == RelationType or kwargs["field_instance"]["_type"] == "RelationType":
          # Write RT related code 
          if not field_value:
            return None
          if field_value:
            field_value = ObjectId(field_value)

          else:
            error_message = "This ObjectId("+field_type+") doesn't exists"
            raise Exception(error_message)

      else:
        if not field_value:
          return []

        if ("[" in field_value) and ("]" in field_value):
          field_value = json.loads(field_value)

        else:
          lr = field_value.replace(" ,", ",")
          rr = lr.replace(", ", ",")
          field_value = rr.split(",")

        return field_value

    elif type(field_data_type) == dict:
      # Write code...
      if not field_value:
        return {}

    elif type(field_data_type) == mongokit.operators.IS:
      # Write code...
      if not field_value:
        return None

      field_value = unicode(field_value) if type(field_value) != unicode else field_value

    elif type(field_data_type) == mongokit.document.R:
      # Write code...
      if kwargs["field_instance"]["_type"] == AttributeType or kwargs["field_instance"]["_type"] == "AttributeType":
        # Write AT related code 
        if not field_value:
          if field_data_type == "dict":
            return {}

          elif field_data_type == "list":
            return []

          else:
            return None

      else:
        error_message = "Neither AttributeType nor RelationType found"
        raise Exception(error_message)

    else:
      error_message = "Unknown data-type found"
      raise Exception(error_message)

    return field_value
  
  except Exception as e:
    error_message = "\n TemplateDataParsingError: "+str(e)+" !!!\n"
    raise Exception(error_message)


@get_execution_time
def create_gattribute(subject_id, attribute_type_node, object_value=None, **kwargs):
  ga_node = None
  info_message = ""
  old_object_value = None

  ga_node = triple_collection.one({'_type': "GAttribute", 'subject': subject_id, 'attribute_type.$id': attribute_type_node._id})
  if ga_node is None:
    # Code for creation
    try:
      ga_node = triple_collection.collection.GAttribute()

      ga_node.subject = subject_id
      ga_node.attribute_type = attribute_type_node

      if (not object_value) and type(object_value) != bool:
        object_value = u"None"
        ga_node.status = u"DELETED"

      else:
        ga_node.status = u"PUBLISHED"

      ga_node.object_value = object_value
      ga_node.save()

      if object_value == u"None":
        info_message = " GAttribute ("+ga_node.name+") created successfully with status as 'DELETED'!\n"

      else:
        info_message = " GAttribute ("+ga_node.name+") created successfully.\n"

        # Fetch corresponding document & append into it's attribute_set
        node_collection.collection.update({'_id': subject_id}, 
                          {'$addToSet': {'attribute_set': {attribute_type_node.name: object_value}}}, 
                          upsert=False, multi=False
                        )

      is_ga_node_changed = True

    except Exception as e:
      error_message = "\n GAttributeCreateError: " + str(e) + "\n"
      raise Exception(error_message)

  else:
    # Code for updation
    is_ga_node_changed = False
    try:
      if (not object_value) and type(object_value) != bool:
        old_object_value = ga_node.object_value

        ga_node.status = u"DELETED"
        ga_node.save()
        info_message = " GAttribute ("+ga_node.name+") status updated from 'PUBLISHED' to 'DELETED' successfully.\n"

        # Fetch corresponding document & update it's attribute_set with proper value
        node_collection.collection.update({'_id': subject_id, 'attribute_set.'+attribute_type_node.name: old_object_value}, 
                          {'$pull': {'attribute_set': {attribute_type_node.name: old_object_value}}}, 
                          upsert=False, multi=False)

      else:
        if type(ga_node.object_value) == list:
          if type(ga_node.object_value[0]) == dict:
            old_object_value = ga_node.object_value

            if len(old_object_value) != len(object_value):
              ga_node.object_value = object_value
              is_ga_node_changed = True

            else:
              pairs = zip(old_object_value, object_value)
              if any(x != y for x, y in pairs):
                ga_node.object_value = object_value
                is_ga_node_changed = True

          elif set(ga_node.object_value) != set(object_value):
            old_object_value = ga_node.object_value
            ga_node.object_value = object_value
            is_ga_node_changed = True

        elif type(ga_node.object_value) == dict:
          if cmp(ga_node.object_value, object_value) != 0:
            old_object_value = ga_node.object_value
            ga_node.object_value = object_value
            is_ga_node_changed = True

        else:
          if ga_node.object_value != object_value:
            old_object_value = ga_node.object_value
            ga_node.object_value = object_value
            is_ga_node_changed = True

        if is_ga_node_changed or ga_node.status == u"DELETED":
          if ga_node.status == u"DELETED":
            ga_node.status = u"PUBLISHED"
            ga_node.save()

            info_message = " GAttribute ("+ga_node.name+") status updated from 'DELETED' to 'PUBLISHED' successfully.\n"

            # Fetch corresponding document & append into it's attribute_set
            node_collection.collection.update({'_id': subject_id}, 
                              {'$addToSet': {'attribute_set': {attribute_type_node.name: object_value}}}, 
                              upsert=False, multi=False)

          else:
            ga_node.status = u"PUBLISHED"
            ga_node.save()

            info_message = " GAttribute ("+ga_node.name+") updated successfully.\n"

            # Fetch corresponding document & update it's attribute_set with proper value
            node_collection.collection.update({'_id': subject_id, 'attribute_set.'+attribute_type_node.name: {"$exists": True}}, 
                              {'$set': {'attribute_set.$.'+attribute_type_node.name: ga_node.object_value}}, 
                              upsert=False, multi=False)
        else:
          info_message = " GAttribute ("+ga_node.name+") already exists (Nothing updated) !\n"

    except Exception as e:
      error_message = "\n GAttributeUpdateError: " + str(e) + "\n"
      raise Exception(error_message)

  # print "\n\t is_ga_node_changed: ", is_ga_node_changed
  if "is_changed" in kwargs:
    ga_dict = {}
    ga_dict["is_changed"] = is_ga_node_changed
    ga_dict["node"] = ga_node
    ga_dict["before_obj_value"] = old_object_value
    return ga_dict
  else:
    return ga_node



@get_execution_time
def create_grelation(subject_id, relation_type_node, right_subject_id_or_list, **kwargs):
  """Creates single or multiple GRelation documents (instances) based on given 
  RelationType's cardinality (one-to-one / one-to-many).

  Arguments:
  subject_id -- ObjectId of the subject-node
  relation_type_node -- Document of the RelationType node (Embedded document)
  right_subject_id_or_list -- 
    - When one to one relationship: Single ObjectId of the right_subject node
    - When one to many relationship: List of ObjectId(s) of the right_subject node(s)

  Returns:
  - When one to one relationship: Created/Updated/Existed document.
  - When one to many relationship: Created/Updated/Existed list of documents.
  
  """
  gr_node = None
  multi_relations = False

  try:
    subject_id = ObjectId(subject_id)

    if relation_type_node["object_cardinality"]:
      # If object_cardinality value exists and greater than 1 (or eaqual to 100)
      # Then it signifies it's a one to many type of relationship
      # assign multi_relations = True
      if relation_type_node["object_cardinality"] > 1:
        multi_relations = True

        # Check whether right_subject_id_or_list is list or not
        # If not convert it to list
        if not isinstance(right_subject_id_or_list, list):
          right_subject_id_or_list = [right_subject_id_or_list]

        # Check whether all values of a list are of ObjectId data-type or not 
        # If not convert them to ObjectId
        for i, each in enumerate(right_subject_id_or_list):
          right_subject_id_or_list[i] = ObjectId(each)

    if multi_relations:
      # For dealing with multiple relations (one to many)

      # Iterate and find all relationships (including DELETED ones' also)
      nodes = triple_collection.find(
        {'_type': "GRelation", 'subject': subject_id, 'relation_type.$id': relation_type_node._id}
      )

      gr_node_list = []

      for n in nodes:
        if n.right_subject in right_subject_id_or_list:
          if n.status != u"DELETED":
            # If match found with existing one's, then only remove that ObjectId from the given list of ObjectIds
            # Just to remove already existing entries (whose status is PUBLISHED)
            right_subject_id_or_list.remove(n.right_subject)
            gr_node_list.append(n)

            node_collection.collection.update(
              {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.name: n.right_subject}}, 
              upsert=False, multi=False
            )

            node_collection.collection.update(
              {'_id': n.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
              upsert=False, multi=False
            )

        else:
          # Case: When already existing entry doesn't exists in newly come list of right_subject(s)
          # So change their status from PUBLISHED to DELETED
          right_subject_id_or_list.remove(n.right_subject)
          n.status = u"DELETED"
          n.save()
          info_message = " MultipleGRelation: GRelation ("+n.name+") status updated from 'PUBLISHED' to 'DELETED' successfully.\n"

          node_collection.collection.update(
            {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
            {'$pull': {'relation_set.$.'+relation_type_node.name: n.right_subject}}, 
            upsert=False, multi=False
          )

          node_collection.collection.update(
            {'_id': n.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
            {'$pull': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
            upsert=False, multi=False
          )

      if right_subject_id_or_list:
        # If still ObjectId list persists, it means either they are new ones' or from deleted ones'
        # For deleted one's, find them and modify their status to PUBLISHED
        # For newer one's, create them as new document
        for nid in right_subject_id_or_list:
          gr_node = triple_collection.one(
            {'_type': "GRelation", 'subject': subject_id, 'relation_type.$id': relation_type_node._id, 'right_subject': nid}
          )

          if gr_node is None:
            # New one found so create it
            gr_node = triple_collection.collection.GRelation()

            gr_node.subject = subject_id
            gr_node.relation_type = relation_type_node
            gr_node.right_subject = nid

            gr_node.status = u"PUBLISHED"
            gr_node.save()
            info_message = " MultipleGRelation: GRelation ("+gr_node.name+") created successfully.\n"

            left_subject = node_collection.one({'_id': subject_id}, {'relation_set': 1})

            rel_exists = False
            for each_dict in left_subject.relation_set:
              if relation_type_node.name in each_dict:
                rel_exists = True
                break

            if not rel_exists:
              # Fetch corresponding document & append into it's relation_set
              node_collection.collection.update(
                {'_id': subject_id}, 
                {'$addToSet': {'relation_set': {relation_type_node.name: [nid]}}}, 
                upsert=False, multi=False
              )

            else:
              node_collection.collection.update(
                {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
                {'$addToSet': {'relation_set.$.'+relation_type_node.name: nid}}, 
                upsert=False, multi=False
              )

            right_subject = node_collection.one({'_id': nid}, {'relation_set': 1})

            inv_rel_exists = False
            for each_dict in right_subject.relation_set:
              if relation_type_node.inverse_name in each_dict:
                inv_rel_exists = True
                break

            if not inv_rel_exists:
              # Fetch corresponding document & append into it's relation_set
              node_collection.collection.update(
                {'_id': nid}, 
                {'$addToSet': {'relation_set': {relation_type_node.inverse_name: [subject_id]}}}, 
                upsert=False, multi=False
              )

            else:
              node_collection.collection.update(
                {'_id': nid, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
                {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
                upsert=False, multi=False
              )

            gr_node_list.append(gr_node)

          else:
            # Deleted one found so change it's status back to Published
            if gr_node.status == u'DELETED':
              gr_node.status = u"PUBLISHED"
              gr_node.save()

              info_message = " MultipleGRelation: GRelation ("+gr_node.name+") status updated from 'DELETED' to 'PUBLISHED' successfully.\n"

              node_collection.collection.update(
                {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
                {'$addToSet': {'relation_set.$.'+relation_type_node.name: gr_node.right_subject}}, 
                upsert=False, multi=False
              )

              node_collection.collection.update(
                {'_id': gr_node.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
                {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
                upsert=False, multi=False
              )

              gr_node_list.append(gr_node)

            else:
              error_message = " MultipleGRelation: Corrupt value found - GRelation ("+gr_node.name+")!!!\n"
              # raise Exception(error_message)

      return gr_node_list

    else:
      # For dealing with single relation (one to one)
      gr_node = None

      if isinstance(right_subject_id_or_list, list):
        right_subject_id_or_list = ObjectId(right_subject_id_or_list[0])

      else:
        right_subject_id_or_list = ObjectId(right_subject_id_or_list)

      gr_node_cur = triple_collection.find(
        {'_type': "GRelation", 'subject': subject_id,'relation_type.$id': relation_type_node._id}
      )

      for node in gr_node_cur:
        if node.right_subject == right_subject_id_or_list:
          # If match found, it means it could be either DELETED one or PUBLISHED one

          if node.status == u"DELETED":
            # If deleted, change it's status back to Published from Deleted
            node.status = u"PUBLISHED"
            node.save()
            info_message = " SingleGRelation: GRelation ("+node.name+") status updated from 'DELETED' to 'PUBLISHED' successfully.\n"

            node_collection.collection.update(
              {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.name: node.right_subject}}, 
              upsert=False, multi=False
            )

            node_collection.collection.update(
              {'_id': node.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
              upsert=False, multi=False
            )

          elif node.status == u"PUBLISHED":
            node_collection.collection.update(
              {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.name: node.right_subject}}, 
              upsert=False, multi=False
            )

            node_collection.collection.update(
              {'_id': node.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
              {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
              upsert=False, multi=False
            )
            info_message = " SingleGRelation: GRelation ("+node.name+") already exists !\n"

          # Set gr_node value as matched value, so that no need to create new one
          node.reload()
          gr_node = node

        else:
          # If match not found and if it's PUBLISHED one, modify it to DELETED
          if node.status == u'PUBLISHED':
            node.status = u"DELETED"
            node.save()

            node_collection.collection.update(
              {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
              {'$pull': {'relation_set.$.'+relation_type_node.name: node.right_subject}}, 
              upsert=False, multi=False
            )

            node_collection.collection.update(
              {'_id': node.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
              {'$pull': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
              upsert=False, multi=False
            )
            info_message = " SingleGRelation: GRelation ("+node.name+") status updated from 'DELETED' to 'PUBLISHED' successfully.\n"
          
          elif node.status == u'DELETED':
            node_collection.collection.update(
              {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
              {'$pull': {'relation_set.$.'+relation_type_node.name: node.right_subject}}, 
              upsert=False, multi=False
            )

            node_collection.collection.update(
              {'_id': node.right_subject, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
              {'$pull': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
              upsert=False, multi=False
            )
            info_message = " SingleGRelation: GRelation ("+node.name+") status updated from 'DELETED' to 'PUBLISHED' successfully.\n"

      if gr_node is None:
        # Code for creation
        gr_node = triple_collection.collection.GRelation()

        gr_node.subject = subject_id
        gr_node.relation_type = relation_type_node
        gr_node.right_subject = right_subject_id_or_list

        gr_node.status = u"PUBLISHED"
        
        gr_node.save()
        info_message = " GRelation ("+gr_node.name+") created successfully.\n"

        left_subject = node_collection.one({'_id': subject_id}, {'relation_set': 1})

        rel_exists = False
        for each_dict in left_subject.relation_set:
          if relation_type_node.name in each_dict:
            rel_exists = True
            break

        if not rel_exists:
          # Fetch corresponding document & append into it's relation_set
          node_collection.collection.update(
            {'_id': subject_id}, 
            {'$addToSet': {'relation_set': {relation_type_node.name: [right_subject_id_or_list]}}}, 
            upsert=False, multi=False
          )

        else:
          node_collection.collection.update(
            {'_id': subject_id, 'relation_set.'+relation_type_node.name: {'$exists': True}}, 
            {'$addToSet': {'relation_set.$.'+relation_type_node.name: right_subject_id_or_list}}, 
            upsert=False, multi=False
          )

        right_subject = node_collection.one({'_id': right_subject_id_or_list}, {'relation_set': 1})

        inv_rel_exists = False
        for each_dict in right_subject.relation_set:
          if relation_type_node.inverse_name in each_dict:
            inv_rel_exists = True
            break

        if not inv_rel_exists:
          # Fetch corresponding document & append into it's relation_set
          node_collection.collection.update(
            {'_id': right_subject_id_or_list}, 
            {'$addToSet': {'relation_set': {relation_type_node.inverse_name: [subject_id]}}}, 
            upsert=False, multi=False
          )

        else:
          node_collection.collection.update(
            {'_id': right_subject_id_or_list, 'relation_set.'+relation_type_node.inverse_name: {'$exists': True}}, 
            {'$addToSet': {'relation_set.$.'+relation_type_node.inverse_name: subject_id}}, 
            upsert=False, multi=False
          )

      return gr_node

  except Exception as e:
      error_message = "\n GRelationError: " + str(e) + "\n"
      raise Exception(error_message)

      

      
###############################################      ##############################################
@get_execution_time
def set_all_urls(member_of):
	Gapp_obj = node_collection.one({"_type":"MetaType", "name":"GAPP"})
	factory_obj = node_collection.one({"_type":"MetaType", "name":"factory_types"})

	url = ""	
	gsType = member_of[0]
	gsType_obj = node_collection.one({"_id":ObjectId(gsType)})
	
	if Gapp_obj._id in gsType_obj.member_of:
		if gsType_obj.name == u"Quiz":
		    url = u"quiz/details"
		else:
		    url = gsType_obj.name.lower()
	elif factory_obj._id in gsType_obj.member_of:
		if gsType_obj.name == u"QuizItem":
		    url = u"quiz/details"
		elif gsType_obj.name == u"Twist":
		    url = u"forum/thread"
		else:
		    url = gsType_obj.name.lower()
	else:
		url = u"None"
	return url
###############################################	###############################################    


@login_required
@get_execution_time
def create_discussion(request, group_id, node_id):
  '''
  Method to create discussion thread for File and Page.
  '''

  try:

    twist_st = node_collection.one({'_type':'GSystemType', 'name':'Twist'})

    node = node_collection.one({'_id': ObjectId(node_id)})

    # group = node_collection.one({'_id':ObjectId(group_id)})

    thread = node_collection.one({ "_type": "GSystem", "name": node.name, "member_of": ObjectId(twist_st._id), "prior_node": ObjectId(node_id) })
    
    if not thread:
      
      # retriving RelationType
      # relation_type = node_collection.one({ "_type": "RelationType", "name": u"has_thread", "inverse_name": u"thread_of" })
      
      # Creating thread with the name of node
      thread_obj = node_collection.collection.GSystem()

      thread_obj.name = unicode(node.name)
      thread_obj.status = u"PUBLISHED"

      thread_obj.created_by = int(request.user.id)
      thread_obj.modified_by = int(request.user.id)
      thread_obj.contributors.append(int(request.user.id))

      thread_obj.member_of.append(ObjectId(twist_st._id))
      thread_obj.prior_node.append(ObjectId(node_id))
      thread_obj.group_set.append(ObjectId(group_id))
      
      thread_obj.save()

      # creating GRelation
      # create_grelation(node_id, relation_type, twist_st)
      response_data = [ "thread-created", str(thread_obj._id) ]

      return HttpResponse(json.dumps(response_data))

    else:
      response_data =  [ "Thread-exist", str(thread._id) ]
      return HttpResponse(json.dumps(response_data))
  
  except Exception as e:
    
    error_message = "\n DiscussionThreadCreateError: " + str(e) + "\n"
    raise Exception(error_message)
    # return HttpResponse("server-error")


# to add discussion replie
@get_execution_time
def discussion_reply(request, group_id):

  try:

    prior_node = request.POST.get("prior_node_id", "")
    content_org = request.POST.get("reply_text_content", "") # reply content

    # process and save node if it reply has content  
    if content_org:
  
      user_id = int(request.user.id)
      user_name = unicode(request.user.username)

      # auth = node_collection.one({'_type': 'Author', 'name': user_name })
      reply_st = node_collection.one({ '_type':'GSystemType', 'name':'Reply'})
      
      # creating empty GST and saving it
      reply_obj = node_collection.collection.GSystem()

      reply_obj.name = unicode("Reply of:" + str(prior_node))
      reply_obj.status = u"PUBLISHED"

      reply_obj.created_by = user_id
      reply_obj.modified_by = user_id
      reply_obj.contributors.append(user_id)

      reply_obj.member_of.append(ObjectId(reply_st._id))
      reply_obj.prior_node.append(ObjectId(prior_node))
      reply_obj.group_set.append(ObjectId(group_id))
  
      reply_obj.content_org = unicode(content_org)
      filename = slugify(unicode("Reply of:" + str(prior_node))) + "-" + user_name + "-"
      reply_obj.content = org2html(content_org, file_prefix=filename)
  
      # saving the reply obj
      reply_obj.save()

      formated_time = reply_obj.created_at.strftime("%B %d, %Y, %I:%M %p")
      
      # ["status_info", "reply_id", "prior_node", "html_content", "org_content", "user_id", "user_name", "created_at" ]
      reply = json.dumps( [ "reply_saved", str(reply_obj._id), str(reply_obj.prior_node[0]), reply_obj.content, reply_obj.content_org, user_id, user_name, formated_time], cls=DjangoJSONEncoder )

      return HttpResponse( reply )

    else: # no reply content

      return HttpResponse(json.dumps(["no_content"]))      

  except Exception as e:
    
    error_message = "\n DiscussionReplyCreateError: " + str(e) + "\n"
    raise Exception(error_message)

    return HttpResponse(json.dumps(["Server Error"]))



@get_execution_time
def discussion_delete_reply(request, group_id):

    nodes_to_delete = json.loads(request.POST.get("nodes_to_delete", "[]"))
    
    reply_st = node_collection.one({ '_type':'GSystemType', 'name':'Reply'})

    deleted_replies = []
    
    for each_reply in nodes_to_delete:
        temp_reply = node_collection.one({"_id": ObjectId(each_reply)})
        
        if temp_reply:
            deleted_replies.append(temp_reply._id.__str__())
            temp_reply.delete()
        
    return HttpResponse(json.dumps(deleted_replies))



@get_execution_time
def get_user_group(userObject):
  '''
  methods for getting user's belongs to group.
  input (userObject) is user object
  output list of dict, dict contain groupname, access, group_type, created_at and created_by
  '''
  blank_list = []
  cur_groups_user = node_collection.find({'_type': "Group", 
                                          '$or': [
                                            {'created_by': userObject.id}, 
                                            {'group_admin': userObject.id},
                                            {'author_set': userObject.id},
                                          ]
                                        }).sort('last_update', -1)
  for eachgroup in cur_groups_user :
    access = ""
    if eachgroup.created_by == userObject.id:
      access = "owner"
    elif userObject.id in eachgroup.group_admin :
      access = "admin"
    elif userObject.id in eachgroup.author_set :
      access = "member"
    else :
      access = "member"
    user = User.objects.get(id=eachgroup.created_by)
    blank_list.append({'id':str(eachgroup._id), 'name':eachgroup.name, 'access':access, 'group_type':eachgroup.group_type, 'created_at':eachgroup.created_at, 'created_by':user.username})
  return blank_list

@get_execution_time
def get_user_task(userObject):
  '''
  methods for getting user's assigned task.
  input (userObject) is user object
  output list of dict, dict contain taskname, status, due_time, created_at and created_by, group_name
  '''
  blank_list = []
  attributetype_assignee = node_collection.find_one({"_type":'AttributeType', 'name':'Assignee'})
  attributetype_status = node_collection.find_one({"_type":'AttributeType', 'name':'Status'})
  attributetype_end_time = node_collection.find_one({"_type":'AttributeType', 'name':'end_time'})
  attr_assignee = triple_collection.find({"_type":"GAttribute", "attribute_type.$id":attributetype_assignee._id, "object_value":userObject.username})
  for attr in attr_assignee :
    blankdict = {}
    task_node = node_collection.find_one({'_id':attr.subject})
    attr_status = triple_collection.find_one({"_type":"GAttribute", "attribute_type.$id":attributetype_status._id, "subject":task_node._id})
    attr_end_time = triple_collection.find_one({"_type":"GAttribute", "attribute_type.$id":attributetype_end_time._id, "subject":task_node._id})
    if attr_status.object_value is not "closed":
      group = node_collection.find_one({"_id":task_node.group_set[0]})
      user = User.objects.get(id=task_node.created_by)
      blankdict.update({'name':task_node.name, 'created_at':task_node.created_at, 'created_by':user.username, 'group_name':group.name, 'id':str(task_node._id)})
      if attr_status:
        blankdict.update({'status':attr_status.object_value})
      if attr_end_time:
        blankdict.update({'due_time':attr_end_time.object_value})
      blank_list.append(blankdict)
  return blank_list


@get_execution_time
def get_user_notification(userObject):
  '''
  methods for getting user's notification.
  input (userObject) is user object
  output list of dict, dict contain notice label, notice display
  '''
  blank_list = []
  notification_object = notification.NoticeSetting.objects.filter(user_id=userObject.id)
  for each in notification_object.reverse():
    ntid = each.notice_type_id
    ntype = notification.NoticeType.objects.get(id=ntid)
    label = ntype.label.split("-")[0]
    blank_list.append({'label':label, 'display': ntype.display})
  blank_list.reverse()
  return blank_list


@get_execution_time
def get_user_activity(userObject):
  '''
  methods for getting user's activity.
  input (userObject) is user object
  output list of dict, dict 
  '''
  blank_list = []
  activity = ""
  activity_user = node_collection.find({'$and':[{'$or':[{'_type':'GSystem'},{'_type':'Group'},{'_type':'File'}]}, 
                                                 {'$or':[{'created_by':userObject.id}, {'modified_by':userObject.id}]}] }).sort('last_update', -1).limit(10)
  for each in activity_user:
    if each.created_by == each.modified_by :
      if each.last_update == each.created_at:
        activity =  'created'
      else :
        activity =  'modified'
    else :
      activity =  'created'
    if each._type == 'Group':
      blank_list.append({'id':str(each._id), 'name':each.name, 'date':each.last_update, 'activity': activity, 'type': each._type})
    else :
      member_of = node_collection.find_one({"_id":each.member_of[0]})
      blank_list.append({'id':str(each._id), 'name':each.name, 'date':each.last_update, 'activity': activity, 'type': each._type, 'group_id':str(each.group_set[0]), 'member_of':member_of.name.lower()})
  return blank_list

@get_execution_time
def get_file_node(file_name=""):
  file_list=[]
  new=[]
  a=str(file_name).split(',')
  for i in a:
        k=str(i.strip('   [](\'u\'   '))
        new.append(k)
	ins_objectid  = ObjectId()
  for i in new:
          if  ins_objectid.is_valid(i) is False:
		  filedoc = node_collection.find({'_type':'File','name':unicode(i)})
	  else:
		  filedoc = node_collection.find({'_type':'File','_id':ObjectId(i)})			
          if filedoc:
             for i in filedoc:
		            file_list.append(i.name)	
  return file_list	

@get_execution_time
def create_task(task_dict, task_type_creation="single"):
    """Creates task with required attribute(s) and relation(s).

    task_dict
    - Required keys: _id[optional], name, group_set, created_by, modified_by, contributors, content_org,
        created_by_name, Status, Priority, start_time, end_time, Assignee, has_type

    task_type_creation
    - Valid input values: "single", "multiple", "group"
    """
    # Fetch Task GSystemType document
    task_gst = node_collection.one(
        {'_type': "GSystemType", 'name': "Task"}
    )

    # List of keys of "task_dict" dictionary
    task_dict_keys = task_dict.keys()

    if "_id" in task_dict:
      task_node = node_collection.one({'_id': task_dict["_id"]})
    else:
      task_node = node_collection.collection.GSystem()
      task_node["member_of"] = [task_gst._id]

    # Store built in variables of task node
    # Iterate task_node using it's keys
    for key in task_node:
        if key in ["Status", "Priority", "start_time", "end_time", "Assignee"]:
            # Required because these values might come as key in node's document
            continue

        if key in task_dict_keys:
            if key == "content_org":
                #  org-content
                task_node[key] = task_dict[key]

                # Required to link temporary files with the current user who is modifying this document
                filename = slugify(task_dict["name"]) + "-" + task_dict["created_by_name"] + "-" + ObjectId().__str__()
                task_dict_keys.remove("created_by_name")
                task_node.content = org2html(task_dict[key], file_prefix=filename)

            else:
                task_node[key] = task_dict[key]

            task_dict_keys.remove(key)

    # Save task_node with built-in variables as required for creating GAttribute(s)/GRelation(s)
    task_node.status = u"PUBLISHED"
    task_node.save()

    # Create GAttribute(s)/GRelation(s)
    for attr_or_rel_name in task_dict_keys:
        attr_or_rel_node = node_collection.one(
            {'_type': {'$in': ["AttributeType", "RelationType"]}, 'name': unicode(attr_or_rel_name)}
        )

        if attr_or_rel_node:
            if attr_or_rel_node._type == "AttributeType":
                ga_node = create_gattribute(task_node._id, attr_or_rel_node, task_dict[attr_or_rel_name])
            
            elif attr_or_rel_node._type == "RelationType":
                gr_node = create_grelation(task_node._id, attr_or_rel_node, task_dict[attr_or_rel_name])

            task_node.reload()

        else:
            raise Exception("\n No AttributeType/RelationType exists with given name("+attr_or_rel_name+") !!!")

    # If given task is a group task (create a task for each Assignee from the list)
    # Iterate Assignee list & create separate tasks for each Assignee 
    # with same set of attribute(s)/relation(s)
    if task_type_creation == "group":
        mutiple_assignee = task_dict["Assignee"]
        collection_set = []
        for each in mutiple_assignee:
            task_dict["Assignee"] = [each]
            task_sub_node = create_task(task_dict)
            collection_set.append(task_sub_node._id)

        node_collection.collection.update({'_id': task_node._id}, {'$set': {'collection_set': collection_set}}, upsert=False, multi=False)

    else:
        # Send notification for each each Assignee of the task
        # Only be done in case when task_type_creation is not group, 
        # i.e. either single or multiple
        if not task_dict.has_key("_id"):
          site = Site.objects.get(pk=1)
          site = site.name.__str__()

          from_user = task_node.user_details_dict["created_by"]  # creator of task

          group_name = node_collection.one(
              {'_type': {'$in': ["Group", "Author"]}, '_id': task_node.group_set[0]},
              {'name': 1}
          ).name

          url_link = "http://" + site + "/" + group_name.replace(" ","%20").encode('utf8') + "/task/" + str(task_node._id)

          to_user_list = []
          for index, user_id in enumerate(task_dict["Assignee"]):
              user_obj = User.objects.get(id=user_id)
              task_dict["Assignee"][index] = user_obj.username
              if user_obj not in to_user_list:
                  to_user_list.append(user_obj)

          msg = "Task '" + task_node.name + "' has been reported by " + from_user + \
              "\n     - Status: " + task_dict["Status"] + \
              "\n     - Priority: " + task_dict["Priority"] + \
              "\n     - Assignee: " + ", ".join(task_dict["Assignee"]) +  \
              "\n     - For more details, please click here: " + url_link

          activity = "reported task"
          render_label = render_to_string(
              "notification/label.html",
              {
                  "sender": from_user,
                  "activity": activity,
                  "conjunction": "-",
                  "link": url_link
              }
          )
          notification.create_notice_type(render_label, msg, "notification")
          notification.send(to_user_list, render_label, {"from_user": from_user})

    return task_node



@get_execution_time
def get_student_enrollment_code(college_id, node_id_to_ignore, registration_date, college_group_id=None):
    """Returns new student's enrollment code

    Enrollment Code is combination of following values:
    Code: (MH/SNG/15/xxxx)
    - 2-letters state code
    - 3-letters college code
    - 2-digits year of registration
    - 4-digits Auto-generated No.

    Arguments:
    college_id: ObjectId of college's node
    node_id_to_ignore: ObjectId of the student node for which this function generates enrollment_code
    registration_date: Date of registration of student node for which this function generates enrollment_code
    college_group_id [Optional]: ObjectId of college's group node

    Returns:
    Newly created enrollment code for student node
    """

    new_student_enrollment_code = u""
    last_enrollment_code = u""
    enrollment_code_except_num = u""
    college_id = ObjectId(college_id)
    if college_group_id:
        college_group_id = ObjectId(college_group_id)
    college_name = u""
    college_code = u""
    state_code = u""
    two_digit_year_code = u""
    student_count = 0
    four_digit_num = u""

    # If registering very first student, then create enrollment code
    # Else fetch enrollment code from last registered student node

    # Fetch college enrollemnt code
    college_node = node_collection.collection.aggregate([{
        "$match": {
            "_id": college_id
        }
    }, {
        "$project": {
            "college_name": "$name",
            "college_code": "$attribute_set.enrollment_code",
            "college_group_id": "$relation_set.has_group",
            "state_id": "$relation_set.organization_belongs_to_state"
        }
    }])

    college_node = college_node["result"]
    if college_node:
        college_node = college_node[0]
        colg_group_id = college_node["college_group_id"]
        if colg_group_id:
            colg_group_id = ObjectId(colg_group_id[0][0])
            if colg_group_id != college_group_id:
                # Reset college_group_id as passed is not given
                # college node's group id
                college_group_id = colg_group_id

        college_name = college_node["college_name"]

        # Set College enrollment code
        college_code = college_node["college_code"]
        if college_code:
            college_code = college_code[0]

        if not college_name or not college_code:
            raise Exception("Either name or enrollment code is not set for given college's ObjectId(" + str(college_id) + ") !!!")

        # Set Last two digits of current year
        # current_year = str(datetime.today().year)
        current_year = str(registration_date.year)
        two_digit_year_code = current_year[-2:]

        # Fetch total no. of students registered for current year
        # Along with enrollment code of last registered student
        date_gte = datetime.strptime("1/1/" + current_year, "%d/%m/%Y")
        date_lte = datetime.strptime("31/12/" + current_year, "%d/%m/%Y")
        student_gst = node_collection.one({
            "_type": "GSystemType",
            "name": "Student"
        })
        res = node_collection.collection.aggregate([{
            "$match": {
                "_id": {"$nin": [ObjectId(node_id_to_ignore)]},
                "member_of": student_gst._id,
                "group_set": college_group_id,
                "relation_set.student_belongs_to_college": college_id,
                "attribute_set.registration_date": {'$gte': date_gte, '$lte': date_lte},
                "status": u"PUBLISHED"
            }
        }, {
            "$sort": {
                "created_at": 1
            }
        }, {
            "$group": {
                "_id": {
                    "college": college_name,
                    "registration_year": current_year
                },
                "count": {
                    "$sum": 1
                },
                "last_enrollment_code": {
                    "$last": "$attribute_set.enrollment_code"
                }
            }
        }])

        student_data_result = res["result"]

        if student_data_result:
            student_count = student_data_result[0]["count"]
            last_enrollment_code = student_data_result[0]["last_enrollment_code"]
            if last_enrollment_code:
                last_enrollment_code = last_enrollment_code[0]

            if last_enrollment_code and student_count:
                # Fetch student enrollment code of last registered student node
                enrollment_code_except_num, four_digit_num = last_enrollment_code.rsplit("/", 1)
                four_digit_num = int(last_enrollment_code[-4:])

                if four_digit_num == student_count:
                    # 4. Four digit number of student's count (new) set
                    four_digit_num = "%04d" % (student_count + 1)
                    new_student_enrollment_code = u"%(enrollment_code_except_num)s/%(four_digit_num)s" % locals()

                else:
                    raise Exception("Inconsistent Data Found (Student count & last enrollment code's number doesn't match) !!!")
            else:
                raise Exception("Invalid Data Found (Student count & no last enrollment code) !!!")
        else:
            # Registering very first student node
            # Create enrollment code, hence fetch state node's state-code
            state_id = college_node["state_id"]
            if state_id:
                state_id = ObjectId(state_id[0][0])

                # Fetch state code
                state_node = node_collection.collection.aggregate([{
                    "$match": {
                        "_id": state_id
                    }
                }, {
                    "$project": {
                        "state_name": "$name",
                        "state_code": "$attribute_set.state_code"
                    }
                }])

                # 2. State code set
                state_node = state_node["result"]
                if state_node:
                    state_node = state_node[0]
                    state_name = state_node["state_name"]
                    state_code = state_node["state_code"]
                    if state_code:
                        state_code = state_code[0]
                    else:
                        raise Exception("No state code found for given state(" + state_name + ")")

                # 4. Four digit number of student's count (new) set
                four_digit_num = "%04d" % (student_count + 1)

                new_student_enrollment_code = u"%(state_code)s/%(college_code)s/%(two_digit_year_code)s/%(four_digit_num)s" % locals()
            else:
                raise Exception("Either state not set or inconsistent state value found for given college(" + college_name + ") !!!")

        return new_student_enrollment_code
    else:
        raise Exception("No college node exists with given college's ObjectId(" + str(college_id) + ") !!!")



@get_execution_time
def create_college_group_and_setup_data(college_node):
    """
    Creates private group for given college; establishes relationship
    between them via "has_group" RelationType.

    Also populating data into it needed for registrations.

    Arguments:
    college_node -- College node (or document)

    Returns:
    College group node
    GRelation node
    """

    gfc = None
    gr_gfc = None

    # [A] Creating group
    group_gst = node_collection.one(
        {'_type': "GSystemType", 'name': "Group"},
        {'_id': 1}
    )
    creator_and_modifier = college_node.created_by

    gfc = node_collection.one(
        {'_type': "Group", 'name': college_node.name},
        {'_id': 1, 'name': 1, 'group_type': 1}
    )

    if not gfc:
        gfc = node_collection.collection.Group()
        gfc._type = u"Group"
        gfc.name = college_node.name
        gfc.altnames = college_node.name
        gfc.member_of = [group_gst._id]
        gfc.group_type = u"PRIVATE"
        gfc.created_by = creator_and_modifier
        gfc.modified_by = creator_and_modifier
        gfc.contributors = [creator_and_modifier]
        gfc.status = u"PUBLISHED"
        gfc.save()

    if "_id" in gfc:
        has_group_rt = node_collection.one(
            {'_type': "RelationType", 'name': "has_group"}
        )
        gr_gfc = create_grelation(college_node._id, has_group_rt, gfc._id)

        # [B] Setting up data into college group
        if gr_gfc:
            # List of Types (names) whose data needs to be populated
            # in college group
            gst_list = [
                "Country", "State", "District", "University",
                "College", "Caste", "NUSSD Course"
            ]

            gst_cur = node_collection.find(
                {'_type': "GSystemType", 'name': {'$in': gst_list}}
            )

            # List of Types (ObjectIds)
            gst_list = []
            for each in gst_cur:
                gst_list.append(each._id)

            mis_admin = node_collection.one(
                {
                    '_type': "Group",
                    '$or': [
                        {'name': {'$regex': u"MIS_admin", '$options': 'i'}},
                        {'altnames': {'$regex': u"MIS_admin", '$options': 'i'}}
                    ],
                    'group_type': "PRIVATE"
                },
                {'_id': 1}
            )

            # Update GSystem node(s) of GSystemType(s) specified in gst_list
            # Append newly created college group's ObjectId in group_set field
            node_collection.collection.update(
                {
                    '_type': "GSystem", 'member_of': {'$in': gst_list},
                    'group_set': mis_admin._id
                },
                {'$addToSet': {'group_set': gfc._id}},
                upsert=False, multi=True
            )

    return gfc, gr_gfc


def get_published_version_dict(request,document_object):
        """Returns the dictionary containing the list of revision numbers of published nodes.
        """
        published_node_version = []
        rcs = RCS()
        fp = history_manager.get_file_path(document_object)
        cmd= 'rlog  %s' % \
	      (fp)
        rev_no =""
        proc1=subprocess.Popen(cmd,shell=True,
				stdout=subprocess.PIPE)
        for line in iter(proc1.stdout.readline,b''):
            if line.find('revision')!=-1 and line.find('selected') == -1:
                  rev_no=string.split(line,'revision')
                  rev_no=rev_no[1].strip( '\t\n\r')
                  rev_no=rev_no.strip(' ')
            if line.find('PUBLISHED')!=-1:
                   published_node_version.append(rev_no)      
        return published_node_version
def parse_data(doc):
  '''Section to parse node '''
  user_idlist = ['modified_by','created_by','author_set','contributors']
  date_typelist = ['last_update','created_at']
  objecttypelist = ['member_of']
  languagelist = ['language']
  for i in doc:
           
           
          if i in user_idlist:
             if type(doc[i]) == list :
                      temp =   ""
                      for userid in doc[i]:
                      		  if User.objects.filter(id = userid).exists():
	                              user = User.objects.get(id = userid)
	                              if user:
	                                user_name = user.get_username
	                                if temp:
	                                        temp =temp  + "," + (user.get_username() ) 
	                                else:
	                                        temp = str(user.get_username())        
	              doc[i] = temp            
             else: 
                      
                      		  if User.objects.filter(id = doc[i]).exists():
	                              user = User.objects.get(id = doc[i])
	                              if user:
	                                doc[i] = user.get_username()
          elif i in date_typelist:
              doc[i] = datetime.strftime(doc[i],"%d %B %Y %H:%M")
          elif i in objecttypelist:
               for j in doc[i]:
                   node = node_collection.one({"_id":ObjectId(j)})
                   doc[i] = node.name
          elif i == "rating":
             new_str = ""
             for k in doc[i]:
                userid = k['user_id']
                score = k['score']
                if User.objects.filter(id = userid).exists():
	                              user = User.objects.get(id = userid)
	                              if user:
	                                 new_str = new_str + "User" +":" + str(user.get_username()) + "  " + "Score" + str (score) + "\n"
	     if not doc[i]:
	              doc[i] = ""
	     else:
	              doc[i] = new_str                     
          elif i == "location":
              coordinates = []
              parsed_string = ""
              for j in doc[i]:
                 coordinates = j['geometry']['coordinates']
              if  coordinates:
                   for j in coordinates:
                      if parsed_string:
                        parsed_string =   str(parsed_string)  + "," + str(j)
                      else:
                        parsed_string =   str(j)  
              if not doc[i]:
                   doc[i] = ""
              else:
                   doc[i] = parsed_string
                 
          elif not doc[i]:
             doc[i] = ""
         

          

def delete_gattribute(subject_id=None, deletion_type=0, **kwargs):
    """This function deletes GAttribute node(s) of Triples collection.

    Keyword arguments:
    subject_id -- (Optional argument)
        - Specify this argument if you need to delete/purge GAttribute(s)
        related to given node belonging to Nodes collection
        - ObjectId of the node whose GAttribute node(s) need(s) to be deleted,
        accepted in either format String or ObjectId
        - Default value is set to None

    kwargs["node_id"] -- (Optional argument)
        - Specify this argument if you need to delete/purge only a given
        GAttribute node
        - ObjectId of the GAttribute node to be deleted/purged, accepted in
        either format String or ObjectId
        - If this argument is specified, subject_id will work as an optional
        argument and even query variable would be overridden by node_id's
        query variable

    deletion_type -- (Optional argument)
        - Specify this to signify which type of deletion you need to perform
        - Accepts only either of the following values:
        (a) 0 (zero, i.e.  Normal delete)
            - Process in which node exists in database; only status field's
            value is set to "DELETED"
        (b) 1 (one, i.e. Purge)
            - Process in which node is deleted from the database
        - Default value is set to 0 (zero)

    Returns:
    A tuple with following values:
        First-element: Boolean value
        Second-element: Message

    If deletion is successful, then (True, "Success message.")
    Otherwise, (False, "Error message !")

    Examples:
    del_status, del_status_msg = delete_attribute(
        subject_id=ObjectId("...")
        [, deletion_type=0[/1]]
    )

    del_status, del_status_msg = delete_attribute(
        node_id=ObjectId("...")
        [, deletion_type=0[/1]]
    )
    """
    node_id = None
    str_node_id = ""
    str_subject_id = ""
    str_deletion_type = "deleted"  # As default value of deletion_type is 0

    # Below variable holds list of ObjectId (string format)
    # of GAttribute node(s) which is/are going to be deleted
    gattribute_deleted_id = []

    # Below variable holds list of ObjectId (string format)
    # of GAttribute node(s) whose object_value field is/are going to be updated
    gattribute_updated_id = []

    query = OrderedDict()

    try:
        # print "\n 1 >> Begin..."
        if deletion_type not in [0, 1]:
            delete_status_message = "Must pass \"deletion_type\" agrument's " \
                + "value as either 0 (Normal delete) or 1 (Purge)"
            raise Exception(delete_status_message)

        # print "\n 2 >> looking for node_id..."
        if "node_id" in kwargs:
            # Typecast node_id from string into ObjectId,
            # if found in string format
            node_id = kwargs["node_id"]

            # print "\t 2a >> convert node_id..."
            if node_id:
                if type(node_id) == ObjectId:
                    str_node_id = str(node_id)
                    # print "\t 2b >> node_id -- O to s: ", type(str_subject_id), " -- ", str_subject_id
                else:
                    str_node_id = node_id
                    if ObjectId.is_valid(node_id):
                        node_id = ObjectId(node_id)
                        # print "\t 2c >> node_id -- s to O: ", type(str_subject_id), " -- ", str_subject_id
                    else:
                        delete_status_message = "Invalid value found for node_id " \
                            + "(%(str_node_id)s)... [Expected value in" % locals() \
                            + " ObjectId format] !!!"
                        raise Exception(delete_status_message)

                # Forming query to delete a specific GAtribute node
                query = {"_id": node_id}
                # print "\t 2d >> query... ", query

        # print "\n 3 >> looking for subject_id..."
        if not node_id:
            # Perform check for subject_id
            # print "\t 3 >> found subject_id..."
            if not subject_id:
                delete_status_message = "Either specify subject_id " \
                    + "or node_id [Expected value in ObjectId format] !!!"
                raise Exception(delete_status_message)

            # print "\t 3a >> convert subject_id..."
            if subject_id:
                # Typecast subject_id from string into ObjectId,
                # if found in string format
                if type(subject_id) == ObjectId:
                    str_subject_id = str(subject_id)
                    # print "\t 3b >> subject_id -- O to s: ", type(str_subject_id), " -- ", str_subject_id
                else:
                    str_subject_id = subject_id
                    if ObjectId.is_valid(subject_id):
                        subject_id = ObjectId(subject_id)
                        # print "\t 3c >> subject_id -- s to O: ", type(str_subject_id), " -- ", str_subject_id
                    else:
                        if not node_id:
                            delete_status_message = "Invalid value found for subject_id " \
                                + "(%(str_subject_id)s)... [Expected value in" % locals() \
                                + " ObjectId format] !!!"
                            raise Exception(delete_status_message)

                # Check first whether request is
                # for single GAttribute node delete or not
                # print "\t 3d >> Override query... ???"
                if not node_id:
                    # Form this query only when you need to
                    # delete GAttribute(s) related to a given node
                    query = {"_type": "GAttribute", "subject": subject_id}
                    # print "\t 3e >> query (YES)... ", query

        # Based on what you need to perform (query)
        # Delete single GAttribute node, or
        # Delete GAttribute node(s) related to a given node (subject_id)
        # Find the required GAttribute node(s)
        gattributes = triple_collection.find(query)
        # print "\n 4 >> gattributes.count()... ", gattributes.count()

        # Perform normal delete operation (i.e. deletion_type == 0)
        for each_ga in gattributes:
            gattribute_deleted_id.append(each_ga._id.__str__())

            if each_ga.status != u"DELETED":
                create_gattribute(each_ga.subject, each_ga.attribute_type)
                # print "\t 4 >> each_ga (0) ... ", each_ga._id

        # print "\n 5 >> gattribute_deleted_id... " + ", ".join(gattribute_deleted_id)

        # Perform purge operation
        if deletion_type == 1:
            # Remove from database
            str_deletion_type = "purged"
            triple_collection.collection.remove(query)
            # print "\n 6 >> purged also... " + ", ".join(gattribute_deleted_id)

        # Formulate delete-status-message
        if gattribute_deleted_id:
            delete_status_message = "\tFollowing are the list of ObjectId(s) of " \
                + "%(str_deletion_type)s GAttribute node(s):- \n\t" % locals() \
                + ", ".join(gattribute_deleted_id)
        else:
            delete_status_message = "\tNo GAttribute nodes have been " \
                + "%(str_deletion_type)s !!!" % locals()

        # print "\n 7 >> special use-case... "
        # Special use-case
        if subject_id:
            # Find GAttribute node(s) whose object_value field (i.e. a list)
            # has subject_id as one of it's value
            gattributes = None
            gattributes = triple_collection.find({
                "_type": "GAttribute", "object_value": subject_id
            })
            # print "\n 8 >> gattributes.count()... ", gattributes.count()
            for each_ga in gattributes:
                # (a) Update GAttribute node's object_value field
                # Remove subject_id from object_value
                # (b) Update subject node's attribute_set field
                # Remove subject_id from the value corresponding to
                # subject node's "attribute-name" key referenced
                # in attribute_set field

                # Expecting object_value as list of ObjectIds
                obj_val = []
                # print "\n 8a >> each_ga... ", each_ga._id
                if type(each_ga.object_value) == list:
                    obj_val = each_ga.object_value

                    # Declaration required to avoid list-copy by reference
                    prev_obj_val = []
                    prev_obj_val.extend(obj_val)

                    if subject_id in obj_val:
                        obj_val.remove(subject_id)

                    # print "\t 8b >> obj_val... ", obj_val
                    # print "\t 8c >> prev_obj_val... ", prev_obj_val

                    if prev_obj_val != obj_val:
                        # Update only when there is any change found
                        # Below call will perform (a) & (b) collectively
                        create_gattribute(
                            each_ga.subject, each_ga.attribute_type, obj_val
                        )

                        gattribute_updated_id.append(each_ga._id.__str__())
                        # print "\t 8d >> updated..."

            if gattribute_updated_id:
                delete_status_message += "\tFollowing are the list of ObjectId(s) of " \
                    + "GAttribute node(s) whose object_value field is updated:- \n\t" \
                    + ", ".join(gattribute_updated_id)

        # Return output of the function
        # print "\n 9 >> ", delete_status_message
        return (True, delete_status_message)
    except Exception as e:
        delete_status_message = "DeleteGAttributeError: " + str(e)
        return (False, delete_status_message)


def delete_grelation(subject_id=None, deletion_type=0, **kwargs):
    """This function deletes GRelation node(s) of Triples collection.

    Keyword arguments:
    subject_id -- (Optional argument)
        - Specify this argument if you need to delete/purge GRelation(s)
        related to given node belonging to Nodes collection
        - ObjectId of the node whose GRelation node(s) need(s) to be deleted,
        accepted in either format String or ObjectId
        - Default value is set to None

    kwargs["node_id"] -- (Optional argument)
        - Specify this argument if you need to delete/purge only a given
        GRelation node
        - ObjectId of the GRelation node to be deleted/purged, accepted in
        either format String or ObjectId
        - If this argument is specified, subject_id will work as an optional
        argument and even query variable would be overridden by node_id's
        query variable

    deletion_type -- (Optional argument)
        - Specify this to signify which type of deletion you need to perform
        - Accepts only either of the following values:
        (a) 0 (zero, i.e.  Normal delete)
            - Process in which node exists in database; only status field's
            value is set to "DELETED"
        (b) 1 (one, i.e. Purge)
            - Process in which node is deleted from the database
        - Default value is set to 0 (zero)

    Returns:
    A tuple with following values:
        First-element: Boolean value
        Second-element: Message

    If deletion is successful, then (True, "Success message.")
    Otherwise, (False, "Error message !")

    Examples:
    del_status, del_status_msg = delete_grelation(
        subject_id=ObjectId("...")
        [, deletion_type=0[/1]]
    )

    del_status, del_status_msg = delete_grelation(
        node_id=ObjectId("...")
        [, deletion_type=0[/1]]
    )
    """
    node_id = None
    str_node_id = ""
    str_subject_id = ""
    str_deletion_type = "deleted"  # As default value of deletion_type is 0

    # Below variable holds list of ObjectId (string format)
    # of GRelation node(s) which is/are going to be deleted
    grelation_deleted_id = []

    # Below variable holds list of ObjectId (string format)
    # of GRelation node(s) [inverse-relation] which is/are going to be deleted
    inverse_grelation_deleted_id = []

    query_by_id = {}  # Search by _id field
    query_for_relation = OrderedDict()  # Search by subject field
    query_for_inverse_relation = OrderedDict()  # Search by right_subject field

    def _perform_delete_updates_on_node(gr_node):
        rel_name = gr_node.relation_type.name
        inv_rel_name = gr_node.relation_type.inverse_name
        subj = gr_node.subject
        right_subj = gr_node.right_subject

        # Remove right-subject-node's ObjectId from the value
        # corresponding to subject-node's "relation-name" key
        # referenced in relation_set field
        res = node_collection.collection.update({
            '_id': subj,
            'relation_set.' + rel_name: {'$exists': True}
        }, {
            '$pull': {'relation_set.$.' + rel_name: right_subj}
        },
            upsert=False, multi=False
        )
        # print "\n 5 -- subject node's (", subj, ") relation-name key (", rel_name, ") referenced in relation_set field updated -- \n", res

        # Remove subject-node's ObjectId from the value corresponding
        # to right-subject-node's "inverse-relation-name" key
        # referenced in relation_set field
        res = node_collection.collection.update({
            '_id': right_subj,
            'relation_set.' + inv_rel_name: {'$exists': True}
        }, {
            '$pull': {'relation_set.$.' + inv_rel_name: subj}
        },
            upsert=False, multi=False
        )
        # print " 5 -- right_subject node's (", right_subj, ") inverse-relation-name key (", inv_rel_name, ") referenced in relation_set field updated -- \n", res

        gr_node.status = u"DELETED"
        gr_node.save()

    try:
        # print "\n 1 >> Begin..."
        if deletion_type not in [0, 1]:
            delete_status_message = "Must pass \"deletion_type\" agrument's " \
                + "value as either 0 (Normal delete) or 1 (Purge) !!!"
            raise Exception(delete_status_message)

        # print "\n 2 >> looking for node_id..."
        if "node_id" in kwargs:
            # Typecast node_id from string into ObjectId,
            # if found in string format
            node_id = kwargs["node_id"]

            # print "\t 2a >> convert node_id..."
            if node_id:
                if type(node_id) == ObjectId:
                    str_node_id = str(node_id)
                    # print "\t 2b >> node_id -- O to s: ", type(str_subject_id), " -- ", str_subject_id
                else:
                    str_node_id = node_id
                    if ObjectId.is_valid(node_id):
                        node_id = ObjectId(node_id)
                        # print "\t 2c >> node_id -- s to O: ", type(str_subject_id), " -- ", str_subject_id
                    else:
                        delete_status_message = "Invalid value found for node_id " \
                            + "(%(str_node_id)s)... [Expected value in" % locals() \
                            + " ObjectId format] !!!"
                        raise Exception(delete_status_message)

                # Forming query to delete a specific GRelation node
                query_by_id = {"_id": node_id}
                # print "\t 2d >> query... ", query_by_id

        # print "\n 3 >> looking for subject_id..."
        if not node_id:
            # Perform check for subject_id
            # print "\t 3 >> found subject_id..."
            if not subject_id:
                delete_status_message = "Either specify subject_id " \
                    + "or node_id [Expected value in ObjectId format] !!!"
                raise Exception(delete_status_message)

            # print "\t 3a >> convert subject_id..."
            if subject_id:
                # Typecast subject_id from string into ObjectId,
                # if found in string format
                if type(subject_id) == ObjectId:
                    str_subject_id = str(subject_id)
                    # print "\t 3b >> subject_id -- O to s: ", type(str_subject_id), " -- ", str_subject_id
                else:
                    str_subject_id = subject_id
                    if ObjectId.is_valid(subject_id):
                        subject_id = ObjectId(subject_id)
                        # print "\t 3c >> subject_id -- s to O: ", type(str_subject_id), " -- ", str_subject_id
                    else:
                        if not node_id:
                            delete_status_message = "Invalid value found for subject_id " \
                                + "(%(str_subject_id)s)... [Expected value in" % locals() \
                                + " ObjectId format] !!!"
                            raise Exception(delete_status_message)

                # Check first whether request is
                # for single GRelation node delete or not
                # print "\t 3d >> Override query... ???"
                if not node_id:
                    # Form this query only when you need to
                    # delete/purge GRelation(s) related to a given node
                    query_for_relation = {"_type": "GRelation", "subject": subject_id}
                    query_for_inverse_relation = {"_type": "GRelation", "right_subject": subject_id}
                    # print "\t 3e >> query (YES)... \n\t", query_for_relation, "\n\t", query_for_inverse_relation

        # Based on what you need to perform
        # Delete single GRelation node (query_by_id), or
        # Delete GRelation node(s) related to a given node (subject_id)
        # (i.e, query_for_relation and query_for_inverse_relation)
        # Find the required GRelation node(s) & perform required operation(s)
        if query_by_id:
            # print "\n delete single GRelation node"
            grelations = triple_collection.find(query_by_id)
            for each_rel in grelations:
                if each_rel.status != u"DELETED":
                    _perform_delete_updates_on_node(each_rel)
                grelation_deleted_id.append(each_rel._id.__str__())

            # print "\n 5 >> grelation_deleted_id... " + ", ".join(grelation_deleted_id)

            # Perform purge operation
            if deletion_type == 1:
                # Remove from database
                str_deletion_type = "purged"
                triple_collection.collection.remove(query_by_id)
                # print "\n 6 >> purged (relation) also... " + ", ".join(grelation_deleted_id)
        else:
            # print "\n handle query_for_relation, query_for_inverse_relation"
            grelations = None
            inv_grelations = None

            # (1) Find relation(s) of given node (subject_id)
            # i.e, GRelation node where given node's ObjectId resides
            # in subject field
            grelations = triple_collection.find(query_for_relation)
            for each_rel in grelations:
                if each_rel.status != u"DELETED":
                    _perform_delete_updates_on_node(each_rel)
                grelation_deleted_id.append(each_rel._id.__str__())

            # (2) Find inverse-relation(s) of given node (subject_id)
            # i.e, GRelation node where given node's ObjectId resides
            # in right_subject field
            inv_grelations = triple_collection.find(query_for_inverse_relation)
            for each_inv_rel in inv_grelations:
                if each_inv_rel.status != u"DELETED":
                    _perform_delete_updates_on_node(each_inv_rel)
                inverse_grelation_deleted_id.append(each_inv_rel._id.__str__())

            # print "\n 5 >> grelation_deleted_id... " + ", ".join(grelation_deleted_id)
            # print "\n 5 >> inverse_grelation_deleted_id... " + ", ".join(inverse_grelation_deleted_id)

            # Perform purge operation
            if deletion_type == 1:
                # Remove from database
                str_deletion_type = "purged"
                triple_collection.collection.remove(query_for_relation)
                triple_collection.collection.remove(query_for_inverse_relation)
                # print "\n 6 >> purged (relation) also... " + ", ".join(grelation_deleted_id)
                # print "\n 6 >> purged (inverse-relation) also... " + ", ".join(inverse_grelation_deleted_id)

        # Formulate delete-status-message
        if grelation_deleted_id:
            delete_status_message = "\tFollowing are the list of ObjectId(s) of " \
                + "%(str_deletion_type)s GRelation [Normal relation] node(s):- \n\t" % locals() \
                + ", ".join(grelation_deleted_id)
        else:
            delete_status_message = "\tNo GRelation [Normal relation] nodes have been " \
                + "%(str_deletion_type)s !!!" % locals()

        if inverse_grelation_deleted_id:
            delete_status_message += "\n\n\tFollowing are the list of ObjectId(s) of " \
                + "%(str_deletion_type)s GRelation [Inverse relation] node(s):- \n\t" % locals() \
                + ", ".join(inverse_grelation_deleted_id)
        else:
            delete_status_message += "\n\n\tNo GRelation [Inverse relation] nodes have been " \
                + "%(str_deletion_type)s !!!" % locals()

        # Return output of the function
        # print "\n 9 >> ", delete_status_message
        return (True, delete_status_message)
    except Exception as e:
        delete_status_message = "DeleteGRelationError: " + str(e)
        return (False, delete_status_message)


def delete_node(
        node_id=None, collection_name=node_collection.collection_name,
        deletion_type=0, **kwargs):
    """This function deletes node belonging to either Nodes collection or
    Triples collection.

    Keyword Arguments:
    node_id -- (Optional argument)
        - Specify this argument if you need to delete/purge only a given
        node from Nodes/Triples collection
        - ObjectId of the node to be deleted/purged, accepted in
        either format String or ObjectId
        - If this argument is specified, then subject_id parameter will be
        ignored (if specified) in case of deleting node from Triples collection
        - If this argument is ignored, then you must specify subject_id as a
        parameter (mandatory in case of deleting node from Triples collection).
        - Default value is set to None

    collection_name -- (Optional argument)
        - Specify this to signify from which collection you need to delete node
        i.e. helpful in setting-up the collection-variable
        - Name of the collection you need to refer for performing deletion
        - Accepts only either of the following values:
        (a) node_collection.collection_name/"Nodes"
        (b) triple_collection.collection_name/"Triples"
        - Default set to node_collection.collection_name (i.e. "Nodes")

    deletion_type -- (Optional argument)
        - Specify this to signify which type of deletion you need to perform
        - Accepts only either of the following values:
        (a) 0 (zero, i.e.  Normal delete)
            - Process in which node exists in database; only status field's
            value is set to "DELETED"
        (b) 1 (one, i.e. Purge)
            - Process in which node is deleted from the database
        - Default value is set to 0 (zero)

    kwargs["subject_id"] -- (Optional argument)
        - Specify this argument if you need to delete/purge GRelation(s) and/or
        GAttribute(s) related to given node belonging to Nodes collection
        - ObjectId of the node whose GAttribute(s) and/or GRelation node(s)
        need(s) to be deleted, accepted in either format String or ObjectId
        - Default value is set to None

    kwargs["_type"] -- (Optional argument)
        - Specify this argument if you need to delete/purge specifically either
        only GAttribute node(s) or GRelation node(s)
        - If ignored, then by default node(s) belonging to both types
        (GAttribute and GRelation) will be considered for deleting/purging
        - Can also be specified in case of delete/purge Nodes collection node

    Returns:
    A tuple with following values:
        First-element: Boolean value
        Second-element: Message

    If deletion is successful, then (True, "Success message.")
    Otherwise, (False, "Error message !")

    If you need to delete node of Nodes collection, then you only need to
    specify node_id, collection_name, and deletion_type as parameters.
        Examples:
        del_status, del_status_msg = delete_node(
            node_id=ObjectId("...")
            [, collection_name=node_collection.collection_name]
            [, deletion_type=0[/1]]
        )

    If you need to delete node(s) of Triples collection, then you need to
    specify node_id/subject_id [depending on whether you need to delete single
    node or multiple nodes which are related to given node of Nodes collection]
    , collection_name, _type, and deletion_type as parameters.
        Examples:
        del_status, del_status_msg = delete_node(
            subject_id=ObjectId("..."),
            collection_name=triple_collection.collection_name
            [, _type="GAttribute"[/"GRelation"]]
            [, deletion_type=0[/1]]
        )
        del_status, del_status_msg = delete_node(
            node_id=ObjectId("..."),
            collection_name=triple_collection.collection_name
            [, _type="GAttribute"[/"GRelation"]]
            [, deletion_type=0[/1]]
        )
    """

    try:
        # print "\n 1 >> Entered in delete_node() function..."
        # Convert into string format if value of some other data-type is passed
        collection_name = collection_name.__str__()

        # Check from which collection you need to delete node from
        if collection_name == node_collection.collection_name:
            # Perform deletion operation on Nodes collection
            str_node_id = ""
            query = {}
            node_to_be_deleted = None
            node_name = ""
            # As default value of deletion_type is 0
            str_deletion_type = "deleted"
            delete_status_message = ""

            # print "\n 2 >> Nodes collection..."
            if deletion_type not in [0, 1]:
                delete_status_message = "Must pass \"deletion_type\" agrument's " \
                    + "value as either 0 (Normal delete) or 1 (Purge) !!!"
                raise Exception(delete_status_message)

            # print "\t 3 >> found node_id..."
            if not node_id:
                delete_status_message = "No value found for node_id" \
                    + "... [Expected value in ObjectId format] !!!"
                raise Exception(delete_status_message)

            # print "\t 3a >> convert node_id..."
            # Typecast node_id from string into ObjectId,
            # if found in string format
            if type(node_id) == ObjectId:
                str_node_id = str(node_id)
                # print "\t 3b >> node_id -- O to s: ", type(str_node_id), " -- ", str_node_id
            else:
                str_node_id = node_id
                if ObjectId.is_valid(node_id):
                    node_id = ObjectId(node_id)
                    # print "\t 3c >> node_id -- s to O: ", type(str_node_id), " -- ", str_node_id
                else:
                    delete_status_message = "Invalid value found for node_id " \
                        + "(%(str_node_id)s)... [Expected value in" % locals() \
                        + " ObjectId format] !!!"
                    raise Exception(delete_status_message)

            # Forming query to delete a specific node from Nodes collection
            query = {"_id": node_id}
            # print "\t 3d >> query... ", query

            # Fetch the deleting-node from given node_id
            node_to_be_deleted = node_collection.find_one(query)

            if not node_to_be_deleted:
                delete_status_message = "Node with given ObjectId " \
                    + "(%(str_node_id)s) doesn't exists " % locals() \
                    + "in Nodes collection !!!"
                raise Exception(delete_status_message)

            node_name = node_to_be_deleted.name

            if node_to_be_deleted.status == u"DELETED" and deletion_type == 0:
                delete_status_message = "%(node_name)s (%(str_node_id)s) has " % locals() \
                    + "already been deleted (using normal delete)." \
                    + "\n\nIf required, you can still purge this node !"
                return (True, delete_status_message)

            # print "\n 4 >> node to be deleted fetched successfully... ", node_to_be_deleted.name
            if ((node_to_be_deleted.status == u"DELETED" and
                deletion_type == 1) or
                    (node_to_be_deleted.status != u"DELETED")):
                # Perform delete/purge operation for
                # deleting-node's GAttribute(s)
                # print "\n\n 5 >> node's (", node_to_be_deleted.name,") GAttribute... "
                del_status, del_status_msg = delete_gattribute(
                    subject_id=node_to_be_deleted._id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message = del_status_msg
                # print "\n 5* >> delete_status_message... \n", delete_status_message

                # Required as below this node is getting saved and
                # in above delete_gattribute() function, it's getting updated
                node_to_be_deleted.reload()

                # Perform delete/purge operation
                # for deleting-node's GRelation(s)
                # print "\n\n 6 >> node's (", node_to_be_deleted.name,") GRelation... "
                del_status, del_status_msg = delete_grelation(
                    subject_id=node_to_be_deleted._id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message += "\n\n" + del_status_msg
                # print "\n 6* >> delete_status_message... \n", delete_status_message

                # Required as below this node is getting saved and
                # in above delete_gattribute() function, it's getting updated
                node_to_be_deleted.reload()

                # Search deleting-node's ObjectId in collection_set field and
                # remove from it, if found any
                res = node_collection.collection.update({
                    "_type": "GSystem",
                    "collection_set": node_to_be_deleted._id
                }, {
                    "$pull": {"collection_set": node_to_be_deleted._id}
                },
                    upsert=False, multi=True
                )
                # print "\n 7 >> collection_set : \n", res

                # Search deleting-node's ObjectId in prior_node field and
                # remove from it, if found any
                res = node_collection.collection.update({
                    "_type": "GSystem", "prior_node": node_to_be_deleted._id
                }, {
                    "$pull": {"prior_node": node_to_be_deleted._id}
                },
                    upsert=False, multi=True
                )
                # print "\n 8 >> prior_node : \n", res

                # Search deleting-node's ObjectId in post_node field and
                # remove from it, if found any
                res = node_collection.collection.update({
                    "_type": "GSystem", "post_node": node_to_be_deleted._id
                }, {
                    "$pull": {"post_node": node_to_be_deleted._id}
                },
                    upsert=False, multi=True
                )
                # print "\n 9 >> post_node : \n", res

                # Perform normal delete on deleting-node
                # Only changes the status of given node to DELETED
                node_to_be_deleted.status = u"DELETED"
                node_to_be_deleted.save()

            # Perform Purge operation on deleting-node
            if deletion_type == 1:
                # Remove from database
                str_deletion_type = "purged"

                # If given node is of member-of File GApp
                # Then remove it's references from GridFS as well
                # Consider File GApp's ObjectId is there in member_of field
                # print "\n node_to_be_deleted.member_of_names_list: ", node_to_be_deleted.member_of_names_list
                if "File" in node_to_be_deleted.member_of_names_list:
                    # print "\n 10 >> node found as File; nodes in GridFS : ", len(node_to_be_deleted.fs_file_ids)
                    if node_to_be_deleted.fs_file_ids:
                        for each in node_to_be_deleted.fs_file_ids:
                            if node_to_be_deleted.fs.files.exists(each):
                                # print "\tdeleting node in GridFS : ", each
                                node_to_be_deleted.fs.files.delete(each)

                # Finally delete the node
                node_to_be_deleted.delete()

            delete_status_message += "\n\n %(node_name)s (%(str_node_id)s) " % locals() \
                + "%(str_deletion_type)s successfully." % locals()
            # print delete_status_message
            return (True, delete_status_message)

        elif collection_name == triple_collection.collection_name:
            # Perform deletion operation on Triples collection
            subject_id = None
            underscore_type = ""
            str_node_id = ""
            query = {}
            delete_status_message = ""

            # print "\n 3 >> Triples collection..."
            if deletion_type not in [0, 1]:
                delete_status_message = "Must pass \"deletion_type\" agrument's " \
                    + "value as either 0 (Normal delete) or 1 (Purge) !!!"
                raise Exception(delete_status_message)

            # print "\n 4 >> look out for subject_id..."
            if "subject_id" in kwargs:
                subject_id = kwargs["subject_id"]
                # print "\t4a >> found subject_id...", subject_id

            if (not node_id) and (not subject_id):
                delete_status_message = "Value not found for neither node_id nor " \
                    + "subject_id... [Expected value(s) in ObjectId format]"
                raise Exception(delete_status_message)

            # print "\n 5 >> look out for _type..."
            if "_type" in kwargs:
                underscore_type = kwargs["_type"].__str__()
                # print "\t5a >> found _type...", underscore_type
                if underscore_type not in ["GAttribute", "GRelation"]:
                    delete_status_message = "Invalid value found for _type parameter " \
                        + "%(underscore_type)s... " % locals() \
                        + "Please pass either GAttribute or GRelation"
                    raise Exception(delete_status_message)

            # print "\n 5b >> convert node_id..."
            if node_id:
                if type(node_id) == ObjectId:
                    str_node_id = str(node_id)
                    # print "\t 5ba >> node_id -- O to s: ", type(str_node_id), " -- ", str_node_id
                else:
                    str_node_id = node_id
                    if ObjectId.is_valid(node_id):
                        node_id = ObjectId(node_id)
                        # print "\t 5bb >> node_id -- s to O: ", type(str_node_id), " -- ", str_node_id
                    else:
                        delete_status_message = "Invalid value found for node_id " \
                            + "(%(str_node_id)s)... [Expected value in" % locals() \
                            + " ObjectId format] !!!"
                        raise Exception(delete_status_message)

                # Forming query to delete a specific node from Triples collection
                query = {"_id": node_id}
                # print "\t 5bc >> query... ", query

                # Fetch the deleting-node from given node_id
                node_to_be_deleted = triple_collection.find_one(query)

                if not node_to_be_deleted:
                    delete_status_message = "Node with given ObjectId " \
                        + "(%(str_node_id)s) doesn't exists in Triples collection" % locals()
                    raise Exception(delete_status_message)
                # print "\t 5bd >> node_to_be_deleted... ", node_to_be_deleted.name, " -- ", node_to_be_deleted._type

                # Resetting underscore_type
                # To rectify, if by mistake wrong value is set
                # That is, consider _type is set as "GAttribute" (by mistake)
                # but node (with node_id) represents "GRelation"
                # To avoid this kind of case(s), resetting underscore_type
                underscore_type = node_to_be_deleted._type
                # print "\t 5be >> underscore_type set to node_to_be_deleted's _type... ", underscore_type

            if underscore_type == "GAttribute":
                # Delete/Purge only GAttribute node(s)

                # print "\n 6 >> Delete/Purge only GAttribute node(s)..."
                del_status, del_status_msg = delete_gattribute(
                    node_id=node_id, subject_id=subject_id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message = del_status_msg
                # print "\n 6* >> delete_status_message... \n", delete_status_message
            elif underscore_type == "GRelation":
                # Delete/Purge only GRelation node(s)

                # print "\n 7 >> Delete/Purge only GRelation node(s)..."
                del_status, del_status_msg = delete_grelation(
                    node_id=node_id, subject_id=subject_id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message = del_status_msg
                # print "\n 7* >> delete_status_message... \n", delete_status_message
            else:
                # Delete/Purge both GAttribute & GRelation node(s)

                # print "\n 8 >> Delete/Purge both GAttribute & GRelation node(s)..."
                # Delete/Purge GAttribute node(s)
                del_status, del_status_msg = delete_gattribute(
                    node_id=node_id, subject_id=subject_id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message = del_status_msg
                # print "\n 8* >> delete_status_message... \n", delete_status_message

                # Delete/Purge GRelation node(s)
                del_status, del_status_msg = delete_grelation(
                    node_id=node_id, subject_id=subject_id,
                    deletion_type=deletion_type
                )
                if not del_status:
                    raise Exception(del_status_msg)
                delete_status_message += "\n\n" + del_status_msg
                # print "\n 8* >> delete_status_message... \n", delete_status_message

            # Return output of the function
            # print delete_status_message
            return (True, delete_status_message)

        else:
            delete_status_message = " Invalid value (%(collection_name)s) " % locals() \
                + "found for collection_name field. Please refer function " \
                + "details for correct value !!!"
            raise Exception(delete_status_message)
    except Exception as e:
        delete_status_message = "Error (from delete_node) :-\n" + str(e)
        return (False, delete_status_message)
