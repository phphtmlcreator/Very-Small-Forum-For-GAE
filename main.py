#!/usr/bin/env python

##############################################################################
#
# Copyright (c) 2009 log1( mailto: log1@poczta.fm). All Rights Reserved.
# 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

__version__ = "Version: 3v1"
__author__ = ("log1@poczta.fm (Kuba Kuropatnicki)")
__license__ = 'GPL v3'

import os
import cgi
import datetime
import wsgiref.handlers
#import logging

from model import DataBaseOperations, Forum, Thread, Topic, Post, UserObj
from functions import strip_ml_tags
from postmarkup import *

from google.appengine.ext.db import *
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import images # for avatar
from django.core.paginator import ObjectPaginator, InvalidPage
#from google.appengine.ext import admin

#logging.getLogger().setLevel(logging.DEBUG)

class AclUser:
  __admin__ = ['phphtmlCreator']
  
  def getAuthentificatedUser(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return None
    return user
  
  def checkIfAuthentificatedUserIsAdmin(self):
    user = users.get_current_user()
    if users.is_current_user_admin():
      return True
    try:
      pos = self.__admin__.index(str(users.get_current_user()))
      return True
    except ValueError:
      pass
    return False
    #return str(users.get_current_user()) == self.__admin__
  
  def checkMode(self, mode):
    return self.checkIfAuthentificatedUserIsAdmin() and mode == 'admin'

class Install(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required
  def get(self):
    if not self.checkIfAuthentificatedUserIsAdmin():
      return
    forum = self.getForumInstance()
    if forum is not None:
      title = forum.title
      description = forum.description
    else:
      title = None
      description = None
    template_values = {
      'title': title,
      'description': description,
    }
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'manageForum.htm'))
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    if not self.checkIfAuthentificatedUserIsAdmin():
      return
    self.updateForumInstance(self.request.get('title'), self.request.get('description'))
    self.redirect('/?mode=admin')
        
class DeleteTopic(webapp.RequestHandler, AclUser):
  @login_required
  def get(self):
    if not self.checkIfAuthentificatedUserIsAdmin():
      return
    try:
      id = self.request.get('id')
      topic = Topic.get(db.Key.from_path('Topic', int(id)))
      thread_id = topic.thread.key().id()
      topic.delete()
    except:
      pass
    self.redirect('/viewThread?mode=admin&id='+str(thread_id))
    
    
class AddTopic(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required  
  def get(self):
    id = self.request.get('id')
    template_values = {
      'id': id,
    }
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'addTopic.htm'))
    self.response.out.write(template.render(path, template_values))
  
  def post(self):
    user = self.getAuthentificatedUser()
    if not user:
      return
    id = self.request.get('id')
    try:
      thread = Thread.get(db.Key.from_path('Thread', int(id)))
    except:
      return
    name = strip_ml_tags(self.request.get('name'))
    if name == '':
      template_values = {
        'topics' : self.topics,
        'name' : name,
      }
    else:
      topic = Topic() #parent=thread
      topic.thread = thread
      topic.name = name
      if users.get_current_user():
        topic.author = users.get_current_user()
      topic.put()
      mode = self.request.get('mode')
      self.redirect('/view?id=' + str(topic.key().id()))
      return 
      template_values = {
        'topics' : self.topics,
        'name' : '',
      }
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'addTopic.htm'))
    self.response.out.write(template.render(path, template_values))
    
