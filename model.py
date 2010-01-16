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

from google.appengine.ext import db
from google.appengine.api import memcache
import math

class DataBaseOperations:
  """All database operations + memcache"""
  
  def getForumInstance(self):
    forum = db.get(db.Key.from_path("Forum", "forum1"))
    if forum is None:
      forum = Forum(key_name="forum1")
      forum.title = 'Configure your Forum first'
      forum.description = 'go to admin mode'
      forum.put()
    return forum
  
  def updateForumInstance(self, newTitle, newDescription):
    forum = self.getForumInstance()
    forum.title = newTitle
    forum.description = newDescription
    forum.put()
    
  def getThread(self, id):
    thread = memcache.get("thread_"+str(id))
    if thread is not None:
      return thread
    try:
      thread = Thread.get(db.Key.from_path('Thread', int(id)))
      memcache.add("thread_"+str(id), thread, 10)
    except:
      pass
    return thread
    
  def getThreads(self):
    threads = memcache.get('threads')
    if threads is not None:
      return threads
    else:
      threads = Thread.all() #.order('position')
    try:
      memcache.add('threads', threads, 10)
    except:
      pass
    return threads
  
  def getTopic(self, id):
    topic = memcache.get("topic_"+str(id))
    if topic is not None:
      return topic
    try:
      topic = Topic.get(db.Key.from_path('Topic', int(id)))
      memcache.add("topic_"+str(id), thread, 10)
    except:
      pass
    return topic
    
  def getTopics(self, thread_id):
    """memcache optimization"""
    topics = memcache.get("topics_"+str(thread_id))
    if topics is not None:
      return topics
    else:
      topics = Topic.all().order('pub_date').filter('thread', db.Key.from_path('Thread',int(thread_id)))
    try:
      memcache.add("topics_"+str(thread_id), topics, 10)
    except:
      pass
    return topics
  
  def getPosts(self, topic_id):
    posts = memcache.get("posts_"+str(topic_id))
    if posts is not None:
      return posts
    else:
      posts = Post.all().order('date').filter('topic', db.Key.from_path('Topic',int(topic_id)))
    try:
      memcache.add("posts_"+str(topic_id), posts, 10)
    except:
      pass
    return posts
  
  def getLastPosts(self, postsCount):
    """get last posts"""
    postsCount = int(postsCount)
    if postsCount > 50:
      postsCount = 20
    lastPosts = memcache.get("lastPost_"+str(postsCount))
    if lastPosts is not None:
      return lastPosts
    else:
      lastPosts = Post.all().order('-date').fetch(postsCount)
    try:
      memcache.add("lastPost_"+str(postsCount), lastPosts, 10)
    except:
      pass
    return lastPosts
  
  def getUser(self, login):
    """get user profile"""
    users = memcache.get("users")
    if users is None:
      users = UserObj().all()
      try:
        memcache.add("users", users, 10)
      except:
        pass
    user = users.filter('login', login)
    try:
      user = user[0]
    except:
      user = UserObj()
      user.login = login
      user.put()
    return user
  
  def getUsers(self):
    """get all forum users"""
    users = memcache.get("users")
    if users is None:
      users = UserObj().all()
      try:
        memcache.add("users", users, 10)
      except:
        pass
    return users
    
     
class UserObj(db.Model):
  login = db.UserProperty()
  name = db.StringProperty(multiline=False)
  lastName = db.StringProperty(multiline=False)
  cameFrom = db.StringProperty(multiline=False)
  webpage = db.StringProperty(multiline=False)
  #db.LinkProperty() -> not allow empty url
  avatar = db.BlobProperty()
  # for the future
  #active = bool
  #role = db.StringProperty(required=True, choices=set(["admin", "moderator", "user", "guest"]))
  registrationDate = db.DateProperty(auto_now_add=True)

class Forum(db.Model):
  title = db.StringProperty(multiline=False)
  description = db.StringProperty(multiline=False)
  
class Thread(db.Model):
  name = db.StringProperty(multiline=False)
  position = db.IntegerProperty(default=0)
  topics_count = db.IntegerProperty(default=0)

  def countTopics(self):
    """return how many posts is in this topic"""
    return self.topics.count()

  def delete(self):    
    #topics = [topic.key() for topic in self.topics]    
    #if topics is not None:
      #db.delete(topics)
    for topic in self.topics:
      topic.delete()
    super(Thread, self).delete()
  
   
class Topic(db.Model, DataBaseOperations):
  thread = db.ReferenceProperty(Thread, collection_name='topics')
  name = db.StringProperty(multiline=False)
  author = db.UserProperty()
  pub_date = db.DateTimeProperty(auto_now_add=True)
  posts_count = db.IntegerProperty(default=0)
  #posts = Post Reference 
  
  def countPosts(self):
    """return how many posts is in this topic"""
    return self.posts.count()

  def getLastPost(self):
    """return last post it this Topic"""
    try:
      post = self.posts[self.posts_count-1] #.filter('topicId =', self.id).order('-date').fetch(1)
      return post
    except:
      return False
    
  def getUserList(self):
    """return users list who write somethink in this topic"""
    posts = Post().all().filter('topicId =', self.id)
    userList = []
    for post in posts:
      if post.author not in userList:
        userList.append(post.author)
    return userList
  
  def put(self):
    super(Topic, self).put()
    self.thread.topics_count = self.thread.countTopics()
    self.thread.put()
    
  def delete(self):
    posts = [post.key() for post in self.posts]
    if posts is not None:
      db.delete(posts)
    super(Topic, self).delete()
    self.thread.topics_count = self.thread.countTopics()
    self.thread.put()
    
    #posts = [post.key() for post in Post.all().ancestor(self.key())]
    #def txn():
    #  if posts is not None:
    #    db.delete(posts)
    #  super(Topic, self).delete()
    #db.run_in_transaction(txn)
    #self.thread.posts_count = self.thread.countThreads()
    #self.thread.put()
    

class Post(db.Model):
  topic = db.ReferenceProperty(Topic, collection_name='posts')
  date = db.DateTimeProperty(auto_now_add=True)
  author = db.UserProperty()
  body = db.TextProperty(required=False) #StringProperty(multiline=True)
  
  def put(self):
    super(Post, self).put()
    self.topic.posts_count = self.topic.countPosts()
    self.topic.put()
    

  def delete(self):
    super(Post, self).delete()
    self.topic.posts_count = self.topic.countPosts()
    self.topic.put()
    
class File(db.Model):
  name = db.StringProperty(multiline=False)
  content = db.BlobProperty() # file content as Blob
  date = db.DateTimeProperty(auto_now_add=True)
    