class ViewTopic(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required
  def get(self):
    user = self.getAuthentificatedUser()
    forum = self.getForumInstance()
    page = self.request.get('page')
    try:
      page = int(page) - 1
    except:
      page = 0
    try:
      id = int(self.request.get('id'))
      #topic = Topic.get(db.Key.from_path('Topic', id))
      topic = self.getTopic(id)
    except:
      self.redirect('/')
      return
      #topic = self.getTopics().order('-pub_date').fetch(1)
      #topic = topic[0]
      #id = topic.key().id()
    posts = self.getPosts(id)
    paginator = ObjectPaginator(posts, 10)
    if page >= paginator.pages or page < 0:
      page = paginator.pages - 1
    if page >= paginator.pages - 1: 
      next = None
    else:
      next = page + 2
    if page < 1:
      prev = None
    else:
      prev = page
    template_values = {
      'url' : users.CreateLogoutURL(self.request.uri),
      'user' : user.nickname(),
      'forum' : forum,
      'topic' : topic,
      'posts' : paginator.get_page(page),
      'pages' : range(1, paginator.pages + 1),
      'page' : page+1,
      'next' : next,
      'prev' : prev,
      
    }    
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewTopic.htm'))
    self.response.out.write(template.render(path, template_values))    
    
class View(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required
  def get(self):
    user = self.getAuthentificatedUser()
    forum = self.getForumInstance()
    threads = self.getThreads().order('position')
    #Thread.all().order('position')
    template_values = {
      'admin': self.checkIfAuthentificatedUserIsAdmin(),
      'url' : users.CreateLogoutURL(self.request.uri),
      'user' : user.nickname(),
      'forum' : forum,
      'threads' : threads,
    }
    try:
      if self.checkMode(str(self.request.get('mode'))):
        #self.response.headers.add_header('Set-Cookie', 'mode=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % 'admin')
        path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewForumAdminMode.htm'))
        self.response.out.write(template.render(path, template_values))
        return
    except:
      pass
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewForum.htm'))
    self.response.out.write(template.render(path, template_values))
    
class SaveThreadPosition(webapp.RequestHandler, AclUser):
  def post(self):
    if self.checkIfAuthentificatedUserIsAdmin():
      for key, value in self.request.POST.items():
        if key[0:7] == "thread_":
          try:
            thread = Thread.get(db.Key.from_path('Thread', int(key[7:])))
            thread.position = int(value)
            thread.put()
          except:
            pass
    self.redirect('/?mode=admin')
    
class AddNewThread(webapp.RequestHandler, AclUser):
  def post(self):
    if self.checkIfAuthentificatedUserIsAdmin():
      name = strip_ml_tags(self.request.get('name'))
      if name != '':
        thread = Thread()
        thread.name = name
        thread.position = int(self.request.get('position'))
        thread.put()
    self.redirect('/?mode=admin')
    
class ModifyThread(webapp.RequestHandler, AclUser):
  @login_required
  def get(self):
    id = int(self.request.get('id'))
    thread = Thread.get(db.Key.from_path('Thread', int(id)))
    template_values = {
      'thread' : thread,
    }
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'modifyThread.htm'))
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    if self.checkIfAuthentificatedUserIsAdmin():
      id = int(self.request.get('id'))
      try:
        thread = Thread.get(db.Key.from_path('Thread', int(id)))
        name = strip_ml_tags(self.request.get('name'))
        if name != '':
          thread.name = name
          thread.put()
      except:
        pass
    self.redirect('/?mode=admin')
    
class DeleteThread(webapp.RequestHandler, AclUser):
  def get(self):  
    if not self.checkIfAuthentificatedUserIsAdmin():
      return
    try:
      id = int(self.request.get('id'))
      thread = Thread.get(db.Key.from_path('Thread', id))
      thread.delete()
    except:
      pass
    self.redirect('/?mode=admin')
    
    
class ViewThread(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required
  def get(self):
    user = self.getAuthentificatedUser()
    forum = self.getForumInstance()
    try:
      id = int(self.request.get('id'))
      #thread = Thread.get(db.Key.from_path('Thread', id))
      thread = self.getThread(id)
    except:
      #thread = Thread.all().order('position').fetch(1)
      thread = self.getThreads().order('position').fetch(1)
      thread = thread[0]
      id = thread.key().id()
    topics = self.getTopics(id).order('-pub_date')
    template_values = {
      'admin': self.checkIfAuthentificatedUserIsAdmin(),
      'url' : users.CreateLogoutURL(self.request.uri),
      'user' : user.nickname(),
      'forum' : forum,
      'thread' : thread,
      'topics' :topics,
    }
    try:
      if self.checkMode(str(self.request.get('mode'))):
        #self.response.headers.add_header('Set-Cookie', 'mode=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % 'admin')
        path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewThreadAdminMode.htm'))
        self.response.out.write(template.render(path, template_values))
        return
    except:
      pass
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewThread.htm'))
    self.response.out.write(template.render(path, template_values))
  
class AddPost(webapp.RequestHandler, AclUser):
  """Add New Post Method"""
  def post(self):
    user = self.getAuthentificatedUser()
    if not user:
      return
    try:
      id = int(self.request.get('id'))
      topic = Topic().get(db.Key.from_path('Topic', id))
    except:
       self.redirect('/')
       return
    post = Post(parent=topic.key())
    post.topic = topic
    if users.get_current_user():
      post.author = users.get_current_user()
    body = db.Text(strip_ml_tags(self.request.get('body')))
    postmarkup = create(use_pygments=False)
    post.body = postmarkup(body)
    # replace('\n','<br />')
    if post.body != '':
      post.put()
      message = mail.EmailMessage(sender=user.email(), subject="New message in small-forum")
      message.to = "log1 <log1@poczta.fm>"
      message.body = post.body + """ ... testing e-mail notification. Sorry if you get this message accidently."""
      message.send()
    #topic = Topic().all().filter('id =', int(self.request.get('id')))
    #topic = topic[0]
    #topic.getUserList()
    # To Do
    if self.request.get('page'):
      self.redirect('/view?id=' + str(self.request.get('id')) + '&page=' + self.request.get('page'))
    else:
      self.redirect('/view?id=' + str(self.request.get('id')))
    
class Profile(webapp.RequestHandler, AclUser, DataBaseOperations):
  """user profile class"""
  def __init__(self):
    self.user = self.getAuthentificatedUser()
    
  @login_required
  def get(self):
    user = self.getAuthentificatedUser()
    forum = self.getForumInstance()
    userData = self.getUser(self.user)
    template_values = {
      'url' : users.CreateLogoutURL(self.request.uri),
      'forum' : forum,
      'user' : self.user.nickname(),
      'name' : userData.name,
      'lastName' : userData.lastName,
      'from' : userData.cameFrom,
      'webpage' : userData.webpage,
    }    
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'myProfile.htm'))
    self.response.out.write(template.render(path, template_values))
  
  def post(self):
    user = self.getAuthentificatedUser()
    if not user:
      return
    userData = self.getUser(self.user)
    userData.name = strip_ml_tags(self.request.get('name'))
    userData.lastName = strip_ml_tags(self.request.get('lastName'))
    userData.cameFrom = strip_ml_tags(self.request.get('from'))
    userData.webpage = self.request.get('webpage')
    if self.request.get('avatar'):
      try:
        avatar = db.Blob(images.resize(self.request.get('avatar'), 100, 100))
        userData.avatar = avatar
      except:
        pass
    userData.put()
    self.redirect('/myProfile')
  
class Avatar(webapp.RequestHandler, AclUser, DataBaseOperations):
  @login_required
  def get(self):
    if self.request.get('user'):
      userData = self.getUser(users.User(self.request.get('user')+ '@gmail.com')) # !!! + '@gmail.com'
    else:
      self.user = self.getAuthentificatedUser()
      userData = self.getUser(self.user)
    if userData.avatar:
      import datetime
      lastmod = datetime.datetime.now() 
      self.response.headers['Content-Type'] = "image/png"
      self.response.headers['Cache-Control']= 'public, max-age=172800'
      self.response.headers['Last-Modified'] = lastmod.strftime("%a, %d %b %Y %H:%M:%S GMT")
      expires = lastmod + datetime.timedelta(days=365)
      self.response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")     
      self.response.out.write(userData.avatar)
    else:
      self.response.out.write("No image")
      
class ViewProfile(webapp.RequestHandler, AclUser, DataBaseOperations):
  """show user profile"""
  @login_required
  def get(self):   
    if self.request.get('user'):
      try:
        userData = self.getUser(users.User(self.request.get('user')+ '@gmail.com')) # !!! + '@gmail.com'
        template_values = {
          'login' : userData.login,
          'name' : userData.name,
          'lastName' : userData.lastName,
          'from' : userData.cameFrom,
          'webpage' : userData.webpage,
        }
        path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'viewProfile.htm'))
        self.response.out.write(template.render(path, template_values))  
      except:
        return
    else:
      return
    
class RSSFeedHandler(webapp.RequestHandler, DataBaseOperations):
  def get(self):
    try:
      n = int(self.request.get('n'))
    except:
      n = 20
    forum = self.getForumInstance()
    posts = self.getLastPosts(n)
    try:
      for post in posts:
        post.body = strip_ml_tags(post.body)
    except:
      pass
    template_values = {
      'forum' : forum,
      'selfurl' : self.request.host_url,
      'posts' : posts,
    }
    self.response.headers['Content-Type'] = 'text/xml'
    path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'rss2.xml'))
    self.response.out.write(template.render(path, template_values))
    
class ViewAllUsers(webapp.RequestHandler, DataBaseOperations):
  """View All Forum Users"""
  def get(self):
    # parameters
    #...
    # end of parameters
    forum = self.getForumInstance()
    template_values = {
      'forum' : forum,
      'users' : self.getUsers(),
    }
    for user in self.getUsers().order('-login'):
      print user.login
    print 'NO BA'
    
    
  
  
    
application = webapp.WSGIApplication([
  ('/', View),
  ('/viewThread', ViewThread),
  ('/manage', Install),
  ('/view', ViewTopic),
  ('/addTopic', AddTopic),
  ('/delTopic', DeleteTopic),
  ('/addPost', AddPost),
  ('/manageForum', Install),
  ('/myProfile', Profile),
  ('/viewProfile', ViewProfile),
  ('/avatar', Avatar),
  ('/saveThreadPosition', SaveThreadPosition),
  ('/addNewThread', AddNewThread),
  ('/modifyThread', ModifyThread),
  ('/delThread', DeleteThread),
  ('/viewUsers', ViewAllUsers),
  ('/rss.xml', RSSFeedHandler),
], debug=True)


def main():
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
